#!/usr/bin/env python3

import json
import os
import secrets
import sys
from pathlib import Path
from urllib import error, request


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def main() -> int:
    root_dir = Path(__file__).resolve().parents[3]
    _load_env_file(root_dir / ".env")

    api_key = os.environ.get("FLR_CHALLENGE_API_KEY")
    if not api_key:
        print("FLR_CHALLENGE_API_KEY is not set", file=sys.stderr)
        return 1

    flowradar_src = root_dir / "src/flr_challenge/challenge/flowradar/src"
    training_file = flowradar_src / "train.py"
    submission_file = flowradar_src / "submissions.py"

    if not training_file.exists():
        print(f"Missing training file: {training_file}", file=sys.stderr)
        return 1
    if not submission_file.exists():
        print(f"Missing submission file: {submission_file}", file=sys.stderr)
        return 1

    try:
        train_script = training_file.read_text(encoding="utf-8")
        inference_script = submission_file.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Failed to read submission files: {exc}", file=sys.stderr)
        return 1

    payload = {
        "miner_input": {"random_val": secrets.token_hex(8)},
        "miner_output": {
            "train_script": train_script,
            "inference_script": inference_script,
        },
    }

    req = request.Request(
        "http://localhost:10001/score",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(body or str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(raw)
        return 0

    if isinstance(data, dict) and "score" in data:
        print(data["score"])
        return 0
    if isinstance(data, (int, float)):
        print(data)
        return 0

    print(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
