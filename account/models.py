from django.core.files.uploadedfile import UploadedFile
from django.db import models

from .file_utils import optimize_student_image
from .validators import validate_student_image, validate_student_pdf

class CustomUser(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
    )

    username = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return self.username


class Course(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class OTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)


class Student(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(db_index=True)
    mobile = models.CharField(max_length=15)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student_photo = models.ImageField(
        upload_to="students/photos/",
        blank=True,
        null=True,
        validators=[validate_student_image],
        help_text="JPG or PNG, max 2 MB (stored optimized 500×500 max, JPEG).",
    )
    document = models.FileField(
        upload_to="students/docs/",
        blank=True,
        null=True,
        validators=[validate_student_pdf],
        help_text="PDF only, max 5 MB.",
    )

    def save(self, *args, **kwargs):
        if self.student_photo and isinstance(self.student_photo, UploadedFile):
            self.student_photo = optimize_student_image(self.student_photo)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class PaymentTransaction(models.Model):
    STATUS_CHOICES = (
        ("created", "Created"),
        ("success", "Success"),
        ("failed", "Failed"),
    )

    email = models.EmailField(db_index=True)
    amount = models.PositiveIntegerField(help_text="Amount in paise")
    order_id = models.CharField(max_length=120, unique=True)
    payment_id = models.CharField(max_length=120, blank=True, null=True)
    signature = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="created")
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.email} - {self.order_id} - {self.status}"


class Notification(models.Model):
    TYPE_CHOICES = (
        ("otp", "OTP"),
        ("login", "Login"),
        ("payment", "Payment"),
        ("password", "Password"),
        ("system", "System"),
    )

    email = models.EmailField(db_index=True)
    message = models.CharField(max_length=255)
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="system")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email} - {self.notification_type} - {self.message[:30]}"
