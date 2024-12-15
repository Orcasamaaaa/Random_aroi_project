from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import *
from django_select2.forms import ModelSelect2MultipleWidget

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

class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = [
            'name', 'description', 'location', 'contact_info',
            'opening_hours', 'social_media', 'images', 'categories'
        ]
        widgets = {
            'categories': ModelSelect2MultipleWidget(
                queryset=RestaurantCategory.objects.all(),
                search_fields=['name__icontains'],  # ทำให้สามารถค้นหาได้
                attrs={'data-placeholder': 'เลือกประเภท...'},
            ),
        }

class RestaurantImageForm(forms.ModelForm):
    class Meta:
        model = RestaurantImage
        fields = ['image']


class FoodForm(forms.ModelForm):
    class Meta:
        model = Food
        fields = ['name', 'description', 'price', 'category', 'image']

    # ใช้ MultipleChoiceField หรือ ModelMultipleChoiceField เพื่อรองรับหลายหมวดหมู่
    category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,  # ใช้ Checkbox เพื่อให้เลือกหลายหมวดหมู่ได้
        required=True
    )


class FoodFilterForm(forms.Form):
    category = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label="ประเภทอาหาร",
        widget=forms.CheckboxSelectMultiple,  # ใช้ checkbox เพื่อให้เลือกหลายตัว
    )
    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        label="ราคาขั้นต่ำ",
        widget=forms.NumberInput(attrs={'step': '0.01'}),  # เพิ่ม step สำหรับราคาทศนิยม
    )
    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        label="ราคาสูงสุด",
        widget=forms.NumberInput(attrs={'step': '0.01'}),  # เพิ่ม step สำหรับราคาทศนิยม
    )

class ForumForm(forms.ModelForm):
    class Meta:
        model =Forum
        fields = ['title','content','image']