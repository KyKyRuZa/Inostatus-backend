from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.auth import (
    APIKeyCreate,
    APIKeyResponse,
    CheckHistoryResponse,
    CheckResultResponse,
)
from app.services.auth import (
    create_api_key,
    get_user_api_keys,
    deactivate_api_key,
    get_api_key_by_key,
    update_api_key_last_used,
    create_check_history,
    get_user_check_history,
    get_check_by_id,
    get_user_stats,
    get_external_api_stats,
    ExternalAPIError,
)
from app.utils.jwt import decode_token
from app.utils.cookies import get_token_from_cookie, ACCESS_TOKEN_COOKIE
from typing import Optional

router = APIRouter(prefix="/api", tags=["Profile"])
security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> int:
    token = get_token_from_cookie(request, ACCESS_TOKEN_COOKIE)
    
    if not token and credentials:
        token = credentials.credentials
    
    if not token:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = decode_token(token)
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

    return int(user_id)



@router.get("/profile/stats")
async def get_profile_stats(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    stats = get_user_stats(db, user_id)
    return stats



@router.get("/profile/keys", response_model=list[APIKeyResponse])
async def get_api_keys(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return get_user_api_keys(db, user_id)


@router.post("/profile/keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_new_api_key(
    key_data: APIKeyCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return create_api_key(
        db,
        user_id,
        key_data.name,
        key_data.key_type or "free",
        key_data.max_uses or 2
    )


@router.delete("/profile/keys/{key_id}")
async def delete_api_key(
    key_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    api_key = get_api_key_by_key(db, str(key_id))
    if not api_key:
        from app.services.auth import get_user_api_keys
        all_keys = get_user_api_keys(db, user_id)
        api_key = next((k for k in all_keys if k.id == key_id), None)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API-ключ не найден",
        )

    if api_key.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для управления этим ключом",
        )

    deactivate_api_key(db, api_key)
    return {"message": "API-ключ деактивирован"}


@router.get("/profile/keys/{key_id}/stats")
async def get_api_key_external_stats(
    key_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    api_key = get_api_key_by_key(db, str(key_id))
    if not api_key:
        from app.services.auth import get_user_api_keys
        all_keys = get_user_api_keys(db, user_id)
        api_key = next((k for k in all_keys if k.id == key_id), None)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API-ключ не найден",
        )

    if api_key.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для просмотра статистики этого ключа",
        )

    try:
        external_stats = await get_external_api_stats(api_key.key)
        
        return {
            "key_id": key_id,
            "key": api_key.key[:10] + "...",  # Показываем только начало ключа
            "limit": external_stats.get("limit"),
            "active_tasks": external_stats.get("active_tasks"),
            "total_processed": external_stats.get("total_processed"),
            "remaining": external_stats.get("remaining"),
            "tasks_history": external_stats.get("tasks_history", []),
        }
        
    except ExternalAPIError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )



@router.get("/profile/history", response_model=list[CheckHistoryResponse])
async def get_check_history(
    skip: int = 0,
    limit: int = 100,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    return get_user_check_history(db, user_id, skip=skip, limit=limit)


@router.get("/profile/history/{check_id}")
async def get_check_result(
    check_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    check = get_check_by_id(db, check_id, user_id)
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Проверка не найдена",
        )

    import json
    try:
        result_data = json.loads(check.result) if check.result else {}
    except:
        result_data = {}
    
    return {
        "id": check.id,
        "text": check.text,
        "filename": check.filename,
        "result": check.result,
        "similarity_score": check.similarity_score,
        "created_at": check.created_at.isoformat() if check.created_at else None,
        "discalimer": result_data.get("discalimer"),
        "discalimer2": result_data.get("discalimer2"),
        "discalimer3": result_data.get("discalimer3"),
        "check_time": result_data.get("check_time", check.created_at.strftime("%d.%m.%Y %H:%M:%S") if check.created_at else None),
        "standart_check": result_data.get("standart_check"),
        "translit_check": result_data.get("translit_check"),
        "database_info": result_data.get("database_info"),
    }
