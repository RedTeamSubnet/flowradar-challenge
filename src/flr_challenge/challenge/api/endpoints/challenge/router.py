from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse

from api.core.constants import ErrorCodeEnum
from api.core.exceptions import BaseHTTPException
from api.logger import logger
from api.core.dependencies.auth import auth_api_key
from .schemas import MinerInput, MinerOutput, ScoringTelemetryResponse
from . import service
from .payload_managers import (
    payload_manager,
    scoring_status_manager,
    scoring_telemetry_manager,
)

router = APIRouter(tags=["Challenge"])


@router.get(
    "/status",
    summary="Get status",
    description="This endpoint returns the current scoring status.",
    response_class=JSONResponse,
)
def get_status(request: Request):
    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Getting status...")

    status = scoring_status_manager.get_scoring_status()
    return {"status": status}


@router.get(
    "/results",
    summary="Get results",
    description="This endpoint returns the fingerprint storage.",
    response_class=JSONResponse,
)
def get_results(request: Request):
    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Getting results...")

    results = payload_manager.get_payload()
    return results


@router.get(
    "/telemetry",
    summary="Get telemetry",
    description="This endpoint returns the scoring telemetry from the latest run.",
    response_class=JSONResponse,
    response_model=ScoringTelemetryResponse,
)
def get_telemetry(request: Request):
    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Getting telemetry...")

    telemetry = scoring_telemetry_manager.get_telemetry()
    return telemetry


@router.get(
    "/task",
    summary="Get task",
    description="This endpoint returns the task for the miner.",
    response_class=JSONResponse,
    response_model=MinerInput,
)
def get_task(request: Request):

    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Getting task...")

    _miner_input: MinerInput
    try:
        _miner_input = service.get_task()

        logger.success(f"[{_request_id}] - Successfully got the task.")
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"[{_request_id}] - Failed to get task!")
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.INTERNAL_SERVER_ERROR,
            message="Failed to get task!",
        )

    return _miner_input


@router.post(
    "/score",
    summary="Score",
    description="This endpoint score miner output.",
    response_class=JSONResponse,
    responses={422: {}},
    dependencies=[Depends(auth_api_key)],
)
def post_score(request: Request, miner_input: MinerInput, miner_output: MinerOutput):

    _request_id = request.state.request_id
    logger.info(f"[{_request_id}] - Scoring the miner output...")
    score = 0
    try:
        score = service.score(request_id=_request_id, miner_output=miner_output)
        logger.success(f"[{_request_id}] - Successfully scored the miner output")
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"[{_request_id}] - Failed to score the miner output!")
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.INTERNAL_SERVER_ERROR,
            message="Failed to score the miner output!",
        )

    return score


__all__ = ["router"]
