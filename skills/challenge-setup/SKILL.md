---
name: challenge-setup
description: Use for local challenge environment setup, boot, and health checks.
---

# Purpose

Set up and run the FlowRadar VPN Detection challenge locally with Docker Compose, validate required environment variables, and verify service health.

# Quick Start

From challenge root:

```bash
./skills/challenge-setup/scripts/setup.sh
./skills/challenge-setup/scripts/healthcheck.sh
```

Build image before start (optional):

```bash
./skills/challenge-setup/scripts/setup.sh --build
```

# Important Files

- `compose.yml` - runs `challenge-api` service on `FLR_API_PORT` (default `10001`).
- `.env` - runtime environment values loaded by Docker Compose and helper scripts.
- `.env.example` - template for initial environment setup.
- `skills/challenge-setup/scripts/setup.sh` - setup and boot helper.
- `skills/challenge-setup/scripts/healthcheck.sh` - API reachability checks.

# Requirements

Required before setup:

- Docker
- Docker Compose plugin (`docker compose`)
- Git LFS for the mandatory `v2_train_data.csv`

Optional for development workflow:

- Python >= 3.10 and pip >= 23
- git

# Setup Workflow

1. Ensure dependencies are installed.
2. Run `git lfs pull` and verify `v2_train_data.csv` is not an LFS pointer.
3. Ensure `.env` exists (script auto-copies from `.env.example` when missing).
4. Confirm `FLR_CHALLENGE_API_KEY` is defined.
5. Confirm the mandatory v2 train/test paths.
6. Start with `docker compose up` (optionally `--build`).
7. Run health checks for `/ping` and `/health`.

# Environment Variables

Critical:

- `FLR_CHALLENGE_API_KEY`
    - Required for protected challenge endpoints (for example: `/score`).
    - Setup script fails fast if this key is missing.

Runtime:

- `FLR_API_PORT`
    - API port exposed by the compose service (default `10001`).
- `FLR_CHALLENGE_TRAIN_CSV_PATH`
    - Must resolve to `{data_dir}/v2_train_data.csv` for production validation.
- `FLR_CHALLENGE_TEST_CSV_PATH`
    - Must resolve to `{data_dir}/v2_test_data.csv` for production validation.
- `FLR_CHALLENGE_TRAINING_TIMEOUT_SECONDS`
    - Maximum container training duration.
- `FLR_CHALLENGE_MODEL_JSON_SIZE_LIMIT`
    - Maximum generated model JSON size.

Debugging:

- `DEBUG`
    - When enabled (for example `DEBUG=true`), debug mode increases log verbosity.
    - Useful for inspecting detector execution behavior during development.

Production-parity caution:

- `FLR_CHALLENGE_ACCEPTABLE_MISS_COUNT`
- `FLR_CHALLENGE_SINGLE_REQUEST_TIMEOUT`

Do not change these for production-grade score validation. You may tune them temporarily for local development, but final checks should use production-like values.

# Do / Don't

Do:

- keep `FLR_CHALLENGE_API_KEY` set before scoring.
- keep production training fixed to `v2_train_data.csv`.
- verify Git LFS data before starting the challenge.
- run healthcheck after every setup/start.
- use `--build` when Docker image or dependencies changed.

Don't:

- do not use v1 data as the production training dataset.
- rely on modified timeout/miss-count values for final score conclusions.
- skip checking container logs when API behavior is unexpected.

# Helper Scripts

- `./skills/challenge-setup/scripts/setup.sh`
    - validates Docker + Compose
    - validates Git LFS and mandatory v2 datasets
    - ensures `.env`
    - validates `FLR_CHALLENGE_API_KEY`
    - rejects non-v2 training and warns on non-v2 compatibility test data
    - starts challenge service

- `./skills/challenge-setup/scripts/healthcheck.sh`
    - checks `GET /ping`
    - checks `GET /health`
    - prints docs and OpenAPI URLs

# Verification Steps

1. Run `./skills/challenge-setup/scripts/setup.sh`.
2. Run `./skills/challenge-setup/scripts/healthcheck.sh`.
3. Confirm the challenge container sees both v2 CSV files.
4. Open:
   - `http://localhost:10001/docs`
   - `http://localhost:10001/openapi.json`

# Troubleshooting

- Setup fails with missing API key:
    - add `FLR_CHALLENGE_API_KEY` to `.env`.
- Training data is missing or very small:
    - run `git lfs pull`.
    - verify `volumes/storage/flowradar-challenge/data/v2_train_data.csv`.
- Wrong dataset is used:
    - set `FLR_CHALLENGE_TRAIN_CSV_PATH="{data_dir}/v2_train_data.csv"`.
    - set `FLR_CHALLENGE_TEST_CSV_PATH="{data_dir}/v2_test_data.csv"`.
- API not reachable:
    - check `docker compose ps` and ensure port mapping for `FLR_API_PORT` is active.
- Need deeper execution details:
    - inspect Docker logs of the running challenge container for scoring/runtime traces.
    - example: `docker compose logs -f challenge-api`

# Expected Success States

- `docker compose ps` shows `challenge-api` as running.
- `GET /ping` and `GET /health` return success.
- API docs are accessible on `http://localhost:10001/docs`.
