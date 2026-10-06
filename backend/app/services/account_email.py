import smtplib, ssl
from email.message import EmailMessage
from fastapi import HTTPException
from app.config import get_settings

def require_email():
    settings = get_settings()
    if not (settings.smtp_host and settings.smtp_port in (465, 587) and settings.smtp_from and settings.public_base_url.startswith('https://')):
        raise HTTPException(503, 'Account email service is unavailable. Contact support.')
    return settings

def send_account_email(recipient, purpose, token):
    settings = require_email()
    message = EmailMessage()
    message['From'] = settings.smtp_from
    message['To'] = recipient
    message['Subject'] = 'Ditto: ' + ('Reset your password' if purpose == 'reset' else 'Verify your email')
    path = 'reset-password' if purpose == 'reset' else 'verify-email'
    message.set_content('Open this link to continue: ' + settings.public_base_url.rstrip('/') + '/account/' + path + '#token=' + token + '\nIf you did not request this, ignore this email. The link expires in 30 minutes.')
    try:
        with (smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=ssl.create_default_context(), timeout=20) if settings.smtp_port == 465 else smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)) as client:
            client.timeout = 20
            if settings.smtp_port == 587: client.starttls(context=ssl.create_default_context())
            if settings.smtp_user: client.login(settings.smtp_user, settings.smtp_password)
            client.send_message(message)
    except (OSError, smtplib.SMTPException):
        raise HTTPException(503, 'Account email service is unavailable. Please try later.') from None
