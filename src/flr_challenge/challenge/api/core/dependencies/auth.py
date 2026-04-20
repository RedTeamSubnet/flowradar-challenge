import re

from fastapi import Security
from fastapi.security import APIKeyHeader

from api.config import config
from api.core.constants import ErrorCodeEnum, ALPHANUM_HYPHEN_REGEX
from api.core.exceptions import BaseHTTPException

_auth_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def auth_api_key(api_key: str | None = Security(_auth_header)) -> None:

    if (not api_key) or (not isinstance(api_key, str)) or (not api_key.strip()):
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.UNAUTHORIZED,
            message="Not authenticated!",
            headers={"WWW-Authenticate": 'X-API-Key error="missing_api_key"'},
        )

    if (len(api_key) <= 8) or (128 < len(api_key)):
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.UNAUTHORIZED,
            message="Invalid API key!",
            headers={"WWW-Authenticate": 'X-API-Key error="invalid_api_key"'},
        )

    if not bool(re.match(pattern=ALPHANUM_HYPHEN_REGEX, string=api_key)):
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.UNAUTHORIZED,
            message="Invalid API key!",
            headers={"WWW-Authenticate": 'X-API-Key error="invalid_api_key"'},
        )

    if api_key != config.challenge.api_key.get_secret_value():
        raise BaseHTTPException(
            error_enum=ErrorCodeEnum.UNAUTHORIZED,
            message="Invalid API key!",
            headers={"WWW-Authenticate": 'X-API-Key error="invalid_api_key"'},
        )

    return


__all__ = [
    "auth_api_key",
]
