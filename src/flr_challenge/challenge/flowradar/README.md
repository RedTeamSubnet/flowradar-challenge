# VPN Detection

Fingerprint-based VPN detection API using network flow features.

## Overview

This project provides the isolated detector and training container used by the
FlowRadar v2 scoring API. Miners submit one training script and one inference
script. Training runs inside this container against the mandatory
`v2_train_data.csv`.

## Architecture

- **Training Logic**: `train.py` receives the training CSV and writes model JSON
- **Detection Logic**: `submissions.py` exposes `detect_vpn(features, model)`
- **Model Loading**: `POST /train` loads the generated `/tmp/model.json`
- **API**: FastAPI for serving VPN detection requests

## Key Components

| File             | Description                                                |
| ---------------- | ---------------------------------------------------------- |
| `train.py`       | Training script that writes a model JSON                   |
| `submissions.py` | VPN detection logic exposing `detect_vpn(features, model)` |
| `app.py`         | FastAPI application and endpoints                          |
| `data_types.py`  | Pydantic models for input/output                           |

## Miner Contract

Training is called as:

```sh
python train.py /path/to/v2_train_data.csv /tmp/model.json
```

The inference script must define:

```python
def detect_vpn(features: dict, model: dict) -> bool:
    ...
```

The challenge enforces `FLR_CHALLENGE_TRAINING_TIMEOUT_SECONDS`, defaulting to
`600` seconds. The generated model JSON remains temporary inside this container
for the current scoring run.

Pretrained or embedded learned weights are prohibited in `train.py` and
`submissions.py`. Training must generate the model from the provided v2 CSV
during the current run, and inference may only use the loaded generated model.

## API Endpoints

### GET /health

Health check endpoint.

### POST /train

Run the mounted training script inside the container, validate its model JSON,
and load that model for detection.

### POST /vpn_detector

Detect if traffic is VPN based on network flow features and the trained model.

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
