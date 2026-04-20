from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Header,
    Request,
    UploadFile,
    File,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime
import json
from typing import Optional
from app.database import get_db
from app.models.user import APIKey
from app.schemas.auth import (
    CheckRequest,
    CheckResponse,
    FileUploadResponse,
    TaskStatusResponse,
    CheckResultResponse,
    CheckWebsiteRequest,
)
from app.services.auth import (
    create_check_history,
    get_api_key_by_key,
    update_api_key_last_used,
    increment_api_key_usage,
)
from app.utils.jwt import decode_token
from app.services.check import (
    check_text_fragment,
    check_website,
    calculate_similarity_score,
    process_file,
    get_task_status,
    download_json_result,
    download_pdf_result,
    calculate_file_similarity_score,
    CheckServiceError,
    FileUploadError,
    TaskStatusError,
    DownloadError,
    TaskTimeoutError,
)
from app.utils.rate_limiter import limiter
from app.config import settings

router = APIRouter(prefix="/api/check", tags=["Check"])
security = HTTPBearer(auto_error=False)


async def get_user_id_from_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> tuple[int, int | None]:
    if credentials:
        token_data = decode_token(credentials.credentials)
        if not token_data or token_data.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный токен",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user_id = token_data.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен"
            )
        return int(user_id), None

    elif x_api_key:
        db = next(get_db())
        api_key = get_api_key_by_key(db, x_api_key)
        if not api_key or not api_key.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный или неактивный API-ключ",
            )
        return api_key.user_id, api_key.id

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация (JWT токен или X-API-Key)",
        )


def validate_file(file: UploadFile) -> None:
    filename = file.filename or ""
    extension = filename.split(".")[-1].lower() if "." in filename else ""
    allowed_extensions = settings.ALLOWED_FILE_TYPES.split(",")

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неподдерживаемый формат. Разрешены: {', '.join(allowed_extensions)}",
        )


@router.post("/fragment", response_model=CheckResponse)
@limiter.limit("60/minute")
async def check_fragment(
    request: Request,
    check_data: CheckRequest,
    db: Session = Depends(get_db),
    auth_result: tuple[int, int | None] = Depends(get_user_id_from_auth),
):
    user_id, api_key_id = auth_result

    effective_api_key_id = (
        check_data.api_key_id if check_data.api_key_id else api_key_id
    )

    max_length = (
        settings.MAX_TEXT_LENGTH_PROFILE
        if effective_api_key_id
        else settings.MAX_TEXT_LENGTH_FREE
    )

    if len(check_data.text) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Превышен лимит {max_length} символов",
        )

    if effective_api_key_id:
        api_key = db.query(APIKey).filter(APIKey.id == effective_api_key_id).first()
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API-ключ не найден",
            )
        if not api_key.can_use():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Лимит ключа исчерпан. Осталось: {api_key.remaining}",
            )

    try:
        external_api_key = check_data.api_key

        if not external_api_key and effective_api_key_id:
            api_key_obj = (
                db.query(APIKey).filter(APIKey.id == effective_api_key_id).first()
            )
            if api_key_obj:
                external_api_key = api_key_obj.key

        result = await check_text_fragment(
            text=check_data.text,
            filename=check_data.filename or "site_fragment_1",
            api_key=external_api_key,
        )

        similarity_score = calculate_similarity_score(result)

        check = create_check_history(
            db=db,
            user_id=user_id,
            text=check_data.text,
            filename=check_data.filename,
            result=json.dumps(result, ensure_ascii=False),
            similarity_score=similarity_score,
            api_key_id=effective_api_key_id,
            check_type="text",
        )

        if effective_api_key_id and api_key:
            increment_api_key_usage(db, api_key)

        return CheckResponse(
            id=check.id,
            text=check.text,
            filename=check.filename,
            result=check.result,
            similarity_score=check.similarity_score,
            created_at=check.created_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ошибка сервиса проверки: {str(e)}",
        )


