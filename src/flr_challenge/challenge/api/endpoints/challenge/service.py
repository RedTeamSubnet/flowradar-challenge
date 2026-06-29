import os
import tempfile
import time
from typing import Any

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


def _json_safe_value(value: Any) -> Any:
    """Convert pandas/numpy missing scalars to valid JSON values."""
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    item = getattr(value, "item", None)
    return item() if callable(item) else value


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
            f.write(miner_output.get_file_content("train.py"))
        with open(submission_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(miner_output.get_file_content("submissions.py"))
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
            container, ip_address = _utils.run_flowradar_container(
                request_id=request_id,
                file_path=submission_path,
                training_path=training_path,
                training_csv_path=config.challenge.train_csv_path,
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
            training_response = requests.post(  # nosec
                f"{base_url}/train",
                timeout=config.challenge.training_timeout_seconds + 10,
            )
            training_response.raise_for_status()
            training_result = training_response.json()
            training_seconds = time.perf_counter() - training_start
            model_size = int(training_result["model_size_bytes"])
            if (
                training_result.get("status") != "trained"
                or model_size < 1
                or model_size > config.challenge.model_json_size_limit
            ):
                raise ValueError("Detector returned an invalid training result")
            total_file_size += model_size
            logger.info(
                f"[{request_id}] - Training completed in {training_seconds:.3f}s; "
                f"model size={model_size} bytes"
            )

            df = pd.read_csv(config.challenge.test_csv_path)
            runtime_start = time.perf_counter()

            label_column = next(
                (
                    column
                    for column in ("vpn_is_enabled", "is_vpn")
                    if column in df.columns
                ),
                None,
            )
            if label_column is None:
                raise ValueError(
                    "Scoring CSV must contain 'vpn_is_enabled' or 'is_vpn'"
                )
            ground_truth = df.pop(label_column)

            _request_session = requests.Session()
            logger.info(
                f"[{request_id}] - Starting fingerprinting process for {len(df)} rows"
            )
            for index, row in df.iterrows():
                row_data = {
                    column: _json_safe_value(value) for column, value in row.items()
                }
                expected_is_vpn = ground_truth.loc[index]

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
                _utils.cleanup_container(container)
                logger.info(f"[{request_id}] - Detector container cleaned up")
            scoring_status_manager.set_scoring_status(ScoringStatus.AVAILABLE)

    return final_score


__all__ = [
    "get_task",
    "score",
]
