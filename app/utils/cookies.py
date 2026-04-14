from fastapi import Response, Request
from app.config import settings
from typing import Optional


ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"

ACCESS_TOKEN_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 30 минут
REFRESH_TOKEN_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # 7 дней


def _get_cookie_params() -> dict:
    is_prod = not settings.DEBUG

    return {
        "httponly": True,        # JS не может прочитать (защита от XSS)
        "secure": is_prod,       # Только HTTPS в production
        "samesite": "strict" if is_prod else "lax",
        "path": "/",
    }


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    cookie_params = _get_cookie_params()

    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        max_age=ACCESS_TOKEN_MAX_AGE,
        **cookie_params,
    )

    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        max_age=REFRESH_TOKEN_MAX_AGE,
        **cookie_params,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(key=REFRESH_TOKEN_COOKIE, path="/")


def get_token_from_cookie(request: Request, cookie_name: str) -> Optional[str]:
    return request.cookies.get(cookie_name)
