import hashlib
import json
import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)


def generate_fingerprint(payload: dict[str, Any]) -> str:
    normalized = {}
    for key, value in payload.items():
        if value is None:
            normalized[key] = ""
        elif isinstance(value, bool):
            normalized[key] = "1" if value else "0"
        elif isinstance(value, (int, float)):
            normalized[key] = str(value)
        else:
            normalized[key] = str(value).lower().strip()

    sorted_json = json.dumps(normalized, sort_keys=True)
    fingerprint = hashlib.sha256(sorted_json.encode()).hexdigest()

    logger.info(f"Generated fingerprint: {fingerprint[:16]}...")
    return fingerprint


def generate_and_link(
    payload: dict[str, Any], db_conn: sqlite3.Connection
) -> dict[str, Any]:
    fingerprint = generate_fingerprint(payload)

    cursor = db_conn.cursor()

    cursor.execute(
        """
        SELECT id, fingerprint, created_at, last_seen
        FROM fingerprints
        WHERE fingerprint = ?
    """,
        (fingerprint,),
    )

    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            """
            UPDATE fingerprints
            SET last_seen = CURRENT_TIMESTAMP
            WHERE fingerprint = ?
        """,
            (fingerprint,),
        )
        db_conn.commit()
        logger.info(f"Updated existing fingerprint: {fingerprint[:16]}...")
        return {
            "fingerprint": fingerprint,
            "is_new": False,
            "id": existing["id"],
            "created_at": existing["created_at"],
        }
    else:
        cursor.execute(
            """
            INSERT INTO fingerprints (
                fingerprint,
                architecture,
                audio_hash,
                canvas_geometry,
                canvas_text,
                canvas_winding,
                color_depth,
                color_gamut,
                contrast,
                cookies_enabled,
                cpu_class,
                device_memory,
                fonts,
                font_preferences,
                forced_colors,
                hardware_concurrency,
                hdr,
                indexed_db,
                inverted_colors,
                languages,
                local_storage,
                math_signature,
                monochrome,
                open_database,
                os_cpu,
                pdf_viewer_enabled,
                platform,
                plugins_count,
                reduced_motion,
                screen_frame,
                screen_resolution,
                session_storage,
                timezone,
                max_touch_points,
                vendor,
                vendor_flavors,
                gpu_renderer,
                gpu_vendor,
                browser_name,
                browser_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) """,  # noqa: E501
            (
                fingerprint,
                payload.get("architecture"),
                payload.get("audio_hash"),
                payload.get("canvas_geometry"),
                payload.get("canvas_text"),
                payload.get("canvas_winding"),
                payload.get("color_depth"),
                payload.get("color_gamut"),
                payload.get("contrast"),
                payload.get("cookies_enabled"),
                payload.get("cpu_class"),
                payload.get("device_memory"),
                payload.get("fonts"),
                payload.get("font_preferences"),
                payload.get("forced_colors"),
                payload.get("hardware_concurrency"),
                payload.get("hdr"),
                payload.get("indexed_db"),
                payload.get("inverted_colors"),
                payload.get("languages"),
                payload.get("local_storage"),
                payload.get("math_signature"),
                payload.get("monochrome"),
                payload.get("open_database"),
                payload.get("os_cpu"),
                payload.get("pdf_viewer_enabled"),
                payload.get("platform"),
                payload.get("plugins_count"),
                payload.get("reduced_motion"),
                payload.get("screen_frame"),
                payload.get("screen_resolution"),
                payload.get("session_storage"),
                payload.get("timezone"),
                payload.get("max_touch_points"),
                payload.get("vendor"),
                payload.get("vendor_flavors"),
                payload.get("gpu_renderer"),
                payload.get("gpu_vendor"),
                payload.get("browser_name"),
                payload.get("browser_version"),
            ),
        )
        db_conn.commit()
        logger.info(f"Inserted new fingerprint: {fingerprint[:16]}...")
        return {"fingerprint": fingerprint, "is_new": True, "id": cursor.lastrowid}


__all__ = ["generate_fingerprint", "generate_and_link"]
