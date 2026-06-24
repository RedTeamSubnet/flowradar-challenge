import sys
import json
import logging
import os
import signal
import subprocess
import tempfile
import threading
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
_MODEL = None
_TRAINING_LOCK = threading.Lock()


def _load_model() -> object:
    model_path = os.getenv("FLOWRADAR_MODEL_PATH", "/tmp/model.json")
    if not os.path.exists(model_path):
        logger.warning("Model JSON not found at %s; using empty model", model_path)
        return {}
    with open(model_path, encoding="utf-8") as model_file:
        return json.load(model_file)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/train")
def train() -> dict[str, int | str]:
    global _MODEL

    if not _TRAINING_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Training is already in progress.")

    training_path = os.getenv("FLOWRADAR_TRAINING_PATH", "/app/train.py")
    training_csv_path = os.getenv(
        "FLOWRADAR_TRAINING_CSV_PATH", "/data/training.csv"
    )
    model_path = os.getenv("FLOWRADAR_MODEL_PATH", "/tmp/model.json")
    timeout = float(os.getenv("FLOWRADAR_TRAINING_TIMEOUT_SECONDS", "600"))
    size_limit = int(
        os.getenv("FLOWRADAR_MODEL_JSON_SIZE_LIMIT", str(20 * 1024 * 1024))
    )

    try:
        _MODEL = None
        if os.path.exists(model_path):
            os.remove(model_path)

        with tempfile.TemporaryFile(mode="w+b") as output:
            process = subprocess.Popen(
                [sys.executable, training_path, training_csv_path, model_path],
                cwd="/tmp",
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                return_code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise HTTPException(status_code=408, detail="Training timed out.")

            output.seek(0, os.SEEK_END)
            output_size = output.tell()
            output.seek(max(0, output_size - 4000))
            training_output = output.read().decode("utf-8", errors="replace")
            if training_output:
                logger.info("Training output:\n%s", training_output)

        if return_code != 0:
            raise HTTPException(
                status_code=422,
                detail=f"Training failed with exit code {return_code}.",
            )
        if not os.path.isfile(model_path):
            raise HTTPException(
                status_code=422, detail="Training did not create model JSON."
            )

        model_size = os.path.getsize(model_path)
        if model_size > size_limit:
            raise HTTPException(
                status_code=413,
                detail=f"Model JSON exceeds the {size_limit}-byte limit.",
            )

        try:
            _MODEL = _load_model()
        except (json.JSONDecodeError, OSError) as exc:
            raise HTTPException(
                status_code=422, detail="Training produced invalid model JSON."
            ) from exc

        return {"status": "trained", "model_size_bytes": model_size}
    finally:
        _TRAINING_LOCK.release()


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
        if _MODEL is None:
            raise HTTPException(status_code=409, detail="Model has not been trained.")
        is_vpn = detect_vpn(vpn_input.products, _MODEL)

        return VPNDetectionOutput(
            is_vpn=is_vpn,
            request_id=_request_id,
        )
    except HTTPException:
        raise
    except Exception as err:
        logger.error(f"Failed to process fingerprint: {str(err)}")
        raise HTTPException(status_code=500, detail="Failed to process fingerprint.")


__all__ = ["app"]
