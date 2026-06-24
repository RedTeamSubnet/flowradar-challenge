# Important Files

Use these files first when solving this challenge.

## Submission entry points

- `src/flr_challenge/challenge/flowradar/src/train.py`
  - receives mandatory v2 training CSV as `sys.argv[1]`.
  - writes model JSON to `sys.argv[2]`.
- `src/flr_challenge/challenge/flowradar/src/submissions.py`
  - contains `detect_vpn(features, model)` used for every replayed row.

## Runtime and API flow

- `src/flr_challenge/challenge/flowradar/src/app.py`
  - `/train` executes the mounted trainer inside the isolated container.
  - `/vpn_detector` request flow.
  - passes `products` and parsed model into `detect_vpn`.
- `src/flr_challenge/challenge/flowradar/src/data_types.py`
  - request/response schema for detector service.

## Scoring and dataset behavior

- `src/flr_challenge/challenge/api/endpoints/challenge/service.py`
  - starts the isolated container, calls `/train`, replays v2 test rows, and computes final score.
- `src/flr_challenge/challenge/api/endpoints/challenge/payload_managers.py`
  - score composition and counters:
    - true/false positives/negatives
    - precision, recall, F1 (final score)
- `src/flr_challenge/challenge/api/core/configs/_challenge.py`
  - challenge config: v2 train/test paths, timeouts, model size, and submission limits.

## Local operations

- `skills/challenge-setup/SKILL.md`
  - setup/run/health checks and environment guidance.
- `skills/challenge-score/SKILL.md`
  - scoring flow and endpoint references.
- `skills/challenge-score/scripts/check_score.py`
  - quick local score command.

## Dataset location

- `volumes/storage/flowradar-challenge/data/v2_train_data.csv`
  - mandatory production training dataset.
- `volumes/storage/flowradar-challenge/data/v2_test_data.csv`
  - production replay dataset used by the scoring service.
- `volumes/storage/flowradar-challenge/data/v1_test_data.csv`
  - optional compatibility data; adapt its label and shape before scoring.
