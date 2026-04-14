import logging

from django.contrib.auth.hashers import check_password, make_password

from account.models import CustomUser
from account.services.notification_service import create_notification, send_notification_email
from account.utils.otp import generate_numeric_otp

logger = logging.getLogger("account")


def register_user(username, email, password, role="user"):
    if role not in ("admin", "user"):
        role = "user"

    if not password:
        return {"ok": False, "error": "Password required ❌", "status": 400}

    if CustomUser.objects.filter(email=email).exists():
        logger.info("Registration blocked for existing email=%s", email)
        return {"ok": False, "error": "Email already exists ❌", "status": 400}

    try:
        CustomUser.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            role=role,
        )
        logger.info("User registered email=%s role=%s", email, role)
        return {"ok": True}
    except Exception:
        logger.exception("Registration failed")
        return {"ok": False, "error": "Something went wrong. Please try again.", "status": 500}


def authenticate_user(username, password):
    user = CustomUser.objects.filter(username=username).first()
    if user and check_password(password, user.password):
        return user
    return None


def send_password_reset_otp(email, session):
    if not email:
        return {"ok": False, "error": "Email required ❌"}

    otp = generate_numeric_otp(length=6)
    session["reset_email"] = email
    session["reset_otp"] = otp

    send_notification_email(
        subject="Password Reset OTP",
        message=f"Your OTP is {otp}",
        recipient_email=email,
    )
    create_notification(email, "OTP sent successfully.", "otp")
    logger.info("Password reset OTP sent to email=%s", email)
    return {"ok": True, "message": "OTP Sent ✅"}


def reset_password_with_session_otp(session, otp_input, new_password):
    email = session.get("reset_email")
    otp_session = session.get("reset_otp")

    if otp_input != otp_session:
        logger.warning("Password reset failed due to wrong OTP for email=%s", email)
        return {"ok": False, "error": "Wrong OTP ❌"}

    user = CustomUser.objects.only("id", "email", "password").filter(email=email).first()
    if not user:
        logger.warning("Password reset attempted for unknown email=%s", email)
        return {"ok": False, "error": "User not found ❌"}

    user.password = make_password(new_password)
    user.save()
    send_notification_email(
        subject="Password Reset Successful",
        message="Your password was reset successfully.",
        recipient_email=email,
    )
    create_notification(email, "Password reset successful.", "password")
    logger.info("Password reset successful for email=%s", email)
    return {"ok": True}


def update_password_from_session_email(session, new_password):
    email = session.get("reset_email")
    user = CustomUser.objects.filter(email=email).first()
    if not user:
        logger.warning("New password endpoint hit but user missing email=%s", email)
        return {"ok": False}

    user.password = make_password(new_password)
    user.save()
    send_notification_email(
        subject="Password Changed",
        message="Your password was changed successfully.",
        recipient_email=email,
    )
    create_notification(email, "Password changed successfully.", "password")
    logger.info("New password set for email=%s", email)
    return {"ok": True}

