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

        file_path = os.path.join(tmp_dir, "submission.py")
        with open(file_path, "w") as f:
            f.write(miner_output.submission_py)
        total_file_size += os.path.getsize(file_path)

        logger.info(
            f"[{request_id}] - Total submission file size: {total_file_size} bytes"
        )

        try:
            container, ip_address = _utils.run_flowradar_container(
                request_id=request_id,
                file_path=file_path,
                flowradar_port=config.challenge.flowradar_port,
            )
            _utils.start_log_streaming_thread(container)

            config.challenge.flowradar_ip = ip_address
            logger.info(
                f"[{request_id}] - Fingerprinter container started at {ip_address}"
            )

            _utils.wait_for_health(
                ip_address, flowradar_port=config.challenge.flowradar_port
            )
            logger.info(f"[{request_id}] - Fingerprinter container is healthy")

            base_url = f"http://{ip_address}:{config.challenge.flowradar_port}"
            df = pd.read_csv(config.challenge.metrics_csv_path)
            runtime_start = time.perf_counter()

            # Save ground truth before dropping the column
            ground_truth = None
            if "is_vpn" in df.columns:
                ground_truth = df["is_vpn"].copy()
                df = df.drop(columns=["is_vpn"])
            _request_session = requests.Session()
            for index, row in df.iterrows():
                row_data = row.to_dict()
                expected_is_vpn = None

                # Use the saved ground truth for scoring
                if ground_truth is not None:
                    expected_is_vpn = ground_truth[index]

                try:

                    resp = _request_session.post(
                        f"{base_url}/fingerprint",
                        json={"products": row_data},
                        timeout=config.challenge.single_request_timeout,
                    )
                    resp.raise_for_status()
                    result = resp.json()
                    is_vpn = result.get("is_vpn")

                    logger.info(
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
            runtime_seconds = time.perf_counter() - runtime_start

            logger.info(
                f"[{request_id}] - Fingerprinting completed. Stored {payload_manager.payload_count()} fingerprints."
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
