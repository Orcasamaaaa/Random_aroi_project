from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from .forms import RegisterForm, ProfileForm, RestaurantForm,RestaurantImageForm,FoodForm
import random
from .models import Profile, Restaurant,RestaurantImage,Food
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse

# หน้าแรก
def home(request):
    # ตรวจสอบว่าผู้ใช้มีร้านอาหารหรือไม่
    restaurant = None
    if request.user.is_authenticated:
        restaurant = Restaurant.objects.filter(owner=request.user).first()

    return render(request, 'core/home.html', {'restaurant': restaurant})


# ลงทะเบียนผู้ใช้
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'core/register.html', {'form': form})


# แสดงโปรไฟล์
@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    return render(request, 'core/profile_view.html', {'profile': profile})


# แก้ไขโปรไฟล์
@login_required
def profile_edit(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('profile_view')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'core/profile_edit.html', {'form': form, 'profile': profile})


# ฟังก์ชันสำหรับสุ่มอาหาร
def random_food(request):
    foods = ['ข้าวมันไก่', 'ก๋วยเตี๋ยว', 'ส้มตำ', 'ข้าวผัด', 'ข้าวหน้าไก่']
    random_choice = random.choice(foods)
    return render(request, 'core/random_food.html', {'food': random_choice})


# รายการร้านอาหาร
def restaurant_list(request):
    restaurants = Restaurant.objects.all()  # ดึงข้อมูลร้านอาหารทั้งหมด
    return render(request, 'core/food/restaurant_list.html', {'restaurants': restaurants})


# รายละเอียดร้านอาหาร
@login_required
def restaurant_detail(request, id):
    restaurant = get_object_or_404(Restaurant, id=id, owner=request.user)
    return render(request, 'core/food/restaurant_detail.html', {'restaurant': restaurant})


# สร้างร้านอาหารใหม่
@login_required
def restaurant_create(request):
    # ตรวจสอบว่าผู้ใช้มีร้านอาหารอยู่แล้วหรือไม่
    if Restaurant.objects.filter(owner=request.user).exists():
        restaurant = Restaurant.objects.get(owner=request.user)
        return redirect('restaurant_detail', restaurant.id)

    if request.method == 'POST':
        form = RestaurantForm(request.POST, request.FILES)
        if form.is_valid():
            restaurant = form.save(commit=False)
            restaurant.owner = request.user
            restaurant.save()
            return redirect('restaurant_detail', restaurant.id)
    else:
        form = RestaurantForm()

    return render(request, 'core/food/restaurant_create.html', {'form': form})


@login_required
def restaurant_edit(request, id):
    restaurant = get_object_or_404(Restaurant, id=id, owner=request.user)

    if request.method == 'POST':
        form = RestaurantForm(request.POST, request.FILES, instance=restaurant)
        image_form = RestaurantImageForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()

        # ตรวจสอบว่ามีไฟล์รูปภาพใหม่ถูกเลือกหรือไม่
        if image_form.is_valid() and 'image' in request.FILES:
            new_image = image_form.save(commit=False)
            new_image.restaurant = restaurant
            new_image.save()

        return redirect('restaurant_detail', id=restaurant.id)
    else:
        form = RestaurantForm(instance=restaurant)
        image_form = RestaurantImageForm()

    return render(request, 'core/food/restaurant_edit.html',
                  {'form': form, 'image_form': image_form, 'restaurant': restaurant})



@login_required
def delete_image(request, restaurant_id, image_id):
    # ตรวจสอบว่าผู้ใช้เป็นเจ้าของร้านอาหารหรือไม่
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, owner=request.user)

    # ดึงรูปภาพที่ต้องการลบ
    image = get_object_or_404(RestaurantImage, id=image_id, restaurant=restaurant)

    # ลบรูปภาพ
    image.delete()

    # เปลี่ยนเส้นทางกลับไปยังหน้ารายละเอียดของร้านอาหาร
    return HttpResponseRedirect(reverse('restaurant_detail', args=[restaurant_id]))


@login_required
def add_food(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, owner=request.user)

    if request.method == 'POST':
        form = FoodForm(request.POST, request.FILES)
        if form.is_valid():
            food = form.save(commit=False)
            food.restaurant = restaurant
            food.save()
            return redirect('restaurant_detail', id=restaurant.id)
    else:
        form = FoodForm()

    return render(request, 'core/food/add_food.html', {'form': form, 'restaurant': restaurant})

@login_required
def edit_food(request, restaurant_id, food_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    food = get_object_or_404(Food, id=food_id, restaurant=restaurant)

    if request.method == 'POST':
        form = FoodForm(request.POST, request.FILES, instance=food)
        if form.is_valid():
            form.save()
            return redirect('restaurant_detail', id=restaurant_id)
    else:
        form = FoodForm(instance=food)

    return render(request, 'core/food/edit_food.html', {'form': form, 'restaurant': restaurant, 'food': food})

# ฟังก์ชันสำหรับลบเมนูอาหาร
@login_required()
def delete_food(request, restaurant_id, food_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    food = get_object_or_404(Food, id=food_id, restaurant=restaurant)

    # ตรวจสอบว่าผู้ใช้งานเป็นเจ้าของร้านอาหารหรือไม่
    if request.user == restaurant.owner:
        food.delete()

    return redirect('restaurant_detail', id=restaurant_id)
# ฟอรัม (กระทู้)
def forum(request):
    return render(request, 'core/forum.html')
