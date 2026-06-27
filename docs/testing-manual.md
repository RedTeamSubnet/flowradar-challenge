# FlowRadar v2 Testing Manual

Use this manual to test a miner submission before production scoring.

## 1. Dataset Contract

Production uses these files:

```text
volumes/storage/flowradar-challenge/data/v2_train_data.csv
volumes/storage/flowradar-challenge/data/v2_test_data.csv
```

`v2_train_data.csv` is mandatory. The challenge passes this exact file to the
submitted `train.py` as its first argument. Miners cannot choose another
training dataset in production.

The v2 schema contains 110 columns:

- label: `vpn_is_enabled`
- inference features: the remaining 109 columns

Production configuration:

```dotenv
FLR_CHALLENGE_TRAIN_CSV_PATH="{data_dir}/v2_train_data.csv"
FLR_CHALLENGE_TEST_CSV_PATH="{data_dir}/v2_test_data.csv"
```

Do not point `FLR_CHALLENGE_TRAIN_CSV_PATH` at v1 data when validating a miner.

## 2. Fast Script Checks

Compile the reference scripts:

```sh
python3 -m py_compile \
  src/flr_challenge/challenge/flowradar/src/train.py \
  src/flr_challenge/challenge/flowradar/src/submissions.py
```

Run the trainer against the mandatory v2 training data:

```sh
python3 src/flr_challenge/challenge/flowradar/src/train.py \
  volumes/storage/flowradar-challenge/data/v2_train_data.csv \
  /tmp/flowradar_model.json
```

Validate the model JSON:

```sh
python3 -m json.tool /tmp/flowradar_model.json >/dev/null
```

Run a minimal inference check:

```sh
python3 - <<'PY'
import importlib.util
import json

spec = importlib.util.spec_from_file_location(
    "submission",
    "src/flr_challenge/challenge/flowradar/src/submissions.py",
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

with open("/tmp/flowradar_model.json", encoding="utf-8") as model_file:
    model = json.load(model_file)

row = {"fwd_sum_pkt_len": 10, "bwd_sum_pkt_len": 30}
print(mod.detect_vpn(row, model))
PY
```

The output must be `True` or `False`.

This direct trainer command is only a development check. Production calls
`POST /train` inside the isolated FlowRadar container.

## 3. Optional v1 Compatibility Test

The v1 datasets have 34 columns and use `is_vpn` as the label. They are not
valid production training replacements. Use them only to test whether inference
handles a reduced legacy feature set.

Create a temporary v1 test file with the v2 shape:

```sh
python3 - <<'PY'
from pathlib import Path

import pandas as pd

data_dir = Path("volumes/storage/flowradar-challenge/data")
v1 = pd.read_csv(data_dir / "v1_test_data.csv")
v2_columns = pd.read_csv(data_dir / "v2_train_data.csv", nrows=0).columns

v1 = v1.rename(columns={"is_vpn": "vpn_is_enabled"})
v1 = v1.reindex(columns=v2_columns)
v1.to_csv("/tmp/v1_test_v2_shape.csv", index=False)
PY
```

This transformation:

- renames `is_vpn` to `vpn_is_enabled`
- preserves v1 features that also exist in v2
- adds missing v2-only columns as empty values
- orders columns exactly like the v2 schema

Keep training on `v2_train_data.csv`, but temporarily score the adapted v1
test file:

```dotenv
FLR_CHALLENGE_TRAIN_CSV_PATH="{data_dir}/v2_train_data.csv"
FLR_CHALLENGE_TEST_CSV_PATH="/tmp/v1_test_v2_shape.csv"
```

When the challenge runs in Docker, the test file must be inside the mounted
data directory. Use:

```sh
cp /tmp/v1_test_v2_shape.csv \
  volumes/storage/flowradar-challenge/data/v1_test_v2_shape.csv
```

Then configure:

```dotenv
FLR_CHALLENGE_TEST_CSV_PATH="{data_dir}/v1_test_v2_shape.csv"
```

Restore `v2_test_data.csv` before production-equivalent scoring.

## 4. Start the Challenge API

Create `.env` if needed:

```sh
cp .env.example .env
```

Start Compose:

```sh
docker compose up -d --remove-orphans --force-recreate
docker compose logs -f -n 100
```

Check health:

```sh
curl -s http://localhost:10001/health
```

## 5. Score the Local Submission

The helper reads the reference `train.py` and `submissions.py`, then sends the
v2 payload to `/score`:

```sh
python3 skills/challenge-score/scripts/check_score.py
```

Expected result: an F1 score from `0` to `1`.

## 6. Inspect Results

```sh
curl -s http://localhost:10001/telemetry | jq
curl -s http://localhost:10001/results | jq
curl -s http://localhost:10001/status | jq
```

## 7. Common Failures

Missing training CSV:

- Confirm `FLR_CHALLENGE_TRAIN_CSV_PATH` resolves to `v2_train_data.csv`.
- Confirm Git LFS downloaded the dataset with `git lfs pull`.

Wrong schema or label:

- Production v2 uses `vpn_is_enabled`.
- V1 uses `is_vpn` and must be adapted before using it as test data.
- Never train the production submission on `v1_train_data.csv`.

Invalid model JSON:

- Write JSON to the exact second CLI argument.
- Use `json.dump(...)`, not `repr(...)`.

Embedded model weights:

- Do not place pretrained weights, encoded model blobs, or learned lookup tables
  inside `train.py` or `submissions.py`.
- All learned weights must be generated from `v2_train_data.csv` during the
  current run.
- `submissions.py` must use only the generated `model` argument.

Detector request failure:

- Define `detect_vpn(features, model)`.
- Handle absent features and JSON `null`; adapted v1 rows lack v2-only fields.
- Empty CSV cells are sent as JSON `null`.

Training timeout:

- Production enforces `FLR_CHALLENGE_TRAINING_TIMEOUT_SECONDS`.
- Increasing it locally does not change the production limit.
