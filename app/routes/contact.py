from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field
from app.services.email import send_contact_notification_email
from app.services.captcha import generate_captcha_challenge, verify_captcha_answer
from app.config import settings
from app.middleware.rate_limiter import limiter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/contact", tags=["Contact"])


@router.get("/captcha", status_code=200)
async def get_captcha():
    return generate_captcha_challenge()


class ContactRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Имя заявителя")
    phone: str = Field(..., min_length=1, max_length=50, description="Телефон")
    email: EmailStr = Field(..., description="Email заявителя")
    comment: str = Field(default="", max_length=2000, description="Комментарий")
    request_type: str = Field(default="free", pattern="^(free|paid)$", description="Тип запроса")
    captcha_token: str = Field(..., min_length=10, description="CAPTCHA токен")
    captcha_answer: int = Field(..., description="Ответ на математический пример")


@router.post("", status_code=200)
@limiter.limit("5/minute")
async def submit_contact_form(request: Request, contact_data: ContactRequest):
    try:
        if not verify_captcha_answer(contact_data.captcha_token, contact_data.captcha_answer):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверная CAPTCHA. Решите пример ещё раз.",
            )

        email_sent = await send_contact_notification_email(
            to=settings.SEND_EMAIL,
            name=contact_data.name,
            phone=contact_data.phone,
            email=contact_data.email,
            comment=contact_data.comment,
            request_type=contact_data.request_type,
        )

        if not email_sent:
            logger.error("Не удалось отправить уведомление о контактной форме")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка отправки заявки. Попробуйте позже.",
            )

        logger.info(f"Контактная форма отправлена: {contact_data.name} ({contact_data.email})")
        return {
            "success": True,
            "message": "Ваша заявка успешно отправлена!",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обработке контактной формы: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера. Попробуйте позже.",
        )
