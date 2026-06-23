import os
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from potato_util.generator import gen_random_string

from api.config import config
from api.logger import logger

api_dir = os.environ.get("FLR_API_DIR", "/app/flowradar-challenge")
_submission_path = Path(os.path.join(api_dir, "flowradar", "src", "submissions.py"))
_training_path = Path(os.path.join(api_dir, "flowradar", "src", "train.py"))
_submission_py = ""
_training_py = ""
try:
    if _submission_path.exists():
        with open(_submission_path) as _submission_file:
            _submission_py = _submission_file.read()
    if _training_path.exists():
        with open(_training_path) as _training_file:
            _training_py = _training_file.read()

except Exception:
    logger.exception("Failed to read example submission files!")


class MinerInput(BaseModel):
    random_val: str | None = Field(
        default_factory=gen_random_string,
        title="Random Value",
        description="Random value to prevent caching.",
        examples=["a1b2c3d4e5f6g7h8"],
    )


class MinerOutput(BaseModel):
    train_script: str = Field(
        ...,
        title="Training Python File",
        description=(
            "Python script content. It is called as "
            "`python train.py <training_csv> <model_json>` and must write model JSON."
        ),
        examples=[
            (
                _training_py
                if _training_py
                else "import json, sys\njson.dump({}, open(sys.argv[2], 'w'))\n"
            )
        ],
    )
    inference_script: str = Field(
        ...,
        title="Inference Python File",
        description=(
            "Python script content exposing `detect_vpn(features, model)` "
            "or legacy `detect_vpn(features)`."
        ),
        examples=[
            (
                _submission_py
                if _submission_py
                else "def detect_vpn(features, model):\n    return False\n"
            )
        ],
    )

    @field_validator("train_script", "inference_script", mode="after")
    @classmethod
    def _check_submission_py(cls, val: str) -> str:
        """
        Validate submitted scripts based on the challenge configuration.
            - Each file should not exceed the line limit.
        """
        if config.challenge.submission_length_limit is not None:
            line_count = len(val.splitlines())
            if line_count > config.challenge.submission_length_limit:
                raise ValueError(
                    f"Submission script exceeds the line limit of {config.challenge.submission_length_limit}. "
                    f"Current line count: {line_count}."
                )

        return val


class ScoringTelemetryResponse(BaseModel):
    request_id: Optional[str] = Field(
        default=None,
        title="Request ID",
        description="The request ID for this scoring run.",
    )
    total_file_size_bytes: int = Field(
        default=0,
        title="Total File Size",
        description="Total size of submission files in bytes.",
        ge=0,
    )
    runtime_seconds: float = Field(
        default=0.0,
        title="Runtime",
        description="Time taken to complete scoring in seconds.",
        ge=0,
    )
    network_rx_bytes: int = Field(
        default=0,
        title="Network RX Bytes",
        description="Total network bytes received during scoring.",
        ge=0,
    )
    network_tx_bytes: int = Field(
        default=0,
        title="Network TX Bytes",
        description="Total network bytes transmitted during scoring.",
        ge=0,
    )
    score: Optional[float] = Field(
        default=None,
        title="Score",
        description="The computed score for this scoring run.",
        ge=0,
        le=1,
    )


__all__ = [
    "MinerInput",
    "MinerOutput",
    "ScoringTelemetryResponse",
]
