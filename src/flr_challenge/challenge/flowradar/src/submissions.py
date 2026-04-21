import logging
from typing import Any

logger = logging.getLogger(__name__)


def detect_vpn(features: dict[str, Any]) -> bool:
    """
    Detect if the traffic is coming from a VPN based on network flow features.

    Args:
        features: Dictionary containing network flow features.

    Returns:
        True if VPN is detected, False otherwise.
    """
    logger.info("Processing VPN detection request...")

    try:
        fwd_num_pkts = features.get("fwd_num_pkts", 0)
        bwd_num_pkts = features.get("bwd_num_pkts", 0)
        fwd_sum_pkt_len = features.get("fwd_sum_pkt_len", 0)
        bwd_sum_pkt_len = features.get("bwd_sum_pkt_len", 0)
        flow_duration = features.get("flow_duration", 0)

        logger.info(
            f"Features - fwd_num_pkts: {fwd_num_pkts}, bwd_num_pkts: {bwd_num_pkts}, "
            f"fwd_sum_pkt_len: {fwd_sum_pkt_len}, bwd_sum_pkt_len: {bwd_sum_pkt_len}, "
            f"flow_duration: {flow_duration}"
        )

        # Heuristic 1: Check if backward packets are significantly larger than forward packets
        # This is often the case with VPN traffic as the server sends more data back
        if fwd_sum_pkt_len > 0:
            ratio = bwd_sum_pkt_len / fwd_sum_pkt_len
            logger.info(f"Backward/Forward packet length ratio: {ratio}")
            if ratio > 1.2:
                logger.info("VPN detected based on packet length ratio")
                return True

        # Heuristic 2: Check total packets vs flow duration
        total_pkts = fwd_num_pkts + bwd_num_pkts
        if flow_duration > 0:
            pkts_per_ms = total_pkts / flow_duration
            logger.info(f"Packets per millisecond: {pkts_per_ms}")
            if pkts_per_ms < 0.005:  # Low packet rate indicates potential VPN
                logger.info("VPN detected based on low packet rate")
                return True

        # If no heuristic matched, assume not VPN
        logger.info("No VPN indicators found, returning False")
        return False

    except Exception as e:
        logger.error(f"Error processing features: {e}")
        return False


__all__ = ["detect_vpn"]