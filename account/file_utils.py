import uuid

from django.core.files.base import ContentFile


def optimize_student_image(uploaded_file):
    """
    Resize to fit within 500x500, compress as JPEG (quality 85).
    Accepts an UploadedFile or any readable image file-like object.
    """
    from PIL import Image

    uploaded_file.seek(0)
    image = Image.open(uploaded_file)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    elif image.mode != "RGB":
        image = image.convert("RGB")

    image.thumbnail((500, 500), Image.Resampling.LANCZOS)

    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85, optimize=True)
    buffer.seek(0)
    name = f"student_{uuid.uuid4().hex}.jpg"
    return ContentFile(buffer.read(), name=name)
