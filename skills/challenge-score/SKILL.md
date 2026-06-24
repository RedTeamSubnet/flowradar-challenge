---
name: challenge-score
description: Use for scoring current submission and inspecting score-related endpoints.
---

# Purpose

This skill provides a reliable way to score the current FlowRadar submission and quickly inspect score-related outputs.

# Quick Start

From challenge root:

```bash
python3 skills/challenge-score/scripts/check_score.py
```

What it does:
1. Loads `FLR_CHALLENGE_API_KEY` from root `.env` (if present).
2. Reads training and inference files from `src/flr_challenge/challenge/flowradar/src/train.py` and `submissions.py`.
3. Sends `POST http://localhost:10001/score` with `X-API-Key` header.
4. Prints score output (F1 score expected from `0` to `1`).

# Important Files

- `skills/challenge-score/scripts/check_score.py` - local scoring helper script.
- `src/flr_challenge/challenge/api/endpoints/challenge/schemas.py` - `MinerOutput` and score telemetry schema.
- `src/flr_challenge/challenge/api/endpoints/challenge/router.py` - challenge endpoint definitions.
- `src/flr_challenge/challenge/flowradar/src/submissions.py` - current solver submission.

# Scoring System

The script builds payload using the challenge submission format:

```json
{
  "miner_input": {
    "random_val": "<random string>"
  },
  "miner_output": {
    "train_script": "<contents of train.py>",
    "inference_script": "<contents of submissions.py>"
  }
}
```

`MinerOutput` constraints (from schema):
- `train_script` is required and called as `python train.py <training_csv> <model_json>`.
- `inference_script` is required and must expose `detect_vpn(features, model)`.
- each script must respect the configured submission line limit.

Expected `/score` behavior:
- endpoint trains with mandatory `v2_train_data.csv`.
- endpoint scores provided `miner_output` by replaying `v2_test_data.csv`.
- endpoint removes `vpn_is_enabled` before inference.
- empty CSV cells are sent as JSON `null`.
- response is a score float in `[0, 1]`.

# Do / Don't

Do:
- keep training logic in `src/flr_challenge/challenge/flowradar/src/train.py`.
- keep inference logic in `src/flr_challenge/challenge/flowradar/src/submissions.py`.
- read the training CSV from `sys.argv[1]` and write JSON to `sys.argv[2]`.
- train only from the provided mandatory v2 CSV.
- score after every meaningful submission change.
- inspect telemetry/results when score changes unexpectedly.

Don't:
- send empty or partial script content.
- replace mandatory production training with v1 data.
- move submission logic outside `submissions.py` without updating challenge config.
- assume stale score state; rerun scoring after edits.

# Helper Scripts

- `python3 skills/challenge-score/scripts/check_score.py`
  - reads `train.py` and `submissions.py`
  - enforces mandatory v2 training, warns on compatibility test data, and
    validates Git LFS data
  - calls `/score`
  - allows the configured training timeout plus scoring time
  - prints score or raw error response

# Verification Steps

1. Ensure API server is running on `localhost:10001`.
2. Ensure root `.env` has `FLR_CHALLENGE_API_KEY`.
3. Ensure `FLR_CHALLENGE_TRAIN_CSV_PATH` points to `v2_train_data.csv`.
4. Ensure `FLR_CHALLENGE_TEST_CSV_PATH` points to `v2_test_data.csv`.
5. Run `git lfs pull` if the mandatory training file is unavailable.
6. Run script and confirm numeric output between `0` and `1`.
7. Optional: inspect `GET /telemetry` and `GET /results` for deeper validation.

# Troubleshooting

- Missing file error:
  - confirm both `train.py` and `submissions.py` exist.
  - confirm Git LFS downloaded `v2_train_data.csv`.
- Invalid JSON model:
  - confirm `train.py` writes valid JSON to its second argument.
- Fingerprint serialization error:
  - ensure inference handles missing features and JSON `null`.
- Auth failure:
  - confirm `FLR_CHALLENGE_API_KEY` value in root `.env`.
- Validation error:
  - compare payload to `MinerOutput` in `src/flr_challenge/challenge/api/endpoints/challenge/schemas.py`.
- Connection error:
  - verify local API is reachable at `http://localhost:10001`.
- Need detailed scoring breakdown:
  - inspect Docker container logs for challenge API/scorer service; logs include request errors and F1 details.

# Related Endpoints

From `src/flr_challenge/challenge/api/endpoints/challenge/router.py`:

- `GET /task` - returns current miner input (randomized string).
- `POST /score` - scores submission payload.
- `GET /status` - current scoring status.
- `GET /results` - stored prediction results.
- `GET /telemetry` - latest scoring telemetry (`request_id`, runtime, network bytes, score).

# Expected Success States

- scoring script exits with code `0`.
- output is a float score in `[0, 1]`.
- telemetry endpoint shows latest run metrics with a populated `score`.
