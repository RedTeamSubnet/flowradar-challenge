# FlowRadar v2 Testing Manual

Use this manual to test a miner submission before scoring it in production.

## 1. Prepare Data

Expected local data paths:

```text
volumes/storage/flowradar-challenge/data/metrics_100k.csv
volumes/storage/flowradar-challenge/data/metrics.csv
```

`metrics_100k.csv` is used only for training. `metrics.csv` is used for scoring.

If your local data directory still has an older or alternate training filename, create `metrics_100k.csv` once. For example:

```sh
cp volumes/storage/flowradar-challenge/data/<source-training-file>.csv \
  volumes/storage/flowradar-challenge/data/metrics_100k.csv
```

## 2. Fast Script Checks

Compile the reference scripts:

```sh
python3 -m py_compile \
  src/flr_challenge/challenge/flowradar/src/train.py \
  src/flr_challenge/challenge/flowradar/src/submissions.py
```

Run the trainer directly:

```sh
python3 src/flr_challenge/challenge/flowradar/src/train.py \
  volumes/storage/flowradar-challenge/data/metrics_100k.csv \
  /tmp/flowradar_model.json
```

Validate the model JSON:

```sh
python3 -m json.tool /tmp/flowradar_model.json >/dev/null
```

Run a minimal inference import check:

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

The output should be `True` or `False`.

## 3. Start the Challenge API

Create `.env` if needed:

```sh
cp .env.example .env
```

Start compose:

```sh
./compose.sh start -l
```

or:

```sh
docker compose up -d --remove-orphans --force-recreate
docker compose logs -f -n 100
```

Check health:

```sh
curl -s http://localhost:10001/health
```

## 4. Score the Local Reference Submission

The helper reads:

- `src/flr_challenge/challenge/flowradar/src/train.py`
- `src/flr_challenge/challenge/flowradar/src/submissions.py`

Then it sends the v2 payload to `/score`:

```sh
python3 skills/challenge-score/scripts/check_score.py
```

Expected result: a numeric F1 score from `0` to `1`.

## 5. Inspect Telemetry and Results

Telemetry:

```sh
curl -s http://localhost:10001/telemetry | jq
```

Stored row-level results:

```sh
curl -s http://localhost:10001/results | jq
```

Status:

```sh
curl -s http://localhost:10001/status | jq
```

## 6. Common Failures

Training timeout:

- Increase only for local experiments with `FLR_CHALLENGE_TRAINING_TIMEOUT_SECONDS`.
- Production should keep the configured challenge limit.

Missing training CSV:

- Confirm `FLR_API_DATA_DIR` points to the directory containing `metrics_100k.csv`.
- In compose, confirm `volumes/storage/flowradar-challenge/data/metrics_100k.csv` exists.

Invalid model JSON:

- The training script must write JSON to the exact second CLI argument.
- Use `json.dump(...)`, not `repr(...)`.

Detector returns HTTP 500:

- Confirm `detect_vpn(features, model)` is defined.
- Ensure inference code handles missing fields and string numeric values.
