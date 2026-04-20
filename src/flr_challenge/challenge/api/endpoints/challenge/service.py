import json
import os
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
def score(request_id: str, miner_output: MinerOutput) -> None:
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
        for file in miner_output.commit_files:
            file_path = os.path.join(tmp_dir, file.file_name)
            with open(file_path, "w") as f:
                f.write(file.content)
            total_file_size += os.path.getsize(file_path)

        logger.info(
            f"[{request_id}] - Total submission file size: {total_file_size} bytes"
        )

        try:
            container, ip_address = _utils.run_fingerprinter_container(
                request_id=request_id,
                files_dir=tmp_dir,
                fingerprinter_port=config.challenge.fingerprinter_port,
            )
            _utils.start_log_streaming_thread(container)

            config.challenge.fingerprinter_ip = ip_address
            logger.info(
                f"[{request_id}] - Fingerprinter container started at {ip_address}"
            )

            _utils.wait_for_health(
                ip_address, fingerprinter_port=config.challenge.fingerprinter_port
            )
            logger.info(f"[{request_id}] - Fingerprinter container is healthy")

            base_url = f"http://{ip_address}:{config.challenge.fingerprinter_port}"
            df = pd.read_csv(config.challenge.metrics_csv_path)
            runtime_start = time.perf_counter()
            for index, row in df[["social_id", "user_metrics"]].iterrows():
                social_id = str(row["social_id"])
                user_metrics = json.loads(str(row["user_metrics"]))
                try:
                    resp = requests.post(
                        f"{base_url}/fingerprint",
                        json={"products": user_metrics},
                        timeout=config.challenge.single_request_timeout,
                    )
                    resp.raise_for_status()
                    fingerprint = resp.json().get("fingerprint")
                    payload = resp.json().get("payload")
                    if fingerprint:
                        payload_manager.store_fingerprint(
                            social_id,
                            fingerprint,
                            payload,
                            resp.json().get("request_id"),
                        )
                    else:
                        _request_miss_counter += 1
                        logger.warning(
                            f"[{request_id}] - No fingerprint returned for {social_id}"
                        )
                except requests.RequestException as e:
                    _request_miss_counter += 1
                    logger.error(
                        f"[{request_id}] - Error during fingerprint request for {social_id}: {str(e)}"
                    )
                if _request_miss_counter > config.challenge.acceptable_miss_count:
                    logger.error(
                        f"[{request_id}] - Exceeded max request misses. Stopping fingerprinting."
                    )
                    break
            runtime_seconds = time.perf_counter() - runtime_start

            logger.info(
                f"[{request_id}] - Fingerprinting completed. Stored {payload_manager.fingerprint_count()} fingerprints"
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
                logger.info(f"[{request_id}] - Fingerprinter container cleaned up")
            scoring_status_manager.set_scoring_status(ScoringStatus.AVAILABLE)

    return final_score


__all__ = [
    "get_task",
    "score",
]
