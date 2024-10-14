from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import RegisterForm, ProfileForm
import random
from .models import Profile
from django.contrib.auth.decorators import login_required

def home(request):
    return render(request, 'core/home.html')


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'core/register.html', {'form': form})


# Profile view
@login_required
def profile_view(request):
    # ดึงหรือสร้างโปรไฟล์ของผู้ใช้ที่ล็อกอินอยู่
    profile, created = Profile.objects.get_or_create(user=request.user)
    # ส่งข้อมูล Profile ไปยัง template
    return render(request, 'core/profile_view.html', {'profile': profile})


# Profile edit view
@login_required
def profile_edit(request):
    # ตรวจสอบว่าผู้ใช้มีโปรไฟล์หรือไม่ ถ้าไม่มี ให้สร้างใหม่
    profile = request.user.profile
    if request.method == 'POST':
        # ตรวจสอบว่า request.FILES ถูกส่งเข้ามาด้วยเพื่อรองรับไฟล์อัปโหลด
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            print(form.cleaned_data['profile_picture'])  # ตรวจสอบว่าไฟล์ถูกส่งเข้ามา
            print(request.FILES)
            form.save()
            return redirect('profile_view')  # คืนค่า redirect ไปที่หน้าโปรไฟล์หลังบันทึกข้อมูลสำเร็จ
        else:
            print(form.errors)  # แสดงข้อผิดพลาดที่เกิดขึ้น
    else:
        form = ProfileForm(instance=profile)

    # คืนค่าการ render เสมอ
    return render(request, 'core/profile_edit.html', {'form': form, 'profile': profile})  # เพิ่ม 'profile' เพื่อใช้แสดงรูปภาพ

# ฟังก์ชันสำหรับสุ่มอาหาร
def random_food(request):
    foods = ['ข้าวมันไก่', 'ก๋วยเตี๋ยว', 'ส้มตำ', 'ข้าวผัด', 'ข้าวหน้าไก่']
    random_choice = random.choice(foods)
    return render(request, 'core/random_food.html', {'food': random_choice})


# ร้านอาหาร
def restaurant_list(request):
    return render(request, 'core/food/restaurant_list.html')


# กระทู้
def forum(request):
    return render(request, 'core/community/forum.html')
