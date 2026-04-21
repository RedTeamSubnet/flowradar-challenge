from api.logger import logger
from enum import Enum
from dataclasses import dataclass


@dataclass
class ScoringTelemetry:
    request_id: str | None = None
    total_file_size_bytes: int = 0
    runtime_seconds: float = 0.0
    network_rx_bytes: int = 0
    network_tx_bytes: int = 0
    score: float | None = None


class ScoringTelemetryManager:
    def __init__(self):
        self._latest: ScoringTelemetry = ScoringTelemetry()

    def set_telemetry(
        self,
        request_id: str | None = None,
        total_file_size_bytes: int = 0,
        runtime_seconds: float = 0.0,
        network_rx_bytes: int = 0,
        network_tx_bytes: int = 0,
        score: float | None = None,
    ) -> None:
        self._latest = ScoringTelemetry(
            request_id=request_id,
            total_file_size_bytes=total_file_size_bytes,
            runtime_seconds=runtime_seconds,
            network_rx_bytes=network_rx_bytes,
            network_tx_bytes=network_tx_bytes,
            score=score,
        )
        logger.info(
            f"[Telemetry] Recorded: runtime={runtime_seconds:.2f}s, "
            f"net_rx={network_rx_bytes}, net_tx={network_tx_bytes}"
        )

    def get_telemetry(self) -> ScoringTelemetry:
        return self._latest

    def reset(self) -> None:
        self._latest = ScoringTelemetry()


class PayloadManager:
    def __init__(self):
        self.payloads: list[dict] = []

    def restart_manager(self) -> None:
        self.payloads = []

    def store_payload(
        self, row_id: str, is_vpn: str, expected_is_vpn: str, request_id: str = None
    ) -> None:
        self.payloads.append(
            {
                "row_id": row_id,
                "is_vpn": is_vpn,
                "expected_is_vpn": expected_is_vpn,
                "request_id": request_id,
            }
        )

    def get_payload(self) -> list[dict]:
        return self.payloads

    def payload_count(self) -> int:
        return len(self.payloads)

    def calculate_score(self) -> float:
        if not self.payloads:
            logger.warning("No payloads to score")
            return 0.0

        # Use local variables to calculate TP, FP, TN, FN
        tp = fp = tn = fn = 0
        for payload in self.payloads:
            predicted_vpn = bool(payload["is_vpn"] == "True")
            actual_vpn = bool(payload["expected_is_vpn"] == "True")

            if predicted_vpn and actual_vpn:
                tp += 1
            elif predicted_vpn and not actual_vpn:
                fp += 1
            elif not predicted_vpn and not actual_vpn:
                tn += 1
            else:  # not predicted_vpn and actual_vpn
                fn += 1

        total_count = len(self.payloads)
        logger.info(
            f"Total predictions: {total_count}, TP: {tp}, FP: {fp}, TN: {tn}, FN: {fn}"
        )

        if total_count == 0:
            return 0.0

        # Calculate Precision, Recall, F1
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        if precision + recall == 0:
            f1 = 0.0
        else:
            f1 = 2 * (precision * recall) / (precision + recall)

        logger.info(f"Precision: {precision:.3f}, Recall: {recall:.3f}, F1: {f1:.3f}")

        return round(f1, 3)


class ScoringStatus(str, Enum):
    STARTED = "started"
    SCORING = "scoring"
    AVAILABLE = "available"


class ScoringStatusManager:
    def __init__(self):
        self._scoring_status = ScoringStatus.STARTED

    def get_scoring_status(self) -> ScoringStatus:
        return self._scoring_status

    def set_scoring_status(self, status: ScoringStatus) -> None:
        self._scoring_status = status


payload_manager = PayloadManager()
scoring_status_manager = ScoringStatusManager()
scoring_telemetry_manager = ScoringTelemetryManager()

__all__ = [
    "PayloadManager",
    "payload_manager",
    "ScoringStatusManager",
    "scoring_status_manager",
    "ScoringTelemetry",
    "ScoringTelemetryManager",
    "scoring_telemetry_manager",
]
