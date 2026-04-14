import logging
import json
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.db.models import Count
from django.views.decorators.csrf import csrf_exempt

from otp_project import settings
from .models import Student, PaymentTransaction, Notification
from .forms import StudentForm

# DRF Imports
from rest_framework.generics import ListAPIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from .serializers import StudentSerializer
from .permisions import IsAdmin
from .security import rate_limit
from .services.auth_service import (
    authenticate_user,
    register_user,
    reset_password_with_session_otp,
    send_password_reset_otp,
    update_password_from_session_email,
)
from .services.notification_service import create_notification, send_notification_email

logger = logging.getLogger("account")
security_logger = logging.getLogger("security")


# 🔹 ROLE BASED DASHBOARDS

def admin_dashboard(request):
    if request.session.get('role') != 'admin':
        security_logger.warning(
            "Unauthorized admin dashboard access ip=%s role=%s",
            request.META.get("REMOTE_ADDR", "unknown"),
            request.session.get("role"),
        )
        return HttpResponse("Access Denied ❌")
    return render(request, 'admin.html')


def user_dashboard(request):
    if request.session.get('role') != 'user':
        security_logger.warning(
            "Unauthorized user dashboard access ip=%s role=%s",
            request.META.get("REMOTE_ADDR", "unknown"),
            request.session.get("role"),
        )
        return HttpResponse("Access Denied ❌")
    return render(request, 'user.html')


# 🔹 DRF API (Pagination + Filter + Search)

