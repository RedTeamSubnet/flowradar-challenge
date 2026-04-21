from pydantic import BaseModel, Field


class VPNDetectionInput(BaseModel):
    products: dict = Field(
        ...,
        title="Products",
        description="Raw network flow features from CSV row.",
    )


class VPNDetectionOutput(BaseModel):
    is_vpn: bool = Field(
        ...,
        title="Is VPN",
        description="Whether the traffic is detected as VPN.",
    )
    request_id: str = Field(
        ...,
        title="Request ID",
        description="Unique identifier for the request.",
    )


__all__ = [
    "VPNDetectionInput",
    "VPNDetectionOutput",
]