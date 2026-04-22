# VPN Detection

Fingerprint-based VPN detection API using network flow features.

## Overview

This project provides an API that processes network flow data to detect if the traffic is coming from a VPN. It analyzes packet length ratios, packet rates, and other network features.

## Architecture

- **Detection Logic**: Heuristic-based VPN detection
- **API**: FastAPI for serving VPN detection requests

## Key Components

| File             | Description                       |
| ---------------- | --------------------------------- |
| `submissions.py` | VPN detection logic (heuristics)  |
| `app.py`         | FastAPI application and endpoints |
| `data_types.py`  | Pydantic models for input/output  |

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
