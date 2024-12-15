from django.contrib.messages import success
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods

from .forms import *
import random
from .models import *
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
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

    # ดึงรายการอาหารที่ชอบและไม่ชอบ
    liked_foods = LikeDislikeFood.objects.filter(user=request.user, liked=True)
    disliked_foods = LikeDislikeFood.objects.filter(user=request.user, liked=False)

    return render(request, 'core/profile_view.html', {
        'profile': profile,
        'liked_foods': liked_foods,
        'disliked_foods': disliked_foods,
    })


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
    food = None  # อาหารที่สุ่มได้

    if form.is_valid() and request.GET:
        # กรองข้อมูลอาหารตามฟอร์ม
        foods = Food.objects.all()

        category = form.cleaned_data.get('category')
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')

        if category:
            foods = foods.filter(category__in=category)
        if min_price is not None:
            foods = foods.filter(price__gte=min_price)
        if max_price is not None:
            foods = foods.filter(price__lte=max_price)

        # สุ่มอาหารจากผลลัพธ์
        if foods.exists():
            food = random.choice(foods)

    # การจัดการ POST สำหรับการกดปุ่ม "ชอบ" และ "ไม่ชอบ"
    if request.method == 'POST' and food:
        if request.user.is_authenticated:
            # กรณีที่ผู้ใช้ล็อกอิน
            action = request.POST.get('action')
            if action == 'like':
                LikeDislikeFood.objects.update_or_create(user=request.user, food=food, defaults={'liked': True})
                messages.success(request, f"คุณชอบอาหาร {food.name}!")
            elif action == 'dislike':
                LikeDislikeFood.objects.update_or_create(user=request.user, food=food, defaults={'liked': False})
                messages.warning(request, f"คุณไม่ชอบอาหาร {food.name}!")
            return redirect('random_food')
        else:
            # กรณีที่ผู้ใช้ไม่ได้ล็อกอิน
            messages.info(request, "กรุณาล็อกอินเพื่อบันทึกความชอบหรือไม่ชอบอาหาร")
            return redirect('random_food')

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
    # ดึงข้อมูลร้านอาหารที่เป็นเจ้าของโดย user
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, owner=request.user)

    if request.method == 'POST':
        form = FoodForm(request.POST, request.FILES)
        if form.is_valid():
            food = form.save(commit=False)
            food.restaurant = restaurant  # เชื่อมอาหารกับร้านอาหาร
            food.save()  # บันทึกข้อมูลอาหาร

            # บันทึก ManyToManyField
            form.save_m2m()

            # เพิ่มข้อความแจ้งเตือนสำเร็จ
            messages.success(request, "เพิ่มเมนูอาหารเรียบร้อยแล้ว!")
            return redirect('restaurant_detail', restaurant_id=restaurant.id)
        else:
            messages.error(request, "เกิดข้อผิดพลาด กรุณาตรวจสอบข้อมูล.")
    else:
        # ตั้งค่า queryset สำหรับ categories
        form = FoodForm()
        form.fields['category'].queryset = Category.objects.all()

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
    forum = get_object_or_404(Forum, pk=forum_id)
    return render(request, 'core/community/forum_detail.html', {'forum': forum})



def my_forums(request):
    forums = Forum.objects.filter(user=request.user)  # แสดงกระทู้ของผู้ใช้ที่ล็อกอิน
    return render(request, 'core/community/forum.html', {'forums': forums})

@login_required
def forum_edit(request, forum_id):
    forum = get_object_or_404(Forum, id=forum_id, user=request.user)  # ตรวจสอบว่าผู้ใช้งานต้องเป็นเจ้าของกระทู้
    if request.method == 'POST':
        form = ForumForm(request.POST, request.FILES, instance=forum)
        if form.is_valid():
            form.save()
            return redirect('forum_detail', forum_id=forum.id)
    else:
        form = ForumForm(instance=forum)
    return render(request, 'core/community/forum_edit.html', {'form': form, 'forum': forum})


@login_required
def forum_delete(request, pk):
    forum = get_object_or_404(Forum, pk=pk, user=request.user)  # ตรวจสอบเจ้าของกระทู้
    if request.method == 'POST':
        forum.delete()
        return redirect('my_forums')  # กลับไปที่หน้ารายการกระทู้
    return render(request, 'core/community/forum_delete.html', {'forum': forum})


@csrf_protect
def add_comment(request, forum_id):
    if request.method == 'POST':
        forum = get_object_or_404(Forum, id=forum_id)
        content = request.POST.get('content', '').strip()

        if content:
            # สร้างคอมเมนต์ใหม่
            ForumComment.objects.create(
                forum=forum,
                user=request.user,
                content=content
            )
            # โหลดคอมเมนต์ทั้งหมดใหม่
            comments = forum.comments.select_related('user__profile').order_by('-created_at')
            html = render_to_string(
                'core/partials/forum_comments.html',
                {'comments': comments, 'request': request},  # ใส่ request เพื่อให้ template ใช้งานข้อมูล user
                request=request
            )
            return JsonResponse({'html': html})
        return JsonResponse({'error': 'Content is required'}, status=400)

    return JsonResponse({'error': 'Invalid request'}, status=400)


def load_comments(request, forum_id):
    forum = get_object_or_404(Forum, id=forum_id)
    comments = ForumComment.objects.filter(forum=forum).select_related('user__profile').order_by('-created_at')

    # โหลด partial template และส่งคอมเมนต์กลับมา
    return render(request, 'core/partials/forum_comments.html', {'comments': comments})


def delete_comment(request, comment_id):
    if request.method == "DELETE" and request.user.is_authenticated:
        comment = get_object_or_404(ForumComment, id=comment_id, user=request.user)
        comment.delete()
        return HttpResponse(status=204)  # Success without content
    return HttpResponse(status=403)  # Forbidden
