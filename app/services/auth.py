from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.user import User, APIKey, CheckHistory
from app.schemas.auth import UserCreate, UserUpdate
from app.utils.jwt import get_password_hash, verify_password
from datetime import datetime
import secrets
import httpx
from app.config import settings
from typing import Optional


class ExternalAPIError(Exception):
    pass


async def get_external_api_stats(api_key: str) -> dict:
    api_base_url = settings.CHECK_FILES_API_URL
    
    url = f"{api_base_url}/stats"
    
    headers = {
        "X-API-Key": api_key,
        "IntegratorID": settings.INTEGRATOR_ID,
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 403:
                raise ExternalAPIError("Неверный API ключ")
            elif response.status_code == 404:
                raise ExternalAPIError("API ключ не найден")
            elif response.status_code == 429:
                raise ExternalAPIError("Превышен лимит запросов")
            elif response.status_code != 200:
                raise ExternalAPIError(f"Ошибка API: {response.status_code}")
            
            return response.json()
            
    except httpx.RequestError as e:
        raise ExternalAPIError(f"Ошибка соединения: {str(e)}")


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user: UserCreate) -> User:
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        password_hash=hashed_password,
        name=user.name,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user: User, user_update: UserUpdate) -> User:
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def verify_user_password(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user



def create_api_key(
    db: Session,
    user_id: int,
    name: str | None = None,
    key_type: str = "free",
    max_uses: int = 2
) -> APIKey:
    api_key = f"sk_{secrets.token_urlsafe(32)}"
    db_api_key = APIKey(
        user_id=user_id,
        key=api_key,
        name=name,
        key_type=key_type,
        max_uses=max_uses,
        used_count=0,
    )
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    return db_api_key


def get_api_key_by_key(db: Session, key: str) -> APIKey | None:
    return db.query(APIKey).filter(APIKey.key == key).first()


def get_user_api_keys(db: Session, user_id: int) -> list[APIKey]:
    return db.query(APIKey).filter(APIKey.user_id == user_id).all()


def deactivate_api_key(db: Session, api_key: APIKey) -> APIKey:
    api_key.is_active = False
    db.commit()
    db.refresh(api_key)
    return api_key


def update_api_key_last_used(db: Session, api_key: APIKey) -> APIKey:
    api_key.last_used_at = datetime.utcnow()
    db.commit()
    db.refresh(api_key)
    return api_key


def increment_api_key_usage(db: Session, api_key: APIKey) -> APIKey:
    api_key.used_count += 1
    api_key.last_used_at = datetime.utcnow()
    db.commit()
    db.refresh(api_key)
    return api_key



def create_check_history(
    db: Session,
    user_id: int | None,
    text: str,
    filename: str | None = None,
    result: str | None = None,
    similarity_score: float = 0.0,
    api_key_id: int | None = None,
) -> CheckHistory:
    check = CheckHistory(
        user_id=user_id,
        text=text,
        filename=filename,
        result=result,
        similarity_score=similarity_score,
        api_key_id=api_key_id,
    )
    db.add(check)
    db.commit()
    db.refresh(check)
    return check


def get_user_check_history(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[CheckHistory]:
    return (
        db.query(CheckHistory)
        .filter(CheckHistory.user_id == user_id)
        .order_by(CheckHistory.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_check_by_id(db: Session, check_id: int, user_id: int) -> CheckHistory | None:
    return (
        db.query(CheckHistory)
        .filter(CheckHistory.id == check_id, CheckHistory.user_id == user_id)
        .first()
    )


def get_user_stats(db: Session, user_id: int) -> dict:
    total_checks = (
        db.query(func.count(CheckHistory.id))
        .filter(CheckHistory.user_id == user_id)
        .scalar()
    )
    total_api_keys = (
        db.query(func.count(APIKey.id))
        .filter(APIKey.user_id == user_id)
        .scalar()
    )
    active_api_keys = (
        db.query(func.count(APIKey.id))
        .filter(APIKey.user_id == user_id, APIKey.is_active == True)
        .scalar()
    )

    return {
        "total_checks": total_checks,
        "total_api_keys": total_api_keys,
        "active_api_keys": active_api_keys,
    }
