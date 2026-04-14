from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse
from app.config import settings
import os
import socket


def _is_docker_network_ip(ip: str) -> bool:
    if not ip:
        return False
    try:
        parts = ip.split(".")
        if len(parts) == 4:
            first_octet = int(parts[0])
            second_octet = int(parts[1])
            if first_octet == 172 and 16 <= second_octet <= 31:
                return True
    except (ValueError, IndexError):
        pass
    return False


def get_client_ip(request: Request) -> str:
    if settings.DISABLE_RATE_LIMIT:
        return "whitelisted"

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip in ["127.0.0.1", "::1", "localhost", "0.0.0.0"]:
            return "whitelisted"
        if _is_docker_network_ip(client_ip) and client_ip.endswith(".1"):
            return "whitelisted"
        return client_ip

    client_ip = request.client.host if request.client else "127.0.0.1"

    if client_ip in ["127.0.0.1", "::1", "localhost"]:
        return "whitelisted"

    if _is_docker_network_ip(client_ip) and client_ip.endswith(".1"):
        return "whitelisted"

    return client_ip


limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[
        "100/minute",
        "1000/hour",
    ],
    storage_uri="memory://",
)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Слишком много запросов. Пожалуйста, попробуйте позже.",
            "error": "rate_limit_exceeded",
            "retry_after": str(exc.detail).split(":")[-1].strip() if ":" in str(exc.detail) else "60"
        }
    )



