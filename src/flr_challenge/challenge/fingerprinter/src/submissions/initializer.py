import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "database.db"


def initialize_db(db_path: str | None = None) -> sqlite3.Connection:
    if db_path is None:
        db_path = str(DB_PATH)

    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fingerprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fingerprint TEXT UNIQUE NOT NULL,
            visitor_id TEXT,
            user_agent TEXT,
            ip_address TEXT,
            architecture TEXT,
            canvas_geometry TEXT,
            canvas_text TEXT,
            canvas_winding INTEGER,
            audio_hash TEXT,
            color_depth INTEGER,
            color_gamut TEXT,
            contrast INTEGER,
            cookies_enabled INTEGER,
            cpu_class TEXT,
            device_memory INTEGER,
            fonts TEXT,
            font_preferences TEXT,
            forced_colors INTEGER,
            hardware_concurrency INTEGER,
            hdr INTEGER,
            indexed_db INTEGER,
            inverted_colors INTEGER,
            languages TEXT,
            local_storage INTEGER,
            math_signature TEXT,
            monochrome INTEGER,
            open_database INTEGER,
            os_cpu TEXT,
            os TEXT,
            pdf_viewer_enabled INTEGER,
            platform TEXT,
            plugins_count INTEGER,
            reduced_motion INTEGER,
            screen_frame TEXT,
            screen_resolution TEXT,
            session_storage INTEGER,
            timezone TEXT,
            max_touch_points INTEGER,
            vendor TEXT,
            vendor_flavors TEXT,
            gpu_renderer TEXT,
            gpu_vendor TEXT,
            browser_name TEXT,
            browser_version TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    logger.info(f"Database initialized at {db_path}")

    return conn


__all__ = ["initialize_db"]