class StudentListAPI(ListAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    authentication_classes = []
    permission_classes = [IsAdmin]
    throttle_scope = 'student_api'
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['course']
    search_fields = ['name']


# 🔹 AGGREGATION

def student_summary(request):
    if request.session.get('role') != 'admin':
        security_logger.warning(
            "Unauthorized student summary access ip=%s role=%s",
            request.META.get("REMOTE_ADDR", "unknown"),
            request.session.get("role"),
        )
        return HttpResponse("Access Denied ❌")
    data = Student.objects.values('course').annotate(total=Count('id'))
    return render(request, 'summary.html', {'data': data})


# 🔹 REGISTER (send_otp)

@rate_limit(max_requests=5, window_seconds=300, key_prefix="register")
def send_otp(request):
    if request.method == 'POST':
        result = register_user(
            username=request.POST.get('username'),
            email=request.POST.get('email'),
            password=request.POST.get('password'),
            role=request.POST.get('role') or 'user',
        )
        if not result["ok"]:
            return HttpResponse(result["error"], status=result.get("status", 400))

        return redirect('login')
    return render(request, 'send_otp.html')


# 🔹 OTP VERIFY

@rate_limit(max_requests=8, window_seconds=300, key_prefix="verify_otp")
def verify_otp(request):
    if request.method == 'POST':
        otp_input = request.POST.get('otp')
        otp_session = request.session.get('reset_otp')

        if otp_input == otp_session:
            logger.info("OTP verification success for email=%s", request.session.get("reset_email"))
            return redirect('new_password')
        logger.warning("OTP verification failed for email=%s", request.session.get("reset_email"))

    return render(request, 'verify_otp.html')


# 🔹 RESET PASSWORD

@rate_limit(max_requests=6, window_seconds=300, key_prefix="password_reset")
def reset_password(request):
    msg = None
    error = None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'send_otp':
            result = send_password_reset_otp(
                email=request.POST.get('email'),
                session=request.session,
            )
            if result["ok"]:
                msg = result["message"]
            else:
                error = result["error"]

        elif action == 'reset':
            result = reset_password_with_session_otp(
                session=request.session,
                otp_input=request.POST.get('otp'),
                new_password=request.POST.get('password'),
            )
            if result["ok"]:
                return redirect('login')
            error = result["error"]

    email = request.session.get('reset_email')

    return render(request, 'reset_password.html', {
        'email': email,
        'msg': msg,
        'error': error
    })


# 🔹 STUDENT FORM

def student_form(request):
    if not request.session.get('email'):
        security_logger.warning(
            "Student form access denied (not logged in) ip=%s",
            request.META.get("REMOTE_ADDR", "unknown"),
        )
        return redirect('login')

    email = request.session.get('email')

    if request.method == 'POST':
        form = StudentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return render(request, 'success.html')
    else:
        form = StudentForm(initial={'email': email})

    return render(request, 'student_form.html', {'form': form})


# 🔹 LOGIN

@rate_limit(max_requests=10, window_seconds=300, key_prefix="login")
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate_user(username=username, password=password)

        if user:
            request.session['email'] = user.email
            request.session['role'] = user.role
            create_notification(user.email, "Login successful.", "login")
            logger.info("Login success username=%s role=%s", username, user.role)

            if user.role == 'admin':
                return redirect('admin_dashboard')
            return redirect('user_dashboard')
        else:
            security_logger.warning(
                "Login failed username=%s ip=%s",
                username,
                request.META.get("REMOTE_ADDR", "unknown"),
            )
            return render(request, 'login.html', {
                'error': 'Invalid username or password ❌'
            })

    return render(request, 'login.html')


# 🔹 NEW PASSWORD

def new_password(request):
    if request.method == 'POST':
        new_pass = request.POST.get('password')

        if not new_pass:
            return HttpResponse("Password required ❌")

        result = update_password_from_session_email(
            session=request.session,
            new_password=new_pass,
        )
        if result["ok"]:
            return redirect('login')

    return render(request, 'new_password.html')


def logout_view(request):
    logger.info("Logout for email=%s", request.session.get("email"))
    request.session.flush()
    return redirect('login')


def razorpay_checkout(request):
    if not request.session.get('email'):
        return redirect('login')

    amount_rupees = request.GET.get("amount", "499")
    try:
        amount_paise = int(float(amount_rupees) * 100)
    except ValueError:
        return HttpResponse("Invalid amount", status=400)

    if amount_paise <= 0:
        return HttpResponse("Amount must be greater than 0", status=400)

    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        logger.error("Razorpay keys are not configured")
        return HttpResponse("Payment gateway is not configured.", status=500)

    try:
        import razorpay
    except ImportError:
        logger.exception("razorpay package not installed")
        return HttpResponse("Razorpay SDK missing. Install package first.", status=500)

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    order_data = {
        "amount": amount_paise,
        "currency": "INR",
        "payment_capture": 1,
    }
    order = client.order.create(data=order_data)

    PaymentTransaction.objects.create(
        email=request.session.get("email"),
        amount=amount_paise,
        order_id=order["id"],
        status="created",
    )

    logger.info("Razorpay order created order_id=%s email=%s", order["id"], request.session.get("email"))
    return render(
        request,
        "razorpay_checkout.html",
        {
            "razorpay_key_id": settings.RAZORPAY_KEY_ID,
            "amount_paise": amount_paise,
            "amount_rupees": amount_paise / 100,
            "currency": "INR",
            "order_id": order["id"],
            "email": request.session.get("email"),
        },
    )


@rate_limit(max_requests=10, window_seconds=300, key_prefix="razorpay_verify")
def razorpay_verify(request):
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    payment_id = request.POST.get("razorpay_payment_id")
    order_id = request.POST.get("razorpay_order_id")
    signature = request.POST.get("razorpay_signature")

    if not (payment_id and order_id and signature):
        return HttpResponse("Missing payment details", status=400)

    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return HttpResponse("Payment gateway is not configured.", status=500)

    try:
        import razorpay
    except ImportError:
        return HttpResponse("Razorpay SDK missing. Install package first.", status=500)

    tx = PaymentTransaction.objects.filter(order_id=order_id).first()
    if not tx:
        security_logger.warning("Payment verification failed due to unknown order_id=%s", order_id)
        return HttpResponse("Invalid order", status=400)

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    payload = {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": signature,
    }

    try:
        client.utility.verify_payment_signature(payload)
        was_success = tx.status == "success"
        tx.payment_id = payment_id
        tx.signature = signature
        tx.status = "success"
        tx.error_message = ""
        tx.save(update_fields=["payment_id", "signature", "status", "error_message", "updated_at"])
        if not was_success:
            amount_rupees = tx.amount / 100
            send_notification_email(
                subject="Payment Successful",
                message=f"Your payment of Rs. {amount_rupees:.2f} was successful. Order ID: {order_id}",
                recipient_email=tx.email,
            )
            create_notification(tx.email, f"Payment successful for Rs. {amount_rupees:.2f}.", "payment")
        logger.info("Payment success order_id=%s payment_id=%s", order_id, payment_id)
        return render(request, "payment_result.html", {"status": "success", "message": "Payment successful."})
    except Exception as exc:
        tx.payment_id = payment_id
        tx.signature = signature
        tx.status = "failed"
        tx.error_message = str(exc)
        tx.save(update_fields=["payment_id", "signature", "status", "error_message", "updated_at"])
        security_logger.warning("Payment verification failed order_id=%s error=%s", order_id, str(exc))
        return render(request, "payment_result.html", {"status": "failed", "message": "Payment verification failed."})


def payment_status_api(request, order_id):
    tx = PaymentTransaction.objects.filter(order_id=order_id).values(
        "order_id", "payment_id", "email", "amount", "status", "created_at", "updated_at"
    ).first()
    if not tx:
        return JsonResponse({"error": "Order not found"}, status=404)
    return JsonResponse(tx)


def payment_config_health(request):
    if request.session.get("role") != "admin":
        security_logger.warning(
            "Payment health endpoint denied ip=%s role=%s",
            request.META.get("REMOTE_ADDR", "unknown"),
            request.session.get("role"),
        )
        return JsonResponse({"error": "forbidden"}, status=403)

    data = {
        "razorpay_key_id_loaded": bool(settings.RAZORPAY_KEY_ID),
        "razorpay_key_secret_loaded": bool(settings.RAZORPAY_KEY_SECRET),
        "razorpay_webhook_secret_loaded": bool(settings.RAZORPAY_WEBHOOK_SECRET),
        "payment_gateway_ready": bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET),
        "webhook_ready": bool(
            settings.RAZORPAY_KEY_ID
            and settings.RAZORPAY_KEY_SECRET
            and settings.RAZORPAY_WEBHOOK_SECRET
        ),
    }
    return JsonResponse(data)


