import logging

from django.conf import settings
from django.core.mail import send_mail

from account.models import Notification

logger = logging.getLogger("account")


def create_notification(email, message, notification_type="system"):
    if not email:
        return None
    return Notification.objects.create(
        email=email,
        message=message,
        notification_type=notification_type,
    )


def send_notification_email(subject, message, recipient_email):
    if not recipient_email:
        return False
    if not settings.EMAIL_HOST_USER:
        logger.warning("Email host user is not configured; skipping email send")
        return False
    try:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.EMAIL_HOST_USER
        send_mail(
            subject,
            message,
            from_email,
            [recipient_email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Failed to send notification email to %s", recipient_email)
        return False


def send_plain_email(subject, message, recipient_email):
    """Generic email sender reused by background tasks."""
    return send_notification_email(
        subject=subject,
        message=message,
        recipient_email=recipient_email,
    )

