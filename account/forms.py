from django import forms
from .models import Student

class EmailForm(forms.Form):
    username = forms.CharField(max_length=100)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

class OTPForm(forms.Form):
    otp = forms.CharField(max_length=6)

class PasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput)

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['name', 'email', 'mobile', 'course', 'student_photo', 'document']
        widgets = {
            'student_photo': forms.ClearableFileInput(
                attrs={'accept': 'image/jpeg,image/png,.jpg,.jpeg,.png'}
            ),
            'document': forms.ClearableFileInput(
                attrs={'accept': 'application/pdf,.pdf'}
            ),
        }
