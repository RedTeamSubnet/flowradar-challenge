import os
import time

from dataclasses import dataclass
from threading import Thread

import docker
import requests

from api.logger import logger
from api.config import config


@dataclass
class ContainerStatsResult:
    network_rx_bytes: int = 0
    network_tx_bytes: int = 0


def ensure_network_exists() -> None:
    client = docker.from_env()
    try:
        client.networks.get(config.challenge.fp_container.network_name)
    except docker.errors.NotFound:
        client.networks.create(
            config.challenge.fp_container.network_name, driver="bridge", internal=True
        )


def wait_for_health(
    ip_address: str, timeout: int = 100, flowradar_port: int = 8000
) -> None:
    url = f"http://{ip_address}:{flowradar_port}/health"
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200 and resp.json().get("status") == "ok":
                return
        except Exception as e:
            logger.warning(f"Error occurred while checking health: {e}")
        time.sleep(1)
    raise TimeoutError(
        f"Detector container health check timed out after {timeout}s in this url: {url}"
    )


def _ensure_image(client: docker.DockerClient) -> None:
    try:
        client.images.get(config.challenge.fp_container.image)
    except docker.errors.NotFound:
        try:
            client.images.pull(config.challenge.fp_container.image)
        except docker.errors.NotFound:
            client.images.build(
                path=config.challenge.fp_container.build_path,
                tag=config.challenge.fp_container.image,
                rm=True,
            )


def run_flowradar_container(
    request_id: str,
    file_path: str,
    training_path: str,
    training_csv_path: str,
    flowradar_port: int = 8000,
) -> tuple[docker.models.containers.Container, str]:
    if not os.path.isfile(training_csv_path):
        raise FileNotFoundError(f"Training CSV not found: {training_csv_path}")

    client = docker.from_env()
    ensure_network_exists()
    _ensure_image(client)

    container_name = f"flowradar_{request_id}"

    volumes = {}

    volumes[file_path] = {"bind": "/app/submissions.py", "mode": "ro"}
    volumes[training_path] = {"bind": "/app/train.py", "mode": "ro"}
    volumes[training_csv_path] = {"bind": "/data/training.csv", "mode": "ro"}
    environment = {
        "PORT": str(flowradar_port),
        "PYTHONDONTWRITEBYTECODE": "1",
        "FLOWRADAR_TRAINING_PATH": "/app/train.py",
        "FLOWRADAR_TRAINING_CSV_PATH": "/data/training.csv",
        "FLOWRADAR_MODEL_PATH": "/tmp/model.json",  # nosec
        "FLOWRADAR_TRAINING_TIMEOUT_SECONDS": str(
            config.challenge.training_timeout_seconds
        ),
        "FLOWRADAR_MODEL_JSON_SIZE_LIMIT": str(config.challenge.model_json_size_limit),
    }

    container = client.containers.run(
        config.challenge.fp_container.image,
        detach=True,
        network=config.challenge.fp_container.network_name,
        environment=environment,
        volumes=volumes,
        name=container_name,
        read_only=True,
        tmpfs={"/tmp": "rw,noexec,nosuid,size=64m"},  # nosec
        cap_drop=["ALL"],
        security_opt=["no-new-privileges:true"],
    )
    time.sleep(3)

    container.reload()
    ip_address = container.attrs["NetworkSettings"]["Networks"][
        config.challenge.fp_container.network_name
    ]["IPAddress"]

    return container, ip_address


def cleanup_container(container: docker.models.containers.Container) -> None:
    try:
        container.stop()
        container.remove()
    except docker.errors.NotFound:
        pass


def stream_container_logs(
    container: docker.models.containers.Container, prefix: str = "[DETECTOR]"
) -> None:
    for log_line in container.logs(stream=True, follow=True):
        logger.debug(f"{prefix} {log_line.decode('utf-8').strip()}")


def start_log_streaming_thread(
    container: docker.models.containers.Container, prefix: str = "[DETECTOR]"
) -> Thread:
    thread = Thread(target=stream_container_logs, args=(container, prefix), daemon=True)
    thread.start()
    return thread


def get_container_network_stats(
    container: docker.models.containers.Container,
) -> ContainerStatsResult:
    try:
        stats = container.stats(stream=False)
        logger.debug(f"Container stats: {stats}")
        networks = stats.get("networks") or {}
        rx_bytes = 0
        tx_bytes = 0
        for iface_stats in networks.values():
            if isinstance(iface_stats, dict):
                rx_bytes += iface_stats.get("rx_bytes", 0)
                tx_bytes += iface_stats.get("tx_bytes", 0)
        return ContainerStatsResult(
            network_rx_bytes=rx_bytes, network_tx_bytes=tx_bytes
        )
    except Exception as e:
        logger.warning(f"Error fetching network stats: {e}")
        return ContainerStatsResult()


__all__ = [
    "ensure_network_exists",
    "wait_for_health",
    "run_flowradar_container",
    "cleanup_container",
    "stream_container_logs",
    "start_log_streaming_thread",
    "get_container_network_stats",
    "ContainerStatsResult",
]
