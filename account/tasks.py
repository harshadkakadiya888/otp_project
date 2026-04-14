"""
Celery tasks for scheduled jobs (see CELERY_BEAT_SCHEDULE in settings).

Tasks are registered on the project Celery app (otp_project.celery.app) so the
worker can resolve them reliably.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from otp_project.celery import app

from .models import OTP, Student
from .services.notification_service import send_plain_email

logger = logging.getLogger("account")


@app.task(name="account.tasks.cleanup_expired_otps")
def cleanup_expired_otps():
    """
    Remove OTP rows older than OTP_EXPIRY_MINUTES (based on created_at).
    """
    minutes = int(getattr(settings, "OTP_EXPIRY_MINUTES", 15))
    cutoff = timezone.now() - timedelta(minutes=minutes)
    qs = OTP.objects.filter(created_at__lt=cutoff)
    delete_result = qs.delete()
    # delete() returns (total_deleted, per_model_dict); avoid tuple-unpack edge cases
    deleted_count = delete_result[0] if delete_result else 0
    logger.info(
        "cleanup_expired_otps: deleted %s OTP(s) older than %s minutes (cutoff=%s)",
        deleted_count,
        minutes,
        cutoff.isoformat(),
    )
    return {"deleted": deleted_count, "cutoff": cutoff.isoformat()}


@app.task(name="account.tasks.send_daily_student_reminders")
def send_daily_student_reminders():
    """
    Send a simple daily reminder to each student (by distinct email on Student rows).
    Iterates model instances — no tuple unpacking from values_list.
    """
    if not getattr(settings, "EMAIL_HOST_USER", None) or not getattr(settings, "EMAIL_HOST_PASSWORD", None):
        logger.warning(
            "send_daily_student_reminders: email not configured (DEFAULT_FROM_EMAIL / EMAIL_HOST_USER / password)"
        )
        return {"sent": 0, "skipped": "email_not_configured"}

    subject = "Daily reminder"
    body = "Hello, this is your daily reminder."
    sent = 0
    failed = 0
    seen = set()

    # Iterate Student rows; use .email on each instance (no multi-column unpack).
    for student in Student.objects.only("email").order_by("id").iterator(chunk_size=100):
        email = (getattr(student, "email", None) or "").strip()
        if not email or email in seen:
            continue
        seen.add(email)
        try:
            was_sent = send_plain_email(subject=subject, message=body, recipient_email=email)
            if was_sent:
                sent += 1
            else:
                failed += 1
        except Exception:
            logger.exception("send_daily_student_reminders: failed for %s", email)
            failed += 1

    logger.info(
        "send_daily_student_reminders: sent=%s failed=%s distinct_emails=%s",
        sent,
        failed,
        len(seen),
    )
    return {"sent": sent, "failed": failed, "total": len(seen)}
