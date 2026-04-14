import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
import logging

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, html_body: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject

    msg.attach(MIMEText(html_body, "html"))

    try:
        if settings.SMTP_PORT == 1025:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER if settings.SMTP_USER else None,
                password=settings.SMTP_PASSWORD if settings.SMTP_PASSWORD else None,
            )
        else:
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER if settings.SMTP_USER else None,
                password=settings.SMTP_PASSWORD if settings.SMTP_PASSWORD else None,
                start_tls=True,
            )
        logger.info(f"✅ Email отправлен: {to} - {subject}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка отправки email: {e}")
        return False


async def send_verification_email(to: str, token: str) -> bool:
    verification_link = f"{settings.FRONTEND_URL}/auth/verify?token={token}"

    html_body = (
        "<!DOCTYPE html>"
        "<html><head><meta charset='UTF-8'>"
        "<style>"
        "body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }"
        ".container { max-width: 600px; margin: 0 auto; padding: 20px; }"
        ".header { background: #4F46E5; color: white; padding: 20px; text-align: center; }"
        ".content { padding: 30px 20px; background: #f9f9f9; }"
        ".button { display: inline-block; padding: 12px 30px; background: #4F46E5;"
        "  color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }"
        ".footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }"
        "</style></head><body>"
        "<div class='container'>"
        "<div class='header'><h1>InnoStatus</h1></div>"
        "<div class='content'>"
        "<h2>Подтверждение регистрации</h2>"
        "<p>Здравствуйте!</p>"
        "<p>Спасибо за регистрацию в InnoStatus. Для завершения регистрации подтвердите ваш email.</p>"
        "<p style='text-align:center;'><a href='" + verification_link + "' class='button'>Подтвердить email</a></p>"
        "<p>Или скопируйте ссылку:</p>"
        "<p style='word-break: break-all; color: #4F46E5;'>" + verification_link + "</p>"
        "<p>Ссылка действительна в течение 24 часов.</p>"
        "</div>"
        "<div class='footer'><p>© 2024 InnoStatus. Все права защищены.</p>"
        "<p>Это письмо отправлено автоматически, не отвечайте на него.</p></div>"
        "</div></body></html>"
    )

    return await send_email(to, "Подтверждение email", html_body)


async def send_password_reset_email(to: str, token: str) -> bool:
    reset_link = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"

    html_body = (
        "<!DOCTYPE html>"
        "<html><head><meta charset='UTF-8'>"
        "<style>"
        "body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }"
        ".container { max-width: 600px; margin: 0 auto; padding: 20px; }"
        ".header { background: #DC2626; color: white; padding: 20px; text-align: center; }"
        ".content { padding: 30px 20px; background: #f9f9f9; }"
        ".button { display: inline-block; padding: 12px 30px; background: #DC2626;"
        "  color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }"
        ".warning { background: #FEF3C7; padding: 15px; border-left: 4px solid #F59E0B; margin: 20px 0; }"
        ".footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }"
        "</style></head><body>"
        "<div class='container'>"
        "<div class='header'><h1>Восстановление пароля</h1></div>"
        "<div class='content'>"
        "<h2>Сброс пароля</h2>"
        "<p>Вы запросили восстановление пароля для вашего аккаунта InnoStatus.</p>"
        "<p style='text-align:center;'><a href='" + reset_link + "' class='button'>Сбросить пароль</a></p>"
        "<p>Или скопируйте ссылку:</p>"
        "<p style='word-break: break-all; color: #DC2626;'>" + reset_link + "</p>"
        "<div class='warning'><strong>Важно:</strong> Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.</div>"
        "<p>Ссылка действительна в течение 1 часа.</p>"
        "</div>"
        "<div class='footer'><p>© 2024 InnoStatus. Все права защищены.</p>"
        "<p>Это письмо отправлено автоматически, не отвечайте на него.</p></div>"
        "</div></body></html>"
    )

    return await send_email(to, "Восстановление пароля", html_body)


async def send_welcome_email(to: str, name: str = None) -> bool:
    display_name = f" {name}!" if name else "!"

    html_body = (
        "<!DOCTYPE html>"
        "<html><head><meta charset='UTF-8'>"
        "<style>"
        "body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }"
        ".container { max-width: 600px; margin: 0 auto; padding: 20px; }"
        ".header { background: #10B981; color: white; padding: 20px; text-align: center; }"
        ".content { padding: 30px 20px; background: #f9f9f9; }"
        ".button { display: inline-block; padding: 12px 30px; background: #10B981;"
        "  color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }"
        ".features { margin: 20px 0; }"
        ".feature { padding: 10px 0; border-bottom: 1px solid #eee; }"
        ".footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }"
        "</style></head><body>"
        "<div class='container'>"
        "<div class='header'><h1>Добро пожаловать!</h1></div>"
        "<div class='content'>"
        "<h2>Здравствуйте" + display_name + "</h2>"
        "<p>Ваш аккаунт InnoStatus успешно создан и готов к работе.</p>"
        "<div class='features'>"
        "<h3>Что вы можете делать:</h3>"
        "<div class='feature'>✅ Проверять текст на плагиат</div>"
        "<div class='feature'>✅ Получать API-ключи для интеграции</div>"
        "<div class='feature'>✅ Отслеживать историю проверок</div>"
        "<div class='feature'>✅ Выбирать подходящий тариф</div>"
        "</div>"
        "<p style='text-align:center;'><a href='" + settings.FRONTEND_URL + "/profile' class='button'>Перейти в личный кабинет</a></p>"
        "</div>"
        "<div class='footer'><p>© 2024 InnoStatus. Все права защищены.</p></div>"
        "</div></body></html>"
    )

    return await send_email(to, "Добро пожаловать!", html_body)
