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
    ip_address: str, timeout: int = 100, fingerprinter_port: int = 8000
) -> None:
    url = f"http://{ip_address}:{fingerprinter_port}/health"
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
        f"Fingerprinter container health check timed out after {timeout}s in this url: {url}"
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


def run_fingerprinter_container(
    request_id: str, files_dir: str, fingerprinter_port: int = 8000
) -> tuple[docker.models.containers.Container, str]:
    client = docker.from_env()
    ensure_network_exists()
    _ensure_image(client)

    container_name = f"fingerprinter_{request_id}"

    volumes = {}
    for file_name in os.listdir(files_dir):
        file_path = os.path.join(files_dir, file_name)
        target_path = f"/app/submissions/{file_name}"
        volumes[file_path] = {"bind": target_path, "mode": "ro"}
    container = client.containers.run(
        config.challenge.fp_container.image,
        detach=True,
        network=config.challenge.fp_container.network_name,
        environment={"PORT": str(fingerprinter_port)},
        volumes=volumes,
        name=container_name,
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
    container: docker.models.containers.Container, prefix: str = "[FINGERPRINTER]"
) -> None:
    for log_line in container.logs(stream=True, follow=True):
        logger.debug(f"{prefix} {log_line.decode('utf-8').strip()}")


def start_log_streaming_thread(
    container: docker.models.containers.Container, prefix: str = "[FINGERPRINTER]"
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
    "run_fingerprinter_container",
    "cleanup_container",
    "stream_container_logs",
    "start_log_streaming_thread",
    "get_container_network_stats",
    "ContainerStatsResult",
]
