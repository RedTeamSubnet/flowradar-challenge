# FlowRadar Documentation

FlowRadar v2 uses a two-stage miner submission:

1. Train a model from `training.csv`.
2. Score `metrics.csv` with the trained JSON model mounted into the detector container.

## Manuals

- [Miner v2 submission guide](./miner-v2-submission.md)
- [Testing manual](./testing-manual.md)
- [Release notes](./release-notes.md)

## Important Paths

| Path | Purpose |
| --- | --- |
| `volumes/storage/flowradar-challenge/data/training.csv` | Training dataset passed to miner `train_script` |
| `volumes/storage/flowradar-challenge/data/metrics.csv` | Scoring dataset replayed through the detector |
| `/data/weights/miner_input_<unix>.json` | Persisted trained model inside the challenge API container |
| `volumes/storage/flowradar-challenge/weights/` | Host-mounted weights directory for compose runs |
| `src/flr_challenge/challenge/flowradar/src/train.py` | Reference trainer |
| `src/flr_challenge/challenge/flowradar/src/submissions.py` | Reference inference script |
