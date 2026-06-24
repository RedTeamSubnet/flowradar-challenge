# Miner v2 Submission Guide

FlowRadar v2 submissions contain:

- `train_script`
- `inference_script`

## Mandatory Training Dataset

Production always trains miners with:

```text
volumes/storage/flowradar-challenge/data/v2_train_data.csv
```

Inside the challenge container, the path is configured by:

```dotenv
FLR_CHALLENGE_TRAIN_CSV_PATH="{data_dir}/v2_train_data.csv"
```

This dataset is mandatory. Miners cannot provide a dataset path, replace the
dataset, or request a different production training file.

The repository stores this dataset with Git LFS. Run `git lfs pull` after
cloning if the local file contains only an LFS pointer.

The challenge mounts the submitted trainer and v2 data read-only into the
isolated FlowRadar container. The container executes:

```sh
python train.py <v2_train_csv> <model_json>
```

The v2 dataset has 110 columns. Its label is `vpn_is_enabled`; the other 109
columns are model features.

The training script must:

- read the CSV path from `sys.argv[1]`
- write valid JSON to `sys.argv[2]`
- finish before `FLR_CHALLENGE_TRAINING_TIMEOUT_SECONDS`, default `600`
- keep JSON below `FLR_CHALLENGE_MODEL_JSON_SIZE_LIMIT`, default `20 MiB`
- work using only the submitted script, installed dependencies, and provided CSV

The generated model remains temporary inside the detector container and is
destroyed after scoring.

## Inference Script

The inference script must expose:

```python
def detect_vpn(features: dict, model: dict) -> bool:
    ...
```

Production inference rows come from `v2_test_data.csv`. The challenge removes
`vpn_is_enabled` before calling the miner function. Empty CSV cells are passed
as JSON `null`.

Inference code should tolerate:

- missing or null optional values
- numeric values represented as Python `int` or `float`
- string-valued JA4 and sequence fields

## V1 Compatibility Testing

The provided v1 datasets use 34 columns and the label `is_vpn`. They are only
for optional compatibility testing. They are not accepted as substitutes for
`v2_train_data.csv`.

To test against v1:

1. Train on `v2_train_data.csv`.
2. Rename the v1 test label from `is_vpn` to `vpn_is_enabled`.
3. Reindex the v1 test columns to the v2 schema.
4. Score the adapted v1 file.

See [Testing Manual](./testing-manual.md) for the exact conversion command.

## Score Payload

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

## Minimal Trainer

```python
import json
import sys

training_csv = sys.argv[1]
model_path = sys.argv[2]

# Train using training_csv.
with open(model_path, "w", encoding="utf-8") as model_file:
    json.dump({"always": False}, model_file)
```

## Minimal Inference

```python
def detect_vpn(features, model):
    return bool(model.get("always", False))
```
