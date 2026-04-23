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
        logger.info(f"Email отправлен: {to} - {subject}")
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки email: {e}")
        return False


async def send_password_reset_email(to: str, token: str) -> bool:
    link = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"

    html_body = f"""
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: Arial, sans-serif;">
        <table role="presentation" style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 40px 0;">
                    <table role="presentation" style="width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 4px; overflow: hidden;">
                        <tr>
                            <td style="background-color: #d32f2f; padding: 30px; text-align: center;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">InnoStatus</h1>
                            </td>
                        </tr>
                        
                        <tr>
                            <td style="padding: 40px 30px;">
                                <h2 style="margin: 0 0 20px 0; font-size: 20px; color: #333333;">Восстановление пароля</h2>
                                <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 1.6; color: #666666;">
                                    Вы запросили восстановление пароля для вашего аккаунта InnoStatus. Нажмите кнопку ниже, чтобы создать новый пароль:
                                </p>
                                
                                <table role="presentation" style="margin: 30px 0; border-collapse: collapse;">
                                    <tr>
                                        <td style="background-color: #d32f2f; border-radius: 4px; text-align: center;">
                                            <a href="{link}" style="display: inline-block; padding: 12px 40px; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: 600;">Сбросить пароль</a>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="margin: 30px 0 0 0; font-size: 14px; color: #999999;">
                                    Или скопируйте ссылку в браузер:
                                </p>
                                <p style="margin: 10px 0 0 0; padding: 10px; background-color: #f4f4f4; font-size: 12px; word-break: break-all; color: #d32f2f;">
                                    {link}
                                </p>
                                
                                <table role="presentation" style="margin: 20px 0 0 0; border-collapse: collapse; width: 100%;">
                                    <tr>
                                        <td style="background-color: #fff3cd; padding: 15px; border-left: 3px solid #ffc107;">
                                            <p style="margin: 0; font-size: 14px; color: #856404;">
                                                <strong>Важно:</strong> Если вы не запрашивали сброс пароля, проигнорируйте это письмо. Ссылка действительна 1 час.
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        
                        <tr>
                            <td style="background-color: #f4f4f4; padding: 20px 30px; text-align: center; border-top: 1px solid #e0e0e0;">
                                <p style="margin: 0; font-size: 13px; color: #999999;">
                                    © 2024 InnoStatus. Все права защищены.
                                </p>
                                <p style="margin: 8px 0 0 0; font-size: 12px; color: #999999;">
                                    Это письмо отправлено автоматически, не отвечайте на него.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    return await send_email(to, "Восстановление пароля", html_body)


async def send_contact_notification_email(
    to: str,
    name: str,
    phone: str,
    email: str,
    comment: str = "",
    request_type: str = "free",
) -> bool:
    request_type_label = (
        "Бесплатный тестовый доступ" if request_type == "free" else "Платный доступ"
    )

    comment_row = ""
    if comment:
        comment_row = f"""
        <tr>
            <td style="padding: 12px 0; font-weight: bold; color: #333333; vertical-align: top;">Комментарий:</td>
            <td style="padding: 12px 0; color: #666666;">
                <div style="padding: 12px; background-color: #f4f4f4; border-left: 3px solid #1a73e8;">{comment}</div>
            </td>
        </tr>
        """

    html_body = f"""
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: Arial, sans-serif;">
        <table role="presentation" style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 40px 0;">
                    <table role="presentation" style="width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 4px; overflow: hidden;">
                        <tr>
                            <td style="background-color: #1a73e8; padding: 30px; text-align: center;">
                                <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 600;">InnoStatus</h1>
                            </td>
                        </tr>
                        
                        <tr>
                            <td style="padding: 40px 30px;">
                                <h2 style="margin: 0 0 20px 0; font-size: 20px; color: #333333;">Новая заявка с контактной формы</h2>
                                
                                <table role="presentation" style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                                    <tr>
                                        <td style="padding: 12px 0; font-weight: bold; color: #333333; width: 140px;">Имя:</td>
                                        <td style="padding: 12px 0; color: #666666;">{name}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 0; font-weight: bold; color: #333333;">Телефон:</td>
                                        <td style="padding: 12px 0; color: #666666;">
                                            <a href="tel:{phone}" style="color: #1a73e8; text-decoration: none;">{phone}</a>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 0; font-weight: bold; color: #333333;">Email:</td>
                                        <td style="padding: 12px 0; color: #666666;">
                                            <a href="mailto:{email}" style="color: #1a73e8; text-decoration: none;">{email}</a>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 12px 0; font-weight: bold; color: #333333;">Тип запроса:</td>
                                        <td style="padding: 12px 0; color: #666666;">{request_type_label}</td>
                                    </tr>
                                    {comment_row}
                                </table>
                            </td>
                        </tr>
                        
                        <tr>
                            <td style="background-color: #f4f4f4; padding: 20px 30px; text-align: center; border-top: 1px solid #e0e0e0;">
                                <p style="margin: 0; font-size: 13px; color: #999999;">
                                    © 2024 InnoStatus. Все права защищены.
                                </p>
                                <p style="margin: 8px 0 0 0; font-size: 12px; color: #999999;">
                                    Это письмо отправлено автоматически из контактной формы.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    return await send_email(to, f"Новая заявка: {name}", html_body)
