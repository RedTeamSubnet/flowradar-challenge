# FlowRadar Documentation

FlowRadar v2 uses a two-stage miner submission:

1. Train a model from the mandatory `v2_train_data.csv`.
2. Score `v2_test_data.csv` with the temporary model inside the detector container.

## Manuals

- [Miner v2 submission guide](./miner-v2-submission.md)
- [Testing manual](./testing-manual.md)
- [Release notes](./release-notes.md)

## Important Paths

| Path | Purpose |
| --- | --- |
| `volumes/storage/flowradar-challenge/data/v2_train_data.csv` | Mandatory production training CSV passed to miner `train_script` |
| `volumes/storage/flowradar-challenge/data/v2_test_data.csv` | Production scoring dataset replayed through the detector |
| `volumes/storage/flowradar-challenge/data/v1_test_data.csv` | Optional compatibility test data; must be adapted to the v2 shape |
| `src/flr_challenge/challenge/flowradar/src/train.py` | Reference trainer |
| `src/flr_challenge/challenge/flowradar/src/submissions.py` | Reference inference script |
