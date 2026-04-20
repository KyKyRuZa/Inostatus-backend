from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import timedelta
from app.database import get_db
from app.schemas.auth import (
    UserCreate,
    UserResponse,
    LoginRequest,
    TokenResponse,
    UserUpdate,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.services.auth import (
    get_user_by_email,
    create_user,
    update_user,
    verify_user_password,
    get_user_by_id,
    create_api_key,
    get_user_api_keys,
    deactivate_api_key,
    get_user_stats,
)
from app.utils.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    decode_token as jwt_decode_token,
)
from app.config import settings
from app.services.email import (
    send_welcome_email,
    send_verification_email,
    send_password_reset_email,
)
from app.services.audit_logger import log_login, log_register, log_failed_auth_attempt
from app.middleware.rate_limiter import limiter
from typing import Optional

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)


def _get_access_token(
    request: Request, credentials: Optional[HTTPAuthorizationCredentials] = None
) -> Optional[str]:
    if credentials:
        return credentials.credentials

    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1]

    return None


def _require_authenticated_user(
    request: Request,
    db: Session,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
):
    token = _get_access_token(request, credentials)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = jwt_decode_token(token)
    if not token_data or token_data.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен",
        )

    user = get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    return user


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("3/hour")
async def register(
    request: Request,
    response: Response,
    user_data: UserCreate,
    db: Session = Depends(get_db),
):
    existing_user = get_user_by_email(db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует",
        )

    user = create_user(db, user_data)

    log_register(user_id=str(user.id), request=request, email=user.email)

    await send_welcome_email(user.email, user.name or "")

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: Session = Depends(get_db),
):
    user = verify_user_password(
        db, email=login_data.email, password=login_data.password
    )
    if not user:
        log_failed_auth_attempt(
            identifier=login_data.email,
            request=request,
            failure_reason="invalid_credentials",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        log_failed_auth_attempt(
            identifier=login_data.email,
            request=request,
            failure_reason="account_deactivated",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован",
        )

    log_login(user_id=str(user.id), request=request, status="success")

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    body = await request.json() if request.headers.get("content-type") else {}
    refresh_token_str = body.get("refresh_token")

    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный refresh токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = jwt_decode_token(refresh_token_str)
    if not token_data or token_data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный refresh токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный refresh токен",
        )

    user = get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    new_access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(response: Response):
    return {"message": "Выход выполнен"}


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    user = _require_authenticated_user(request, db, credentials)
    return user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    request: Request,
    user_update: UserUpdate,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    user = _require_authenticated_user(request, db, credentials)

    if user_update.email and user_update.email != user.email:
        existing_user = get_user_by_email(db, user_update.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Пользователь с таким email уже существует",
            )

    updated_user = update_user(db, user, user_update)
    return updated_user


@router.post("/change-password")
async def change_password(
    request: Request,
    password_data: ChangePasswordRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    from app.utils.jwt import get_password_hash

    user = _require_authenticated_user(request, db, credentials)

    verified_user = verify_user_password(
        db, email=user.email, password=password_data.current_password
    )
    if not verified_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль",
        )

    if password_data.current_password == password_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Новый пароль не должен совпадать с текущим",
        )

    user.password_hash = get_password_hash(password_data.new_password)
    db.commit()

    return {"message": "Пароль успешно обновлён"}


@router.post("/forgot-password")
async def forgot_password(
    request_data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    from app.utils.jwt import create_password_reset_token

    user = get_user_by_email(db, email=request_data.email)
    if not user:
        return {"message": "Если пользователь существует, письмо отправлено"}

    reset_token = create_password_reset_token(user.id, user.email)
    await send_password_reset_email(user.email, reset_token)

    return {"message": "Если пользователь существует, письмо отправлено"}


@router.post("/reset-password")
async def reset_password(
    reset_data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    from app.utils.jwt import decode_password_reset_token, get_password_hash

    token_data = decode_password_reset_token(reset_data.token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или истёкший токен",
        )

    user_id = int(token_data.get("sub"))
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )

    user.password_hash = get_password_hash(reset_data.password)
    db.commit()

    return {"message": "Пароль успешно обновлён"}
