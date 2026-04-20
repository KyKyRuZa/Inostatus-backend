from fastapi import Response, Request
from typing import Optional


ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    # TODO
    pass


def clear_auth_cookies(response: Response) -> None:
     # TODO
    pass


def get_token_from_cookie(request: Request, cookie_name: str) -> Optional[str]:
     # TODO
    return None
