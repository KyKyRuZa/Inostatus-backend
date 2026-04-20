import httpx
import asyncio
import uuid
from datetime import datetime
from typing import Optional
from app.config import settings


class CheckServiceError(Exception):
    pass


class FileUploadError(CheckServiceError):
    pass


class TaskStatusError(CheckServiceError):
    pass


class DownloadError(CheckServiceError):
    pass


class TaskTimeoutError(CheckServiceError):
    pass


async def check_text_fragment(
    text: str, filename: str = "site_fragment_1", api_key: str | None = None
) -> dict:
    import logging

    logger = logging.getLogger(__name__)

    payload = {
        "text": text,
        "filename": filename,
    }

    effective_api_key = api_key or settings.CHECK_FRAGMENT_API_KEY

    key_source = "from_request" if api_key else "from_env_fallback"
    key_display = (
        f"{effective_api_key[:8]}...{effective_api_key[-4:]}"
        if effective_api_key
        else "NONE"
    )
    logger.info(f"Using API key: {key_display} (source: {key_source})")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-Key": effective_api_key or "",
        "IntegratorID": settings.INTEGRATOR_ID,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            settings.CHECK_FRAGMENT_API_URL,
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


async def check_website(
    url: str, filename: str = None, api_key: str | None = None
) -> dict:
    import logging

    logger = logging.getLogger(__name__)

    payload = {
        "url": url,
        "filename": filename or f"website_{uuid.uuid4().hex[:8]}",
    }

    effective_api_key = api_key or settings.CHECK_FILES_API_KEY

    key_source = "from_request" if api_key else "from_env_fallback"
    key_display = (
        f"{effective_api_key[:8]}...{effective_api_key[-4:]}"
        if effective_api_key
        else "NONE"
    )
    logger.info(
        f"Using API key for website check: {key_display} (source: {key_source})"
    )

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-API-Key": effective_api_key or "",
        "IntegratorID": settings.INTEGRATOR_ID,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.CHECK_FILES_API_URL}/check_website",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


def calculate_similarity_score(result: dict) -> float:
    standart_check = result.get("standart_check", {})
    translit_check = result.get("translit_check", {})

    total_finds = 0

    if standart_check:
        finds = standart_check.get("finds", [])
        if isinstance(finds, dict):
            total_finds += len(finds)
        elif isinstance(finds, list):
            total_finds += len(finds)

    if translit_check:
        finds = translit_check.get("finds", [])
        if isinstance(finds, dict):
            total_finds += len(finds)
        elif isinstance(finds, list):
            total_finds += len(finds)

    return min(total_finds * 10, 100)


async def upload_file(file_content: bytes, filename: str, content_type: str) -> dict:
    url = f"{settings.CHECK_FILES_API_URL}/upload"

    headers = {
        "X-API-Key": settings.CHECK_FILES_API_KEY or "",
        "IntegratorID": settings.INTEGRATOR_ID,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            import logging

            logger = logging.getLogger(__name__)
            logger.info(f"Uploading file: {filename}, size: {len(file_content)} bytes")
            logger.info(f"API URL: {url}")
            logger.info(f"API Key present: {bool(settings.CHECK_FILES_API_KEY)}")
            logger.info(f"IntegratorID: {settings.INTEGRATOR_ID}")
            logger.info(f"Content-Type: {content_type}")

            files = {"file": (filename, file_content, content_type)}
            response = await client.post(url, headers=headers, files=files)

            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.text[:500]}")

            if response.status_code == 403:
                raise FileUploadError("Неверный API ключ или превышен лимит задач")
            elif response.status_code == 429:
                raise FileUploadError("Превышен лимит активных задач")
            elif response.status_code == 400:
                try:
                    error_detail = response.json().get(
                        "detail", "Неподдерживаемый формат файла"
                    )
                except:
                    error_detail = response.text[:200]
                raise FileUploadError(f"Ошибка API: {error_detail}")

            response.raise_for_status()
            return response.json()

        except httpx.RequestError as e:
            raise FileUploadError(f"Ошибка соединения: {str(e)}")