@router.post("/fragment/public", response_model=CheckResponse)
@limiter.limit("10/minute")
async def check_fragment_public(
    request: Request,
    check_data: CheckRequest,
    db: Session = Depends(get_db),
):
    max_length = settings.MAX_TEXT_LENGTH_FREE

    if len(check_data.text) > max_length:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Превышен лимит {max_length} символов для бесплатной проверки",
        )

    if not check_data.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Текст не может быть пустым",
        )

    try:
        external_api_key = check_data.api_key

        result = await check_text_fragment(
            text=check_data.text,
            filename=check_data.filename or "public_check",
            api_key=external_api_key,
        )

        similarity_score = calculate_similarity_score(result)

        check = create_check_history(
            db=db,
            user_id=None,
            text=check_data.text,
            filename=check_data.filename,
            result=json.dumps(result, ensure_ascii=False),
            similarity_score=similarity_score,
            api_key_id=None,
            check_type="text",
        )

        return CheckResponse(
            id=check.id,
            text=check.text,
            filename=check.filename,
            result=check.result,
            similarity_score=check.similarity_score,
            created_at=check.created_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ошибка сервиса проверки: {str(e)}",
        )


@router.post("/check_website", response_model=CheckResponse)
@limiter.limit("60/minute")
async def check_website_endpoint(
    request: Request,
    check_data: CheckWebsiteRequest,
    db: Session = Depends(get_db),
    auth_result: tuple[int, int | None] = Depends(get_user_id_from_auth),
):
    user_id, api_key_id = auth_result

    effective_api_key_id = api_key_id

    if effective_api_key_id:
        api_key = db.query(APIKey).filter(APIKey.id == effective_api_key_id).first()
        if not api_key or not api_key.can_use():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Лимит ключа исчерпан. Осталось: {api_key.remaining if api_key else 0}",
            )

    try:
        external_api_key = None
        if effective_api_key_id:
            api_key_obj = (
                db.query(APIKey).filter(APIKey.id == effective_api_key_id).first()
            )
            external_api_key = api_key_obj.key if api_key_obj else None

        result = await check_website(
            url=str(check_data.url),
            filename=check_data.filename,
            api_key=external_api_key,
        )

        similarity_score = calculate_similarity_score(result)

        check = create_check_history(
            db=db,
            user_id=user_id,
            text=str(check_data.url),
            filename=check_data.filename or str(check_data.url),
            result=json.dumps(result, ensure_ascii=False),
            similarity_score=similarity_score,
            api_key_id=effective_api_key_id,
            check_type="website",
        )

        if effective_api_key_id and api_key:
            increment_api_key_usage(db, api_key)

        return CheckResponse(
            id=check.id,
            text=check.text,
            filename=check.filename,
            result=check.result,
            similarity_score=check.similarity_score,
            created_at=check.created_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Ошибка сервиса проверки: {str(e)}",
        )


@router.post("/upload", response_model=FileUploadResponse)
@limiter.limit("30/minute")
async def upload_file(
    request: Request,
    file: UploadFile = File(..., description="Файл для проверки (PDF, TXT, DOCX)"),
    db: Session = Depends(get_db),
    auth_result: tuple[int, int | None] = Depends(get_user_id_from_auth),
):
    import logging

    logger = logging.getLogger(__name__)

    user_id, api_key_id = auth_result

    try:
        content = await file.read()

        logger.info(
            f"Received file: filename={file.filename}, size={len(content)} bytes, content_type={file.content_type}"
        )

        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Файл слишком большой. Максимум: {settings.MAX_FILE_SIZE_MB}MB",
            )

        validate_file(file)

        filename = file.filename or "uploaded_file"
        content_type = file.content_type or "application/octet-stream"

        upload_result = await process_file(
            file_content=content,
            filename=filename,
            content_type=content_type,
            wait=False,
        )

        create_check_history(
            db=db,
            user_id=user_id,
            text=f"Файл: {filename}",
            filename=filename,
            result=json.dumps(upload_result, ensure_ascii=False),
            similarity_score=0.0,
            api_key_id=api_key_id,
            check_type="file",
        )

        if api_key_id:
            api_key = db.query(APIKey).filter(APIKey.id == api_key_id).first()
            if api_key:
                increment_api_key_usage(db, api_key)

        return FileUploadResponse(
            id=upload_result["task_id"],
            status=upload_result["status"],
            input_filename=upload_result.get("input_filename", filename),
            output_filename=None,
            error=None,
            created_at=datetime.now(),
            api_key="***",
        )

    except FileUploadError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except CheckServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка: {str(e)}",
        )


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
@limiter.limit("60/minute")
async def get_status(
    request: Request,
    task_id: str,
    db: Session = Depends(get_db),
    auth_result: tuple[int, int | None] = Depends(get_user_id_from_auth),
):
    try:
        status_data = await get_task_status(task_id)

        return TaskStatusResponse(
            id=status_data["id"],
            status=status_data["status"],
            input_filename=status_data.get("input_filename", ""),
            output_filename=status_data.get("output_filename"),
            error=status_data.get("error"),
            created_at=datetime.fromisoformat(status_data["created_at"])
            if "created_at" in status_data
            else datetime.now(),
            api_key="***",
        )

    except TaskStatusError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CheckServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/result/{task_id}", response_model=CheckResultResponse)
