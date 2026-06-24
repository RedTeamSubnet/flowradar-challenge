---
name: challenge-solver-guide
description: Use for designing and implementing high-score VPN detection submissions for this challenge.
---

# Purpose

Guide agents to solve the FlowRadar challenge with robust VPN detection logic, not brittle one-rule heuristics.

Primary objective:
- maximize F1 score by improving precision/recall balance for VPN classification.

# Quick Start

1. Set up and run challenge services:
   - `./skills/challenge-setup/scripts/setup.sh`
   - `./skills/challenge-setup/scripts/healthcheck.sh`
2. Implement the two submission scripts:
   - `src/flr_challenge/challenge/flowradar/src/train.py`
   - `src/flr_challenge/challenge/flowradar/src/submissions.py`
3. Score after each meaningful iteration:
   - `python3 skills/challenge-score/scripts/check_score.py`
4. Inspect diagnostics:
   - `GET /telemetry`, `GET /results`, and container logs.

# Important Files

See full map in:
- `skills/challenge-solver-guide/references/important-files.md`

Core challenge data/input locations:
- mandatory training dataset: `volumes/storage/flowradar-challenge/data/v2_train_data.csv`
- production scoring dataset: `volumes/storage/flowradar-challenge/data/v2_test_data.csv`
- trainer: `src/flr_challenge/challenge/flowradar/src/train.py`
- inference: `src/flr_challenge/challenge/flowradar/src/submissions.py`

Both locations are mandatory because the score helper submits both files.

# Architecture Overview

High-level pipeline:
1. Challenge API `/score` receives both files through
   `miner_output.commit_files`.
2. API starts an isolated FlowRadar container with both scripts and mandatory
   `v2_train_data.csv` mounted read-only.
3. `POST /train` runs `train.py` and loads its temporary JSON model.
4. `v2_test_data.csv` rows are replayed through `/vpn_detector`.
5. `detect_vpn(features, model)` returns a prediction.
6. API computes final score from classification outcomes.

Implementation implication:
- strong solutions combine multiple flow signals and robust handling of noisy or missing values.

# Scoring System

Current scoring logic (`payload_managers.py`):
- track TP, FP, TN, FN across replayed rows.
- compute precision and recall.
- compute F1 score and round to 3 decimals.

Hard failure behavior:
- if misses exceed `FLR_CHALLENGE_ACCEPTABLE_MISS_COUNT`, scoring stops early.
- excessive misses/timeouts often lower score heavily.

Optimization priority:
- improve both precision and recall together.
- reduce false positives without collapsing recall, and vice versa.

# Solver Workflow

1. Baseline
   - run current score and capture telemetry.
2. Training strategy
   - learn only from `v2_train_data.csv`.
   - keep the serialized JSON model compact and deterministic.
3. Feature strategy
   - identify predictive features from duration, packet length, IAT, and TCP flags.
   - define safe normalization/casting for every used key.
4. Decision strategy
   - combine multiple heuristics/signals into a balanced decision.
   - avoid one-feature hard dependence.
5. Iterate
   - run scoring, inspect errors, compare precision/recall tradeoffs.
6. Harden
   - ensure logic handles missing fields and unexpected values gracefully.

# Investigation Priorities

1. Feature extraction quality in `submissions.py`
   - robust parsing (`int`/`float` coercion, default values, bounds).
2. Model construction quality in `train.py`
   - use `vpn_is_enabled` as the v2 label.
   - produce valid JSON within the configured limit.
3. Signal design
   - packet size asymmetry, packet rates, timing variability, and flag patterns.
4. Threshold tuning
   - use combinations and score-like aggregation instead of brittle single cutoff.
5. Failure resilience
   - never throw for malformed payloads; fallback to safe defaults.

# Common Vulnerability Patterns

- High false-positive pattern:
  - classifying normal asymmetric traffic as VPN too aggressively.
- High false-negative pattern:
  - relying on only one VPN signature and missing alternate patterns.
- Overfitting pattern:
  - thresholds tuned to one narrow traffic distribution.
- Runtime failure pattern:
  - unsafe casts and divide-by-zero paths in feature math.

# Challenge-Specific Hints

- Treat this as binary classification, not identity linking.
- Start from interpretable features and incrementally tune thresholds.
- Balance class decisions with explicit precision/recall tradeoff checks.
- Keep logic lightweight; request failures directly hurt score.
- Empty CSV cells arrive as JSON `null`; JA4 and sequence values may be strings.
- V1 data is optional compatibility input only. Never substitute it for v2
  production training.

# Do / Don't

See:
- `skills/challenge-solver-guide/references/do-and-dont.md`

# Helper Scripts

- Setup:
  - `./skills/challenge-setup/scripts/setup.sh`
  - `./skills/challenge-setup/scripts/healthcheck.sh`
- Score:
  - `python3 skills/challenge-score/scripts/check_score.py`

# Verification Steps

1. Run scoring script and record float score in `[0, 1]`.
2. Check `GET /telemetry` for runtime, network usage, and reported score.
3. Check `GET /results` to inspect prediction vs expected behavior.
4. Review container logs when behavior is unexpected:
   - `docker compose logs -f challenge-api`
5. Repeat after each strategic change and compare score deltas.

# Troubleshooting

- Score remains near zero:
  - inspect TP/FP/FN balance and retune thresholds.
- Training fails:
  - confirm `train.py` reads `sys.argv[1]`, writes `sys.argv[2]`, and handles
    `vpn_is_enabled`.
- Many request errors/timeouts:
  - simplify expensive logic and keep runtime predictable.
- No meaningful improvement after changes:
  - revisit feature combinations and decision calibration.
- Inconsistent local results:
  - reset environment, rerun setup, and validate `.env` + API key.

# Example Requests

- "Analyze current `detect_vpn` logic and propose a precision/recall improvement plan."
- "Implement robust feature normalization for flow metrics and explain each selected signal."
- "Refactor detection logic to combine packet length, IAT, and flag-based evidence."
- "Run score, inspect telemetry, and explain the main bottleneck for higher F1."

# Expected Success States

- score is consistently non-zero and trending upward across iterations.
- misses stay below `FLR_CHALLENGE_ACCEPTABLE_MISS_COUNT`.
- detection logic handles feature noise without frequent unstable flips.