async def get_task_status(task_id: str) -> dict:
    url = f"{settings.CHECK_FILES_API_URL}/status/{task_id}"

    headers = {
        "X-API-Key": settings.CHECK_FILES_API_KEY or "",
        "IntegratorID": settings.INTEGRATOR_ID,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)

            if response.status_code == 404:
                raise TaskStatusError("Задача не найдена")
            elif response.status_code == 403:
                raise TaskStatusError("Доступ запрещен")

            response.raise_for_status()
            return response.json()

        except httpx.RequestError as e:
            raise TaskStatusError(f"Ошибка соединения: {str(e)}")


async def download_json_result(task_id: str) -> dict:
    url = f"{settings.CHECK_FILES_API_URL}/download_json/{task_id}"

    headers = {
        "X-API-Key": settings.CHECK_FILES_API_KEY or "",
        "IntegratorID": settings.INTEGRATOR_ID,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(url, headers=headers)

            if response.status_code == 404:
                raise DownloadError("Задача не найдена")
            elif response.status_code == 400:
                raise DownloadError("Файл отчета не готов")

            response.raise_for_status()
            return response.json()

        except httpx.RequestError as e:
            raise DownloadError(f"Ошибка соединения: {str(e)}")


async def download_pdf_result(task_id: str) -> bytes:
    url = f"{settings.CHECK_FILES_API_URL}/download/{task_id}"

    headers = {
        "X-API-Key": settings.CHECK_FILES_API_KEY or "",
        "IntegratorID": settings.INTEGRATOR_ID,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(url, headers=headers)

            if response.status_code == 404:
                raise DownloadError("Задача не найдена")
            elif response.status_code == 400:
                raise DownloadError("Файл отчета не готов")

            response.raise_for_status()
            return response.content

        except httpx.RequestError as e:
            raise DownloadError(f"Ошибка соединения: {str(e)}")


async def wait_for_task_completion(
    task_id: str, polling_interval: int = 5, timeout: int = 300
) -> dict:
    elapsed = 0

    while elapsed < timeout:
        status_data = await get_task_status(task_id)

        if status_data["status"] == "completed":
            return status_data
        elif status_data["status"] == "failed":
            raise TaskStatusError(
                f"Ошибка обработки: {status_data.get('error', 'Неизвестная ошибка')}"
            )
        elif status_data["status"] not in ["pending", "processing"]:
            raise TaskStatusError(f"Неизвестный статус задачи: {status_data['status']}")

        await asyncio.sleep(polling_interval)
        elapsed += polling_interval

    raise TaskTimeoutError(f"Превышено время ожидания ({timeout} сек)")


async def process_file(
    file_content: bytes, filename: str, content_type: str, wait: bool = True
) -> dict:
    upload_result = await upload_file(file_content, filename, content_type)
    task_id = upload_result["id"]

    if not wait:
        return {
            "task_id": task_id,
            "status": upload_result["status"],
            "message": "Задача создана",
        }

    await wait_for_task_completion(task_id)
    result = await download_json_result(task_id)

    result["task_id"] = task_id
    result["input_filename"] = upload_result.get("input_filename", filename)

    return result


def calculate_file_similarity_score(result: dict) -> float:
    total_finds = 0

    standart_check = result.get("standart_check", {})
    if standart_check:
        finds = standart_check.get("finds", {})
        if isinstance(finds, dict):
            total_finds += len(finds)
        elif isinstance(finds, list):
            total_finds += len(finds)

    translit_check = result.get("translit_check", {})
    if translit_check:
        finds = translit_check.get("finds", {})
        if isinstance(finds, dict):
            total_finds += len(finds)
        elif isinstance(finds, list):
            total_finds += len(finds)

    return min(total_finds * 10.0, 100.0)