def notification_poll(request):
    email = request.session.get("email")
    if not email:
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        last_id = int(request.GET.get("last_id", "0"))
    except ValueError:
        last_id = 0

    notifications = Notification.objects.filter(email=email, id__gt=last_id).order_by("id")[:20]
    data = [
        {
            "id": n.id,
            "message": n.message,
            "type": n.notification_type,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]
    return JsonResponse({"notifications": data})


@csrf_exempt
def razorpay_webhook(request):
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    if not settings.RAZORPAY_KEY_SECRET or not settings.RAZORPAY_WEBHOOK_SECRET:
        logger.error("Razorpay webhook/key secret not configured")
        return HttpResponse("Webhook not configured", status=500)

    signature = request.headers.get("X-Razorpay-Signature", "")
    body = request.body.decode("utf-8")

    try:
        import razorpay
    except ImportError:
        logger.exception("razorpay package not installed")
        return HttpResponse("Razorpay SDK missing.", status=500)

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    try:
        client.utility.verify_webhook_signature(body, signature, settings.RAZORPAY_WEBHOOK_SECRET)
    except Exception as exc:
        security_logger.warning("Invalid Razorpay webhook signature error=%s", str(exc))
        return HttpResponse("Invalid signature", status=400)

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        return HttpResponse("Invalid payload", status=400)

    event_name = event.get("event", "")
    payment_entity = event.get("payload", {}).get("payment", {}).get("entity", {})
    order_id = payment_entity.get("order_id")
    payment_id = payment_entity.get("id")

    if not order_id:
        return HttpResponse("Missing order id", status=400)

    tx = PaymentTransaction.objects.filter(order_id=order_id).first()
    if not tx:
        security_logger.warning("Webhook for unknown order_id=%s event=%s", order_id, event_name)
        return JsonResponse({"status": "ignored", "reason": "unknown order"}, status=200)

    tx.payment_id = payment_id or tx.payment_id
    tx.signature = signature or tx.signature

    if event_name in ("payment.captured", "order.paid"):
        was_success = tx.status == "success"
        tx.status = "success"
        tx.error_message = ""
        if not was_success:
            amount_rupees = tx.amount / 100
            send_notification_email(
                subject="Payment Successful",
                message=f"Your payment of Rs. {amount_rupees:.2f} was successful. Order ID: {order_id}",
                recipient_email=tx.email,
            )
            create_notification(tx.email, f"Payment successful for Rs. {amount_rupees:.2f}.", "payment")
    elif event_name in ("payment.failed",):
        tx.status = "failed"
        fail_reason = payment_entity.get("error_description") or payment_entity.get("status") or "payment.failed"
        tx.error_message = fail_reason

    tx.save(update_fields=["payment_id", "signature", "status", "error_message", "updated_at"])
    logger.info("Webhook processed event=%s order_id=%s status=%s", event_name, order_id, tx.status)
    return JsonResponse({"status": "ok"}, status=200)