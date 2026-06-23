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
    train_script: str = Field(
        ...,
        title="Training Script",
        description="Script called as `python train.py <training_csv> <model_json>`.",
    )
    inference_script: str = Field(
        ...,
        title="Inference Script",
        description="Script exposing `detect_vpn(features, model)`.",
    )

    @field_validator("train_script", "inference_script", mode="after")
    @classmethod
    def _check_scripts(cls, val: str) -> str:
        _content_lines = val.splitlines()
        if len(_content_lines) > 1000:
            raise ValueError(
                "Commit script contains too many lines, should be <= 1000 lines!"
            )

        return val


__all__ = [
    "MinerInput",
    "MinerOutput",
]
