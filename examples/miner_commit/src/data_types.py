from pydantic import BaseModel, Field, field_validator


class MinerInput(BaseModel):
    random_val: str | None = Field(
        default=None,
        min_length=4,
        max_length=64,
        title="Random Value",
        description="Random value to prevent caching.",
        examples=["a1b2c3d4e5f6g7h8"],
    )


class MinerOutput(BaseModel):
    commit_files: str = Field(
        ...,
        title="Commit Files",
        description="List of Commit files for the challenge.",
    )

    @field_validator("commit_files", mode="after")
    @classmethod
    def _check_commit_files(cls, val: str) -> str:
        _content_lines = val.splitlines()
        if len(_content_lines) > 1000:
            raise ValueError(
                f"Commit files contain too many lines, should be <= 1000 lines!"
            )

        return val


__all__ = [
    "MinerInput",
    "MinerOutput",
]
