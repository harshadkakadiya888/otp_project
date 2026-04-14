"""
Send a test email using Django email settings (loads .env via settings).

Usage:
  python manage.py sendtestemail you@example.com
"""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Send one test email via SMTP (verifies .env and Gmail App Password setup)."

    def add_arguments(self, parser):
        parser.add_argument("to_email", type=str, help="Recipient email address")

    def handle(self, *args, **options):
        to = options["to_email"]
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            self.stderr.write(
                "EMAIL_HOST_USER or EMAIL_HOST_PASSWORD is empty. "
                "Use project root .env and run from e:\\Dax\\otp_project (not plain python REPL)."
            )
            return
        from_email = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
        self.stdout.write(f"EMAIL_HOST={settings.EMAIL_HOST} PORT={settings.EMAIL_PORT}")
        self.stdout.write(f"EMAIL_HOST_USER set: {bool(settings.EMAIL_HOST_USER)}")
        self.stdout.write(f"EMAIL_HOST_PASSWORD set: {bool(settings.EMAIL_HOST_PASSWORD)}")
        self.stdout.write(f"from_email={from_email!r} -> to={to!r}")
        send_mail(
            "Django SMTP test",
            "If you receive this, SMTP authentication is working.",
            from_email,
            [to],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS("Sent OK."))
