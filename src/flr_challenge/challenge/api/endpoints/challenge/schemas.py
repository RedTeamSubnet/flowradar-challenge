import os
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from potato_util.generator import gen_random_string

from api.config import config
from api.logger import logger

api_dir = os.environ.get("FLR_CHALLENGE_API_DIR", "/app/historical_fingerprinter")
_submission_path = Path(os.path.join(api_dir, "fingerprinter", "src", "submissions"))
_frameworks_names = config.challenge.submission_fns
_detection_files: dict[list[dict[str, Any]]] = {"commit_files": []}

try:
    if _submission_path.exists():
        for _detection_path in _submission_path.glob("*.py"):
            _file_stem = _detection_path.stem
            if _file_stem in _frameworks_names:
                with open(_detection_path) as _detection_file:
                    _detection_files["commit_files"].append(
                        {
                            "file_name": _detection_path.name,
                            "content": _detection_file.read(),
                        }
                    )

except Exception:
    logger.exception("Failed to read detection files in detections folder!")


class MinerInput(BaseModel):
    random_val: str | None = Field(
        default_factory=gen_random_string,
        title="Random Value",
        description="Random value to prevent caching.",
        examples=["a1b2c3d4e5f6g7h8"],
    )


class CommitFilePM(BaseModel):
    file_name: str = Field(
        ...,
        min_length=4,
        max_length=64,
        title="File Name",
        description="Name of the file.",
        examples=["solution.js"],
    )
    content: str = Field(
        ...,
        min_length=2,
        title="File Content",
        description="Content of the file as a string.",
        examples=["console.log('Challenge accepted!');"],
    )


class MinerOutput(BaseModel):
    commit_files: list[CommitFilePM] = Field(
        ...,
        title="Commit Files",
        description="List of Commit files for the challenge.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": (
                [_detection_files]
                if _detection_files
                else [
                    {"file_name": "initializer.py", "content": "# initializer code"},
                    {
                        "file_name": "metrics_collector.py",
                        "content": "# metrics_collector code",
                    },
                    {"file_name": "linker.py", "content": "# linker code"},
                ]
            )
        }
    }

    @field_validator("commit_files", mode="after")
    @classmethod
    def _check_commit_files(cls, val: list[CommitFilePM]) -> list[CommitFilePM]:
        """
        Validate the commit files based on the challenge configuration.
            - The number of submitted files should match the expected count.
            - Each file should not exceed the line limit.
            - Each file should have a valid name and extension.
        """
        if len(val) != len(config.challenge.submission_fns):
            raise ValueError(
                f"Number of submitted files should be exactly {len(config.challenge.submission_fns)}!"
            )
        for _miner_file_pm in val:
            _content_lines = _miner_file_pm.content.splitlines()
            if len(_content_lines) > config.challenge.submission_length_limit:
                raise ValueError(
                    f"`{_miner_file_pm.file_name}` file contains too many lines, should be \
                        <= {config.challenge.submission_length_limit} lines!"
                )
            _miner_file_name = _miner_file_pm.file_name.strip().split(".")
            if _miner_file_name[-1] != "py":
                raise ValueError(
                    f"`{_miner_file_pm.file_name}` file has invalid extension, should be `.py`!"
                )
            elif _miner_file_name[0] not in config.challenge.submission_fns:
                raise ValueError(
                    f"`{_miner_file_pm.file_name}` file has invalid name, should be one of \
                        {config.challenge.submission_fns}!"
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
    "CommitFilePM",
    "MinerOutput",
    "ScoringTelemetryResponse",
]
