from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from .forms import *
import random
from .models import *
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages

# หน้าแรก
def home(request):
    restaurants = Restaurant.objects.all()
    foods = Food.objects.all()
    forums = Forum.objects.all()
    return render(request, 'core/home.html', {
        'restaurants': restaurants,
        'foods': foods,
        'forums': forums,
    })

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
    form = FoodFilterForm(request.GET or None)
    food = None  # ตั้งค่าเริ่มต้นของ food เป็น None

    # ตรวจสอบว่าฟอร์มถูกส่งข้อมูลมาและใช้เงื่อนไขในการกรอง
    if form.is_valid() and request.GET:
        foods = Food.objects.all()

        # กรองข้อมูลตามเงื่อนไขที่ผู้ใช้เลือก
        category = form.cleaned_data.get('category')
        subcategory = form.cleaned_data.get('subcategory')
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')

        if category:
            foods = foods.filter(category=category)
        if subcategory:
            foods = foods.filter(subcategory=subcategory)
        if min_price is not None:
            foods = foods.filter(price__gte=min_price)
        if max_price is not None:
            foods = foods.filter(price__lte=max_price)

        # สุ่มอาหารจากผลลัพธ์ที่กรองแล้ว
        if foods.exists():
            food = random.choice(foods)

    # ตรวจสอบว่ามีการส่งข้อมูลบันทึกการเลือกอาหารจากผู้ใช้หรือไม่
    if request.method == 'POST' and food:
        # บันทึกการเลือกอาหารของผู้ใช้
        UserChoice.objects.create(user=request.user, food=food)
        messages.success(request, f'คุณได้เลือกอาหาร {food.name} แล้ว')
        return redirect('home')  # เปลี่ยนเส้นทางไปหน้าหลักหลังจากเลือกอาหารเสร็จ

    return render(request, 'core/random_food.html', {'food': food, 'form': form})


@login_required
def choose_food(request, food_id):
    food = get_object_or_404(Food, id=food_id)

    # สร้าง ChosenFood สำหรับผู้ใช้คนปัจจุบัน
    ChosenFood.objects.create(user=request.user, food=food)

    return redirect('home')

# รายการร้านอาหาร
def restaurant_list(request):
    restaurants = Restaurant.objects.all()  # ดึงข้อมูลร้านอาหารทั้งหมด
    return render(request, 'core/food/restaurant_list.html', {'restaurants': restaurants})


# รายละเอียดร้านอาหาร
@login_required
def restaurant_detail(request, id):
    restaurant = get_object_or_404(Restaurant, id=id)
    foods = Food.objects.filter(restaurant=restaurant)  # ดึงเมนูอาหารที่เชื่อมกับร้านอาหารนี้
    return render(request, 'core/food/restaurant_detail.html', {
        'restaurant': restaurant,
        'foods': foods,  # ส่งข้อมูลอาหารไปยัง template
    })


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
def forum_list(request):
    forums = Forum.objects.all().order_by('-created_at')  # ดึงข้อมูลเรียงตามวันที่สร้าง
    return render(request, 'core/community/forum.html', {'forums': forums})


@login_required
def create_forum(request):
    if request.method == "POST":
        form = ForumForm(request.POST, request.FILES)
        if form.is_valid():
            forum = form.save(commit=False)
            forum.user = request.user  # ผูกกระทู้กับผู้ใช้งาน
            forum.save()
            return redirect('forum')  # กลับไปยังหน้ารายการกระทู้
    else:
        form = ForumForm()

    return render(request, 'core/community/create_forum.html', {'form': form})

def forum_detail(request, forum_id):
    forum = get_object_or_404(Forum, id=forum_id)
    return render(request, 'core/community/forum_detail.html', {'forum': forum})

