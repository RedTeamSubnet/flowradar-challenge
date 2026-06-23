import json
import os
import subprocess
import sys
import tempfile
import time

import pandas as pd
import requests
from pydantic import validate_call

from api.config import config
from api.logger import logger

from api.endpoints.challenge import _utils
from .schemas import MinerInput, MinerOutput
from .payload_managers import (
    payload_manager,
    scoring_status_manager,
    scoring_telemetry_manager,
    ScoringStatus,
)


def get_task() -> MinerInput:
    return MinerInput()


@validate_call
def score(request_id: str, miner_output: MinerOutput) -> float:
    if scoring_status_manager.get_scoring_status() == ScoringStatus.SCORING:
        raise RuntimeError("Scoring is already in progress")
    runtime_seconds = 0.0
    payload_manager.restart_manager()
    _request_miss_counter = 0
    container = None

    scoring_status_manager.set_scoring_status(ScoringStatus.SCORING)
    final_score = 0.0

    total_file_size = 0

    with tempfile.TemporaryDirectory() as tmp_dir:

        training_path = os.path.join(tmp_dir, "train.py")
        submission_path = os.path.join(tmp_dir, "submissions.py")
        with open(training_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(miner_output.train_script)
        with open(submission_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(miner_output.inference_script)
        total_file_size += os.path.getsize(training_path)
        total_file_size += os.path.getsize(submission_path)

        logger.info(
            f"[{request_id}] - Total submission file size: {total_file_size} bytes"
        )

        try:
            total_runtime_start = time.perf_counter()
            training_start = time.perf_counter()
            logger.info(
                f"[{request_id}] - Starting model training with timeout "
                f"{config.challenge.training_timeout_seconds}s"
            )
            model_path = _build_model_output_path()
            training_output_path = f"{model_path}.tmp"
            try:
                _run_training_script(
                    request_id=request_id,
                    training_path=training_path,
                    model_path=training_output_path,
                    tmp_dir=tmp_dir,
                )
                os.replace(training_output_path, model_path)
            except Exception:
                if os.path.exists(training_output_path):
                    os.remove(training_output_path)
                raise
            training_seconds = time.perf_counter() - training_start
            total_file_size += os.path.getsize(model_path)
            logger.info(
                f"[{request_id}] - Training completed in {training_seconds:.3f}s; "
                f"model saved to {model_path}; "
                f"model size={os.path.getsize(model_path)} bytes"
            )

            container, ip_address = _utils.run_flowradar_container(
                request_id=request_id,
                file_path=submission_path,
                model_path=model_path,
                flowradar_port=config.challenge.flowradar_port,
            )
            _utils.start_log_streaming_thread(container)

            config.challenge.flowradar_ip = ip_address
            logger.info(f"[{request_id}] - Detector container started at {ip_address}")

            _utils.wait_for_health(
                ip_address, flowradar_port=config.challenge.flowradar_port
            )
            logger.info(f"[{request_id}] - Detector container is healthy")

            base_url = f"http://{ip_address}:{config.challenge.flowradar_port}"
            df = pd.read_csv(config.challenge.metrics_csv_path)
            runtime_start = time.perf_counter()

            # Save ground truth before dropping the column
            ground_truth = None
            if "is_vpn" in df.columns:
                ground_truth = df["is_vpn"].copy()
                df = df.drop(columns=["is_vpn"])
            _request_session = requests.Session()
            logger.info(
                f"[{request_id}] - Starting fingerprinting process for {len(df)} rows"
            )
            for index, row in df.iterrows():
                row_data = row.to_dict()
                expected_is_vpn = None

                # Use the saved ground truth for scoring
                if ground_truth is not None:
                    expected_is_vpn = ground_truth[index]

                try:

                    resp = _request_session.post(
                        f"{base_url}/vpn_detector",
                        json={"products": row_data},
                        timeout=config.challenge.single_request_timeout,
                    )
                    resp.raise_for_status()
                    result = resp.json()
                    is_vpn = result.get("is_vpn")

                    logger.debug(
                        f"[{request_id}] - Row {index}: is_vpn={is_vpn}, expected={expected_is_vpn}"
                    )

                    if is_vpn is not None:
                        payload_manager.store_payload(
                            row_id=str(index),
                            is_vpn=str(is_vpn),
                            expected_is_vpn=str(expected_is_vpn),
                            request_id=result.get("request_id"),
                        )
                    else:
                        _request_miss_counter += 1
                        logger.warning(
                            f"[{request_id}] - No is_vpn returned for row {index}"
                        )
                except requests.RequestException as e:
                    _request_miss_counter += 1
                    logger.error(
                        f"[{request_id}] - Error during fingerprint request for row {index}: {str(e)}"
                    )
                if _request_miss_counter > config.challenge.acceptable_miss_count:
                    logger.error(
                        f"[{request_id}] - Exceeded max request misses. Stopping fingerprinting."
                    )
                    break
            _request_session.close()
            fingerprint_seconds = time.perf_counter() - runtime_start
            runtime_seconds = time.perf_counter() - total_runtime_start

            logger.info(
                f"[{request_id}] - Fingerprinting completed in {fingerprint_seconds:.3f}s. "
                f"Stored {payload_manager.payload_count()} fingerprints."
            )

            final_score = payload_manager.calculate_score()
            logger.success(f"[{request_id}] - Final Score: {final_score:.3f}")

        finally:

            network_stats = _utils.ContainerStatsResult()
            if container is not None:
                network_stats = _utils.get_container_network_stats(container)

            scoring_telemetry_manager.set_telemetry(
                request_id=request_id,
                total_file_size_bytes=total_file_size,
                runtime_seconds=round(runtime_seconds, 3),
                network_rx_bytes=network_stats.network_rx_bytes,
                network_tx_bytes=network_stats.network_tx_bytes,
                score=final_score,
            )

            if container:
                # _utils.cleanup_container(container)
                logger.info(f"[{request_id}] - Detector container cleaned up")
            scoring_status_manager.set_scoring_status(ScoringStatus.AVAILABLE)

    return final_score


def _build_model_output_path() -> str:
    weights_dir = config.challenge.model_weights_dir
    os.makedirs(weights_dir, exist_ok=True)

    timestamp = int(time.time())
    model_path = os.path.join(weights_dir, f"miner_input_{timestamp}.json")
    while os.path.exists(model_path):
        timestamp += 1
        model_path = os.path.join(weights_dir, f"miner_input_{timestamp}.json")
    return model_path


def _run_training_script(
    request_id: str,
    training_path: str,
    model_path: str,
    tmp_dir: str,
) -> None:
    training_csv_path = config.challenge.training_dataset_path
    if not os.path.isfile(training_csv_path):
        raise FileNotFoundError(f"Training dataset not found: {training_csv_path}")

    command = [
        sys.executable,
        training_path,
        training_csv_path,
        model_path,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=tmp_dir,
            capture_output=True,
            text=True,
            timeout=config.challenge.training_timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error(
            f"[{request_id}] - Training timed out after "
            f"{config.challenge.training_timeout_seconds}s"
        )
        raise TimeoutError("Training timed out") from exc

    if result.stdout:
        logger.info(f"[{request_id}] - Training stdout:\n{result.stdout[-4000:]}")
    if result.stderr:
        logger.warning(f"[{request_id}] - Training stderr:\n{result.stderr[-4000:]}")

    if result.returncode != 0:
        raise RuntimeError(f"Training script failed with exit code {result.returncode}")
    if not os.path.isfile(model_path):
        raise FileNotFoundError("Training script did not create model JSON")
    model_size = os.path.getsize(model_path)
    if model_size > config.challenge.model_json_size_limit:
        raise ValueError(
            f"Model JSON exceeds size limit of {config.challenge.model_json_size_limit} bytes"
        )
    with open(model_path, encoding="utf-8") as model_file:
        json.load(model_file)


__all__ = [
    "get_task",
    "score",
]
