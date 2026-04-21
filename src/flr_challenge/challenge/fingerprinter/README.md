# Historical Fingerprinter

Fingerprint-based identification API using CreepJS signals.

## Overview

This project provides an API that processes device fingerprint data from CreepJS products and generates unique identifiers. It extracts key device signals (canvas, audio, browser details, fonts, IP info, etc.) to create stable fingerprints stored in SQLite.

## Architecture

- **Database**: SQLite (`database.db`) for fingerprint persistence
- **API**: FastAPI for serving fingerprint requests
- **Fingerprinting**: SHA-256 hash of normalized device signals

## Key Components

| File                               | Description                                                 |
| ---------------------------------- | ----------------------------------------------------------- |
| `submissions/initializer.py`       | DB connection and table setup                               |
| `submissions/metrics_collector.py` | Extracts fingerprint-relevant signals from raw CreepJS data |
| `submissions/linker.py`            | Generates fingerprint and links to existing records         |

## Database Schema

```sql
fingerprints (
    id, fingerprint, user_agent, ip_address,
    canvas_geometry, canvas_text, audio_hash,
    color_depth, color_gamut, fonts, os,
    browser_name, browser_version, created_at, last_seen
)
```

## API Endpoints

### GET /health

Health check endpoint.

### POST /fingerprint

Generate a fingerprint from CreepJS products data.

**Request:**

```json
{
  "products": {
    "identification": { "data": { ... } },
    "rawDeviceAttributes": { "data": { ... } },
    ...
  }
}
```

**Response:**

```json
{
    "fingerprint": "abc123...",
    "is_new": true
}
```
