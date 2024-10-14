from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class ProfileForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    username = forms.CharField(required=True)

    class Meta:
        model = Profile
        fields = ['first_name', 'last_name', 'profile_picture', 'email', 'username']  # เพิ่ม profile_picture

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ตั้งค่าเริ่มต้นสำหรับ email และ username จาก instance ของ user
        self.fields['email'].initial = self.instance.user.email
        self.fields['username'].initial = self.instance.user.username

    def save(self, commit=True):
        # บันทึกข้อมูลฟอร์ม โดยใช้ commit=False เพื่อให้สามารถแก้ไขโปรไฟล์และ user ได้ก่อน
        profile = super().save(commit=False)

        # ดึงข้อมูล user ที่เชื่อมโยงกับโปรไฟล์
        user = profile.user

        # อัปเดตข้อมูล user จากข้อมูลใหม่ในฟอร์ม
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['username']

        # ตรวจสอบว่ามีการอัปโหลดรูปภาพใหม่หรือไม่
        if self.cleaned_data.get('profile_picture'):
            profile.profile_picture = self.cleaned_data['profile_picture']

        # บันทึกข้อมูลทั้งโปรไฟล์และผู้ใช้
        if commit:
            user.save()  # บันทึกข้อมูล user ก่อน
            profile.save()  # บันทึกข้อมูลโปรไฟล์

        return profile


