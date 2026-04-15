from django.urls import path
from . import views

urlpatterns = [
    path('', views.send_otp, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify/', views.verify_otp, name='verify_otp'),
    path('reset/', views.reset_password, name='reset_password'),
    path('form/', views.student_form, name='student_form'),
    path('new-password/', views.new_password, name='new_password'),
    path('summary/', views.student_summary, name='student_summary'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/user/', views.user_dashboard, name='user_dashboard'),
    path('api/students/', views.StudentListAPI.as_view(), name='student-api'),
    path('payments/razorpay/', views.razorpay_checkout, name='razorpay_checkout'),
    path('payments/razorpay/verify/', views.razorpay_verify, name='razorpay_verify'),
    path('payments/razorpay/webhook/', views.razorpay_webhook, name='razorpay_webhook'),
    path('payments/health/', views.payment_config_health, name='payment_config_health'),
    path('notifications/poll/', views.notification_poll, name='notification_poll'),
    path('api/payment-status/<str:order_id>/', views.payment_status_api, name='payment_status_api'),
    path('send_otp/', views.send_otp, name='send_otp'),

]