from pydantic import BaseModel, Field, field_validator, model_validator


class MinerInput(BaseModel):
    random_val: str | None = Field(
        default=None,
        min_length=4,
        max_length=64,
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
    )
    content: str = Field(
        ...,
        min_length=1,
        title="File Content",
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
        _content_lines = value.splitlines()
        if len(_content_lines) > 1000:
            raise ValueError(
                "Commit file contains too many lines, should be <= 1000 lines!"
            )
        return value


class MinerOutput(BaseModel):
    commit_files: list[CommitFile] = Field(
        ...,
        min_length=2,
        max_length=2,
        description=(
            "Exactly train.py and submissions.py. Learned weights must be generated "
            "during the current run and must not be embedded in either file."
        ),
    )

    @model_validator(mode="after")
    def _check_required_files(self) -> "MinerOutput":
        file_names = [commit_file.file_name for commit_file in self.commit_files]
        if set(file_names) != {"train.py", "submissions.py"}:
            raise ValueError(
                "commit_files must contain exactly one train.py and one submissions.py"
            )
        return self


__all__ = [
    "MinerInput",
    "CommitFile",
    "MinerOutput",
]
