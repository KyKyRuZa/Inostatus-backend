from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

limiter = Limiter(key_func=get_remote_address)


def get_rate_limit() -> str:
    return f"{settings.RATE_LIMIT_PER_MINUTE}/minute"
