import logging
from typing import Any

logger = logging.getLogger(__name__)


def preprocess_metrics(raw_metrics: dict[str, Any]) -> dict[str, Any]:
    payload = {}
    # Canvas 2D
    canvas2d = raw_metrics.get("canvas2d", {})
    if canvas2d:
        payload["canvas_geometry"] = canvas2d.get("$hash", "")[:100]
        emoji_set = canvas2d.get("emojiSet", [])
        if emoji_set:
            payload["canvas_text"] = f"emojis:{len(emoji_set)}"

    # WebGL
    webgl = raw_metrics.get("canvasWebgl", {})
    if webgl:
        params = webgl.get("parameters", {})
        payload["gpu_renderer"] = str(params.get("UNMASKED_RENDERER_WEBGL", "")).lower()
        payload["gpu_vendor"] = str(params.get("UNMASKED_VENDOR_WEBGL", "")).lower()

    # Fonts
    font_data = raw_metrics.get("font", {})
    fonts = font_data.get("fonts", [])
    if fonts and isinstance(fonts, list):
        payload["fonts"] = ",".join(sorted(fonts))

    # Screen
    screen = raw_metrics.get("screen", {})
    resolution = screen.get("resolution")
    if resolution and isinstance(resolution, list) and len(resolution) >= 2:
        payload["screen_resolution"] = f"{resolution[0]}x{resolution[1]}"

    color_depth = screen.get("colorDepth")
    if color_depth is not None:
        payload["color_depth"] = color_depth

    # Language/Platform
    navigator = raw_metrics.get("navigator", {})
    languages = navigator.get("languages")
    if languages:
        payload["languages"] = str(languages)

    platform = navigator.get("platform")
    if platform:
        payload["platform"] = platform.lower()

    vendor = navigator.get("vendor")
    if vendor:
        payload["vendor"] = vendor.lower()

    # Timezone
    timezone = raw_metrics.get("timezone", {}).get("value")
    if timezone:
        payload["timezone"] = str(timezone).lower()

    # Other common fields if present in top-level
    payload["architecture"] = str(raw_metrics.get("architecture", ""))
    payload["hardware_concurrency"] = raw_metrics.get("hardwareConcurrency")
    payload["device_memory"] = raw_metrics.get("deviceMemory")

    # Filter out empty values
    payload = {k: v for k, v in payload.items() if v is not None and v != ""}
    return payload


__all__ = ["preprocess_metrics"]
