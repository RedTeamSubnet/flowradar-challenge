import sys
import logging
from uuid import uuid4

from fastapi import FastAPI, Body, HTTPException, Request

from data_types import VPNDetectionInput, VPNDetectionOutput
from submissions import detect_vpn

logger = logging.getLogger(__name__)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S %z",
    format="[%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d]: %(message)s",
)


app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/vpn_detector", response_model=VPNDetectionOutput)
def fingerprint(
    request: Request, vpn_input: VPNDetectionInput = Body(...)
) -> VPNDetectionOutput:
    logger.info("Processing fingerprint request...")
    # Generate a unique request ID for tracing
    _request_id: str = uuid4().hex
    if "X-Request-ID" in request.headers:
        _request_id: str = request.headers.get("X-Request-ID", _request_id)
    elif "X-Correlation-ID" in request.headers:
        _request_id: str = request.headers.get("X-Correlation-ID", _request_id)
    try:
        is_vpn = detect_vpn(vpn_input.products)

        return VPNDetectionOutput(
            is_vpn=is_vpn,
            request_id=_request_id,
        )
    except Exception as err:
        logger.error(f"Failed to process fingerprint: {str(err)}")
        raise HTTPException(status_code=500, detail="Failed to process fingerprint.")


__all__ = ["app"]
