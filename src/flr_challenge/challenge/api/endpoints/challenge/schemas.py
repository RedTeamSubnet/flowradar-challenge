import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator

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


class CommitFile(BaseModel):
    file_name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        title="File Name",
        description="Submission file name. Must be train.py or submissions.py.",
    )
    content: str = Field(
        ...,
        min_length=1,
        title="File Content",
        description="Complete Python source for this submission file.",
    )

    @field_validator("file_name", mode="after")
    @classmethod
    def _check_file_name(cls, value: str) -> str:
        if value not in {"train.py", "submissions.py"}:
            raise ValueError("file_name must be 'train.py' or 'submissions.py'")
        return value

    @field_validator("content", mode="after")
    @classmethod
    def _check_content(cls, value: str) -> str:
        if config.challenge.submission_length_limit is not None:
            line_count = len(value.splitlines())
            if line_count > config.challenge.submission_length_limit:
                raise ValueError(
                    f"Commit file exceeds the line limit of {config.challenge.submission_length_limit}. "
                    f"Current line count: {line_count}."
                )
        return value


class MinerOutput(BaseModel):
    commit_files: list[CommitFile] = Field(
        ...,
        min_length=2,
        max_length=2,
        title="Commit Files",
        description=(
            "Exactly train.py and submissions.py. Embedded or pretrained learned "
            "weights are prohibited; inference may only use the model generated "
            "by train.py during the current scoring run."
        ),
        examples=[
            [
                {
                    "file_name": "train.py",
                    "content": (
                        _training_py
                        if _training_py
                        else "import json, sys\njson.dump({}, open(sys.argv[2], 'w'))\n"
                    ),
                },
                {
                    "file_name": "submissions.py",
                    "content": (
                        _submission_py
                        if _submission_py
                        else "def detect_vpn(features, model):\n    return False\n"
                    ),
                },
            ]
        ],
    )

    @model_validator(mode="after")
    def _check_required_files(self) -> "MinerOutput":
        file_names = [commit_file.file_name for commit_file in self.commit_files]
        if set(file_names) != {"train.py", "submissions.py"}:
            raise ValueError(
                "commit_files must contain exactly one train.py and one submissions.py"
            )
        return self

    def get_file_content(self, file_name: str) -> str:
        for commit_file in self.commit_files:
            if commit_file.file_name == file_name:
                return commit_file.content
        raise ValueError(f"Missing required commit file: {file_name}")


class ScoringTelemetryResponse(BaseModel):
    request_id: str | None = Field(
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
    score: float | None = Field(
        default=None,
        title="Score",
        description="The computed score for this scoring run.",
        ge=0,
        le=1,
    )


__all__ = [
    "MinerInput",
    "CommitFile",
    "MinerOutput",
    "ScoringTelemetryResponse",
]
