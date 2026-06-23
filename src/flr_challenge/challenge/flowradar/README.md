# VPN Detection

Fingerprint-based VPN detection API using network flow features.

## Overview

This project provides the detector container used by the FlowRadar v2 scoring API. Miners submit one training script and one inference script. The challenge runs training on `metrics_100k.csv` and mounts the produced per-run JSON into this detector container as `/app/model.json`.

## Architecture

- **Training Logic**: `train.py` receives the training CSV and writes model JSON
- **Detection Logic**: `submissions.py` exposes `detect_vpn(features, model)`
- **Model Loading**: `app.py` loads `FLOWRADAR_MODEL_PATH`, default `/app/model.json`
- **API**: FastAPI for serving VPN detection requests

## Key Components

| File             | Description                       |
| ---------------- | --------------------------------- |
| `train.py`       | Training script that writes a model JSON |
| `submissions.py` | VPN detection logic exposing `detect_vpn(features, model)` |
| `app.py`         | FastAPI application and endpoints |
| `data_types.py`  | Pydantic models for input/output  |

## Miner Contract

Training is called as:

```sh
python train.py /path/to/metrics_100k.csv /tmp/model.json
```

The inference script must define:

```python
def detect_vpn(features: dict, model: dict) -> bool:
    ...
```

The challenge enforces `FLR_CHALLENGE_TRAINING_TIMEOUT_SECONDS`, defaulting to `600` seconds. The generated model JSON is mounted into this container at `/app/model.json` for the current scoring run.

## API Endpoints

### GET /health

Health check endpoint.

### POST /vpn_detector

Detect if traffic is VPN based on network flow features and the mounted model JSON.

**Request:**

```json
{
  "products": {
    "flow_duration": 1504,
    "fwd_num_pkts": 11,
    "bwd_num_pkts": 10,
    "fwd_sum_pkt_len": 3211,
    "bwd_sum_pkt_len": 1334,
    ...
  }
}
```

**Response:**

```json
{
    "is_vpn": true,
    "request_id": "abc123..."
}
```