@limiter.limit("60/minute")
async def get_result(
    request: Request,
    task_id: str,
    db: Session = Depends(get_db),
    auth_result: tuple[int, int | None] = Depends(get_user_id_from_auth),
):
    try:
        status_data = await get_task_status(task_id)

        if status_data["status"] != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Задача не завершена. Статус: {status_data['status']}",
            )

        result = await download_json_result(task_id)
        similarity_score = calculate_file_similarity_score(result)

        return CheckResultResponse(
            discalimer=result.get("discalimer"),
            filename=result.get("filename", ""),
            check_time=result.get("check_time", ""),
            standart_check=result.get("standart_check"),
            translit_check=result.get("translit_check"),
            database_info=result.get("database_info"),
            UUID_FILE=result.get("UUID_FILE"),
            UUID_TASK=result.get("UUID_TASK"),
            task_id=task_id,
            input_filename=status_data.get("input_filename"),
            similarity_score=similarity_score,
        )

    except DownloadError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TaskStatusError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CheckServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/download/{task_id}")
async def download_pdf(
    request: Request,
    task_id: str,
    db: Session = Depends(get_db),
    auth_result: tuple[int, int | None] = Depends(get_user_id_from_auth),
):
    from fastapi.responses import StreamingResponse

    try:
        status_data = await get_task_status(task_id)

        if status_data["status"] != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Отчёт ещё не готов. Статус: {status_data['status']}",
            )

        pdf_content = await download_pdf_result(task_id)

        return StreamingResponse(
            iter([pdf_content]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=report_{task_id}.pdf"
            },
        )

    except DownloadError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TaskStatusError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CheckServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/upload-and-wait", response_model=CheckResultResponse)
@limiter.limit("10/minute")
async def upload_and_wait(
    request: Request,
    file: UploadFile = File(..., description="Файл для проверки (PDF, TXT, DOCX)"),
    db: Session = Depends(get_db),
    auth_result: tuple[int, int | None] = Depends(get_user_id_from_auth),
):
    user_id, api_key_id = auth_result

    try:
        content = await file.read()

        max_size = settings.MAX_FILE_SIZE_MB * 1024 * 1024
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Файл слишком большой. Максимум: {settings.MAX_FILE_SIZE_MB}MB",
            )

        validate_file(file)
        filename = file.filename or "uploaded_file"
        content_type = file.content_type or "application/octet-stream"

        result = await process_file(
            file_content=content,
            filename=filename,
            content_type=content_type,
            wait=True,
        )

        similarity_score = calculate_file_similarity_score(result)

        create_check_history(
            db=db,
            user_id=user_id,
            text=f"Файл: {filename}",
            filename=filename,
            result=json.dumps(result, ensure_ascii=False),
            similarity_score=similarity_score,
            api_key_id=api_key_id,
            check_type="file",
        )

        if api_key_id:
            api_key = db.query(APIKey).filter(APIKey.id == api_key_id).first()
            if api_key:
                increment_api_key_usage(db, api_key)

        return CheckResultResponse(
            discalimer=result.get("discalimer"),
            filename=result.get("filename", ""),
            check_time=result.get("check_time", ""),
            standart_check=result.get("standart_check"),
            translit_check=result.get("translit_check"),
            database_info=result.get("database_info"),
            UUID_FILE=result.get("UUID_FILE"),
            UUID_TASK=result.get("UUID_TASK"),
            task_id=result.get("task_id"),
            input_filename=result.get("input_filename"),
            similarity_score=similarity_score,
        )

    except FileUploadError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TaskTimeoutError as e:
        raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail=str(e))
    except CheckServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка: {str(e)}",
        )
