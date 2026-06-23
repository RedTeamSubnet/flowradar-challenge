# VPN Detection

Fingerprint-based VPN detection API using network flow features.

## Overview

This project provides an API that processes network flow data to detect if the traffic is coming from a VPN. In v2, miners submit one training script and one inference script. The challenge runs training on the configured 100k CSV, persists the produced JSON under `/data/weights/miner_input_<unix>.json`, then mounts that JSON into the detector container for scoring.

## Architecture

- **Training Logic**: `train.py` receives the training CSV and writes model JSON
- **Detection Logic**: `submissions.py` reads model data passed by the API wrapper
- **API**: FastAPI for serving VPN detection requests

## Key Components

| File             | Description                       |
| ---------------- | --------------------------------- |
| `train.py`       | Training script that writes JSON model weights |
| `submissions.py` | VPN detection logic exposing `detect_vpn(features, model)` |
| `app.py`         | FastAPI application and endpoints |
| `data_types.py`  | Pydantic models for input/output  |

## Miner Contract

Training is called as:

```sh
python train.py /path/to/training.csv /tmp/model.json
```

The inference script must define:

```python
def detect_vpn(features: dict, model: dict) -> bool:
    ...
```

The challenge enforces `FLR_CHALLENGE_TRAINING_TIMEOUT_SECONDS`, defaulting to `600` seconds. Model files are persisted under `FLR_CHALLENGE_MODEL_WEIGHTS_DIR`, defaulting to `/data/weights`.

## API Endpoints

### GET /health

Health check endpoint.

### POST /fingerprint

Detect if traffic is VPN based on network flow features.

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
