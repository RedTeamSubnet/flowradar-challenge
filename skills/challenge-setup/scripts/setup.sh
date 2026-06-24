#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed. Please install Docker first." >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose is not available. Please install Docker Compose plugin." >&2
  exit 1
fi

if ! command -v git-lfs >/dev/null 2>&1 && ! git lfs version >/dev/null 2>&1; then
  echo "git-lfs is required for v2_train_data.csv." >&2
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  if [[ -f "${ROOT_DIR}/.env.example" ]]; then
    cp "${ROOT_DIR}/.env.example" "${ENV_FILE}"
    echo "Created .env from .env.example"
  else
    echo "Missing .env and .env.example in challenge root." >&2
    exit 1
  fi
fi

set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

if [[ -z "${FLR_CHALLENGE_API_KEY:-}" ]]; then
  echo "FLR_CHALLENGE_API_KEY is missing in .env" >&2
  echo "Add FLR_CHALLENGE_API_KEY to ${ENV_FILE} and rerun." >&2
  exit 1
fi

TRAIN_CSV="${FLR_CHALLENGE_TRAIN_CSV_PATH:-{data_dir}/v2_train_data.csv}"
TEST_CSV="${FLR_CHALLENGE_TEST_CSV_PATH:-{data_dir}/v2_test_data.csv}"
if [[ "${TRAIN_CSV##*/}" != "v2_train_data.csv" ]]; then
  echo "FLR_CHALLENGE_TRAIN_CSV_PATH must point to v2_train_data.csv" >&2
  exit 1
fi
if [[ "${TEST_CSV##*/}" != "v2_test_data.csv" ]]; then
  echo "Warning: test data is not v2_test_data.csv; this is not production-equivalent." >&2
fi

LOCAL_TRAIN_CSV="${ROOT_DIR}/volumes/storage/flowradar-challenge/data/v2_train_data.csv"
LOCAL_TEST_CSV="${ROOT_DIR}/volumes/storage/flowradar-challenge/data/v2_test_data.csv"
if [[ ! -f "${LOCAL_TRAIN_CSV}" ]] || [[ $(wc -c < "${LOCAL_TRAIN_CSV}") -lt 1000000 ]]; then
  echo "v2_train_data.csv is missing or is still an LFS pointer." >&2
  echo "Run: git lfs pull" >&2
  exit 1
fi
if [[ ! -f "${LOCAL_TEST_CSV}" ]]; then
  echo "Missing production test data: ${LOCAL_TEST_CSV}" >&2
  exit 1
fi

echo "Using ENV=${ENV:-LOCAL} DEBUG=${DEBUG:-false}"
echo "Training dataset: ${TRAIN_CSV}"
echo "Scoring dataset: ${TEST_CSV}"

if [[ $# -gt 0 && "$1" == "--build" ]]; then
  docker compose up -d --build --remove-orphans
else
  docker compose up -d --remove-orphans
fi

echo "Challenge setup complete."
echo "Run healthcheck: ./skills/challenge-setup/scripts/healthcheck.sh"
