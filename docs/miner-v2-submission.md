# Miner v2 Submission Guide

FlowRadar v2 submissions contain two Python files encoded in the `/score` payload:

- `train_script`
- `inference_script`

## Training Script

The challenge API writes the submitted training content to `train.py` and calls:

```sh
python train.py <training_csv> <model_json>
```

The default training dataset is:

```text
{FLR_API_DATA_DIR}/training.csv
```

For local compose runs this maps to:

```text
volumes/storage/flowradar-challenge/data/training.csv
```

The training script must:

- finish before `FLR_CHALLENGE_TRAINING_TIMEOUT_SECONDS`, default `600`
- write valid JSON to the second argument
- keep the JSON below `FLR_CHALLENGE_MODEL_JSON_SIZE_LIMIT`, default `20 MiB`
- avoid depending on files outside the submitted script and provided CSV

The challenge persists the validated JSON as:

```text
/data/weights/miner_input_<unix_timestamp>.json
```

In compose, this directory is host-mounted at:

```text
volumes/storage/flowradar-challenge/weights/
```

## Inference Script

The challenge API writes the submitted inference content to `submissions.py` and mounts it into the FlowRadar detector container.

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
