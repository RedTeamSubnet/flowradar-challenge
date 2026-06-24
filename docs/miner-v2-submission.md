# Miner v2 Submission Guide

FlowRadar v2 submissions contain two Python files encoded in the `/score` payload:

- `train_script`
- `inference_script`

## Training Script

The challenge API mounts the submitted training content read-only into an
isolated FlowRadar container. It calls the container's `POST /train` endpoint,
which executes:

```sh
python train.py <training_csv> <model_json>
```

The default training CSV is:

```text
{FLR_API_DATA_DIR}/metrics_100k.csv
```

For local compose runs this maps to:

```text
volumes/storage/flowradar-challenge/data/metrics_100k.csv
```

The training script must:

- finish before `FLR_CHALLENGE_TRAINING_TIMEOUT_SECONDS`, default `600`
- write valid JSON to the second argument
- keep the JSON below `FLR_CHALLENGE_MODEL_JSON_SIZE_LIMIT`, default `20 MiB`
- avoid depending on files outside the submitted script and provided CSV
- stay within the configured container CPU, memory, and PID limits

The model JSON is written to `/tmp/model.json` inside the detector container,
validated there, and loaded into memory for that scoring run. The challenge API
process does not execute miner Python and does not receive or persist the model
file.

## Inference Script

The challenge API writes the submitted inference content to `submissions.py`
and mounts it read-only into the same FlowRadar detector container.

The preferred interface is:

```python
def detect_vpn(features: dict, model: dict) -> bool:
    ...
```

`features` is one CSV row from `metrics.csv` after the `is_vpn` ground-truth column has been removed. `model` is the parsed JSON object produced by the training script.

Legacy one-argument submissions still run through a fallback:

```python
def detect_vpn(features: dict) -> bool:
    ...
```

New miners should use the two-argument interface.

## Score Payload Shape

```json
{
  "miner_input": {
    "random_val": "nonce"
  },
  "miner_output": {
    "train_script": "import json, sys\n...",
    "inference_script": "def detect_vpn(features, model):\n    return False\n"
  }
}
```

## Minimal Example

Training:

```python
import json
import sys

model_path = sys.argv[2]
with open(model_path, "w", encoding="utf-8") as model_file:
    json.dump({"always": False}, model_file)
```

Inference:

```python
def detect_vpn(features, model):
    return bool(model.get("always", False))
```
