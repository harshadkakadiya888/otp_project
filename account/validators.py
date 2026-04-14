import os

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

# Limits (bytes)
MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_PDF_BYTES = 5 * 1024 * 1024  # 5 MB

ALLOWED_IMAGE_EXTENSIONS = ("jpg", "jpeg", "png")
PDF_MAGIC = b"%PDF"


def _validate_size(value, max_bytes, label):
    if value.size > max_bytes:
        raise ValidationError(
            f"{label} file size must be at most {max_bytes // (1024 * 1024)} MB."
        )


def validate_student_image(value):
    """JPG/PNG only, max 2MB; verify real image with Pillow."""
    if not value:
        return
    _validate_size(value, MAX_IMAGE_BYTES, "Image")
    FileExtensionValidator(allowed_extensions=list(ALLOWED_IMAGE_EXTENSIONS))(value)
    ext = os.path.splitext(value.name)[1].lower().lstrip(".")
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError("Only JPG and PNG images are allowed.")
    value.seek(0)
    try:
        from PIL import Image

        with Image.open(value) as img:
            img.verify()
    except Exception as exc:
        raise ValidationError("Invalid or corrupted image file.") from exc
    value.seek(0)


def validate_student_pdf(value):
    """PDF only, max 5MB; basic magic-byte check."""
    if not value:
        return
    _validate_size(value, MAX_PDF_BYTES, "PDF")
    FileExtensionValidator(allowed_extensions=["pdf"])(value)
    head = value.read(5)
    value.seek(0)
    if not head.startswith(PDF_MAGIC):
        raise ValidationError("Invalid PDF file.")
