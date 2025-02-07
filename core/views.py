import numpy as np
from django.contrib.messages import success
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods
import re

from sklearn.preprocessing import OneHotEncoder, MinMaxScaler

from .forms import *
import random
from .models import *
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse, HttpResponseForbidden
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
import logging
from urllib.parse import unquote
from django.db.models import Avg
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.core.paginator import Paginator
from sklearn.ensemble import RandomForestClassifier

# หน้าแรก
def home(request):
    # จำกัดจำนวนรายการเป็น 6 รายการแรกในแต่ละประเภท
    restaurants = Restaurant.objects.all()[:6]
    foods = Food.objects.all()[:6]
    forums = Forum.objects.all()[:6]

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

    # ดึงร้านอาหารที่ผู้ใช้บันทึกไว้
    saved_restaurants = Restaurant.objects.filter(saved_by=request.user)

    # ดึงกระทู้ที่ผู้ใช้บันทึกไว้
    saved_forums = Forum.objects.filter(saved_by=request.user)

    return render(request, 'core/profile_view.html', {
        'profile': profile,
        'liked_foods': liked_foods,
        'disliked_foods': disliked_foods,
        'saved_restaurants': saved_restaurants,  # ร้านอาหารที่บันทึก
        'saved_forums': saved_forums,  # กระทู้ที่บันทึก
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
    food = None  # ค่าเริ่มต้นของอาหารที่สุ่มได้
    avg_rating = None  # ค่าเริ่มต้นของคะแนนเฉลี่ยร้านอาหาร
    foods = Food.objects.all().select_related('restaurant')  # ดึงอาหารทั้งหมดก่อนกรอง

    # ตรวจสอบว่ามีการส่งค่า GET และ form ถูกต้อง
    if request.GET and form.is_valid():
        category = form.cleaned_data.get('category')
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')

        if category:
            foods = foods.filter(category__in=category)

            # ถ้าเลือกหมวดหมู่แล้ว ไม่มีอาหารในหมวดหมู่นั้นเลย → แจ้งเตือน
            if not foods.exists():
                messages.warning(request, "ไม่มีอาหารในหมวดหมู่นี้")
                return render(request, 'core/random_food.html', {'food': None, 'form': form})

        # กรองช่วงราคาถ้ามีค่า
        if min_price:
            foods = foods.filter(price__gte=min_price)
        if max_price:
            foods = foods.filter(price__lte=max_price)

        # ถ้าไม่มีอาหารที่ตรงตามช่วงราคา → หาตัวที่ใกล้เคียงที่สุด
        if not foods.exists() and (min_price or max_price):
            closest_food = Food.objects.order_by('price').first()
            if closest_food:
                food = closest_food
                messages.warning(request, f"ไม่มีอาหารในช่วงราคาที่เลือก แสดงอาหารที่ใกล้เคียงที่สุด: {food.name}")
            else:
                messages.warning(request, "ไม่มีอาหารที่ตรงกับเงื่อนไข")
                return render(request, 'core/random_food.html', {'food': None, 'form': form})

        # สุ่มอาหารจากที่กรองได้
        if foods.exists():
            food = random.choice(list(foods))
            request.session['selected_food_id'] = food.id  # เก็บ ID อาหารที่สุ่มได้

        # คำนวณคะแนนเฉลี่ยของร้านที่สุ่มได้
        if food:
            avg_rating = Review.objects.filter(restaurant=food.restaurant).aggregate(Avg('rating'))['rating__avg']
            avg_rating = round(avg_rating, 1) if avg_rating else None  # ปัดเศษเหลือ 1 ตำแหน่ง

    # ตรวจสอบว่ามีการกด Like/Dislike หรือไม่
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "กรุณาเข้าสู่ระบบก่อน")
            return redirect('login')

        food_id = request.POST.get('food_id')
        try:
            food = Food.objects.get(id=food_id)
            action = request.POST.get('action')
            liked_status = action == 'like'

            LikeDislikeFood.objects.create(
                user=request.user,
                food=food,
                liked=liked_status,
                timestamp=timezone.now()
            )
            messages.success(request, f"คุณ{'ชอบ' if liked_status else 'ไม่ชอบ'}อาหาร {food.name} แล้ว!")
            return redirect(request.path)
        except Food.DoesNotExist:
            messages.error(request, "ไม่พบอาหารที่คุณเลือก กรุณาลองใหม่")

    return render(request, 'core/random_food.html', {
        'food': food,
        'form': form,
        'avg_rating': avg_rating if food else None,  # ส่งคะแนนเฉลี่ยไปที่ template
    })
@login_required
def choose_food(request, food_id):
    food = get_object_or_404(Food, id=food_id)

    # สร้าง ChosenFood สำหรับผู้ใช้คนปัจจุบัน
    LikeDislikeFood.objects.create(user=request.user, food=food)

    return redirect('home')

# รายการร้านอาหาร
def restaurant_list(request):
    restaurants = Restaurant.objects.all()  # ดึงข้อมูลร้านอาหารทั้งหมด
    return render(request, 'core/food/restaurant_list.html', {'restaurants': restaurants})


# รายละเอียดร้านอาหาร

def restaurant_detail(request, id):
    restaurant = get_object_or_404(Restaurant, id=id)
    foods = Food.objects.filter(restaurant=restaurant)
    categories = restaurant.categories.all()
    reviews = Review.objects.filter(restaurant=restaurant)  # ดึงรีวิวร้านอาหาร

    # ตรวจสอบว่าผู้ใช้ได้รีวิวร้านอาหารนี้หรือยัง
    user_reviewed = False
    if request.user.is_authenticated:  # ตรวจสอบว่า user ล็อกอินอยู่หรือไม่
        user_reviewed = reviews.filter(user=request.user).exists()

    # ตรวจสอบว่าผู้ใช้ได้บันทึกร้านนี้หรือยัง
    is_saved = False
    if request.user.is_authenticated:
        is_saved = restaurant.saved_by.filter(id=request.user.id).exists()

    # คำนวณคะแนนเฉลี่ยดาวของร้านอาหาร
    average_rating = reviews.aggregate(average=Avg('rating'))['average']

    return render(request, 'core/food/restaurant_detail.html', {
        'restaurant': restaurant,
        'foods': foods,
        'categories': categories,
        'reviews': reviews,  # ส่งข้อมูลรีวิวไปยังเทมเพลต
        'user_reviewed': user_reviewed,  # ส่งตัวแปรตรวจสอบการรีวิวไปยังเทมเพลต
        'average_rating': average_rating,  # ส่งคะแนนเฉลี่ยไปยังเทมเพลต
        'is_saved': is_saved,  # ส่งสถานะการบันทึกไปยังเทมเพลต
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
    restaurant = get_object_or_404(Restaurant, id=id)

    # ตรวจสอบว่าเป็นเจ้าของร้านหรือเป็น Superuser
    if request.user != restaurant.owner and not request.user.is_superuser:
        messages.error(request, "คุณไม่มีสิทธิ์แก้ไขร้านอาหารนี้!")
        return redirect('restaurant_detail', id=restaurant.id)

    if request.method == 'POST':
        form = RestaurantForm(request.POST, request.FILES, instance=restaurant)

        if form.is_valid():
            restaurant = form.save(commit=False)  # ยังไม่บันทึกใน DB

            # อัปเดตหมวดหมู่ (categories)
            category_ids = request.POST.getlist('categories')  # รับค่าหมวดหมู่จาก form
            categories = RestaurantCategory.objects.filter(id__in=category_ids)  # ค้นหา Category objects
            restaurant.save()  # บันทึกข้อมูลหลักของร้าน
            restaurant.categories.set(categories)  # ตั้งค่าหมวดหมู่

            # อัปเดตรูปภาพใหม่หากมีการอัปโหลด
            if 'images' in request.FILES:
                restaurant.images = request.FILES['images']
                restaurant.save()

            messages.success(request, "แก้ไขข้อมูลร้านอาหารเรียบร้อยแล้ว!")
            return redirect('restaurant_detail', id=restaurant.id)
        else:
            messages.error(request, "กรุณาตรวจสอบข้อมูลให้ถูกต้อง.")

    else:
        form = RestaurantForm(instance=restaurant)

    return render(request, 'core/food/restaurant_edit.html', {
        'form': form,
        'restaurant': restaurant,
    })

@login_required
def add_restaurant_image(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, owner=request.user)

    if request.method == 'POST':
        form = RestaurantImageForm(request.POST, request.FILES)
        if form.is_valid():
            RestaurantImage.objects.create(restaurant=restaurant, image=form.cleaned_data['image'])
            messages.success(request, "เพิ่มรูปบรรยากาศร้านเรียบร้อยแล้ว!")
            return redirect('restaurant_detail', id=restaurant.id)  # แก้ตรงนี้
    else:
        form = RestaurantImageForm()

    return render(request, 'core/food/add_image.html', {
        'form': form,
        'restaurant': restaurant
    })




@login_required
@require_http_methods(["DELETE", "POST"])
def delete_restaurant(request, pk):
    """
    View สำหรับลบร้านอาหาร รองรับทั้ง DELETE และ POST method
    """
    # ดึงข้อมูลร้านอาหาร
    restaurant = get_object_or_404(Restaurant, pk=pk)

    # ตรวจสอบว่า request.user เป็นเจ้าของร้าน
    if restaurant.owner != request.user:
        return JsonResponse({'error': 'คุณไม่มีสิทธิ์ในการลบร้านอาหารนี้'}, status=403)

    # ทำการลบร้านอาหาร
    restaurant.delete()

    # ตรวจสอบว่าเป็น HTMX request หรือไม่
    if request.headers.get('HX-Request'):
        return HttpResponse(status=204)  # HTMX ชอบ response 204 สำหรับการลบ
    else:
        # ถ้าไม่ใช่ HTMX request ให้ redirect ไปยัง restaurant_list
        return HttpResponseRedirect(reverse('restaurant_list'))


@login_required
def delete_image(request, restaurant_id, image_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, owner=request.user)
    image = get_object_or_404(RestaurantImage, id=image_id, restaurant=restaurant)

    # ลบรูปภาพ
    image.delete()
    messages.success(request, "ลบรูปบรรยากาศร้านเรียบร้อยแล้ว!")

    # เปลี่ยนพารามิเตอร์เป็น id
    return redirect('restaurant_detail', id=restaurant.id)


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
            return redirect('restaurant_detail', id=restaurant.id)  # ต้องใส่ return
        else:
            messages.error(request, "เกิดข้อผิดพลาด กรุณาตรวจสอบข้อมูล.")
    else:
        # ตั้งค่า queryset สำหรับ categories
        form = FoodForm()
        form.fields['category'].queryset = Category.objects.all()

    return render(request, 'core/food/add_food.html', {'form': form, 'restaurant': restaurant})

@login_required
def edit_food(request, restaurant_id, food_id):
    """
    View สำหรับแก้ไขเมนูอาหารที่เชื่อมกับร้านอาหาร
    """
    # ดึงข้อมูลร้านอาหารและเมนูที่ต้องการแก้ไข
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, owner=request.user)
    food = get_object_or_404(Food, id=food_id, restaurant=restaurant)

    if request.method == 'POST':
        form = FoodForm(request.POST, request.FILES, instance=food)
        if form.is_valid():
            form.save()
            messages.success(request, "แก้ไขเมนูอาหารเรียบร้อยแล้ว!")
            return redirect('restaurant_detail', id=restaurant.id)  # กลับไปที่หน้ารายละเอียดร้านอาหาร
        else:
            messages.error(request, "มีข้อผิดพลาด กรุณาตรวจสอบข้อมูลที่กรอก")
    else:
        form = FoodForm(instance=food)

    return render(request, 'core/food/edit_food.html', {
        'form': form,
        'restaurant': restaurant,
        'food': food
    })

# ฟังก์ชันสำหรับลบเมนูอาหาร
@login_required()
def delete_food(request, restaurant_id, food_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    food = get_object_or_404(Food, id=food_id, restaurant=restaurant)

    # ตรวจสอบว่าผู้ใช้งานเป็นเจ้าของร้านอาหารหรือไม่
    if request.user == restaurant.owner:
        food.delete()

    return redirect('restaurant_detail', id=restaurant_id)
def food_list(request):
    foods = Food.objects.all()  # ดึงข้อมูลอาหารทั้งหมด
    return render(request, 'core/food/food_list.html', {'foods': foods})
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


@login_required
def forum_detail(request, forum_id):
    """แสดงกระทู้และความคิดเห็น"""
    forum = get_object_or_404(Forum, id=forum_id)
    comments = forum.comments.order_by('-created_at')

    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            ForumComment.objects.create(
                forum=forum,
                user=request.user,
                content=content
            )
            messages.success(request, "ความคิดเห็นของคุณถูกบันทึกแล้ว!")
        else:
            messages.error(request, "กรุณากรอกข้อความก่อนแสดงความคิดเห็น")
        return redirect('forum_detail', forum_id=forum_id)

    return render(request, 'core/community/forum_detail.html', {'forum': forum, 'comments': comments})



def my_forums(request):
    forums = Forum.objects.filter(user=request.user)  # แสดงกระทู้ของผู้ใช้ที่ล็อกอิน
    return render(request, 'core/community/forum.html', {'forums': forums})


@login_required
def forum_edit(request, forum_id):
    forum = get_object_or_404(Forum, id=forum_id)

    # ตรวจสอบสิทธิ์: เจ้าของกระทู้หรือ Superuser เท่านั้นที่สามารถแก้ไขได้
    if request.user != forum.user and not request.user.is_superuser:
        return redirect('forum_detail', forum_id=forum.id)  # ถ้าไม่ใช่เจ้าของหรือ superuser ให้ redirect กลับ

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
    forum = get_object_or_404(Forum, pk=pk)

    # ตรวจสอบสิทธิ์: เจ้าของกระทู้หรือ Superuser เท่านั้นที่สามารถลบได้
    if request.user != forum.user and not request.user.is_superuser:
        return redirect('forum_detail', forum_id=forum.id)  # ถ้าไม่ใช่เจ้าของหรือ superuser ให้ redirect กลับ

    if request.method == 'POST':
        forum.delete()
        return redirect('my_forums')  # กลับไปที่หน้ารายการกระทู้

    return render(request, 'core/community/forum_delete.html', {'forum': forum})


logger = logging.getLogger(__name__)

@login_required
@csrf_protect
def add_comment(request, forum_id):
    """เพิ่มความคิดเห็นใหม่"""
    if request.method == 'POST':
        forum = get_object_or_404(Forum, id=forum_id)
        raw_content = request.POST.get('content', '').strip()

        # ล้างข้อความ
        cleaned_content = strip_tags(raw_content)
        if not cleaned_content:
            return JsonResponse({'error': 'กรุณากรอกข้อความที่ต้องการแสดงความคิดเห็น'}, status=400)

        # สร้างความคิดเห็น
        comment = ForumComment.objects.create(
            forum=forum,
            user=request.user,
            content=cleaned_content
        )

        # โหลดความคิดเห็นใหม่
        comments = forum.comments.select_related('user__profile').order_by('-created_at')

        # Render partial template
        html = render_to_string(
            'core/partials/forum_comments.html',
            {'comments': comments, 'request': request},
            request=request
        )

        # Decode URL ที่อาจถูก encode
        sanitized_html = unquote(html)
        return JsonResponse({'html': sanitized_html.strip()})

    return JsonResponse({'error': 'Invalid request method'}, status=400)

'''@login_required
def load_comments(request, forum_id):
    """โหลดความคิดเห็นทั้งหมด"""
    forum = get_object_or_404(Forum, id=forum_id)
    comments = forum.comments.select_related('user__profile').order_by('-created_at')

    # Render partial template
    html = render_to_string(
        'core/partials/forum_comments.html',
        {'comments': comments},
        request=request
    )

    # Debug HTML
    logger.debug(f"Rendered Comments HTML: {html}")

    return HttpResponse(html, content_type='text/html; charset=utf-8')  # กำหนด encoding เพื่อป้องกันปัญหาภาษาแปลก ๆ'''

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(ForumComment, id=comment_id)

    # ✅ อนุญาตให้ลบได้หากเป็นเจ้าของความคิดเห็นหรือเป็น superuser
    if comment.user != request.user and not request.user.is_superuser:
        return HttpResponseForbidden("คุณไม่มีสิทธิ์ลบความคิดเห็นนี้")

    forum_id = comment.forum.id
    comment.delete()
    return redirect('forum_detail', forum_id=forum_id)

@login_required
def edit_comment(request, comment_id):
    """View สำหรับการแก้ไขความคิดเห็น"""
    comment = get_object_or_404(ForumComment, id=comment_id)

    # ✅ อนุญาตให้แก้ไขได้หากเป็นเจ้าของความคิดเห็นหรือเป็น superuser
    if comment.user != request.user and not request.user.is_superuser:
        return HttpResponseForbidden("คุณไม่มีสิทธิ์แก้ไขความคิดเห็นนี้")

    if request.method == "POST":
        new_content = request.POST.get('content', '').strip()
        if new_content:
            comment.content = new_content
            comment.save()
            return redirect('forum_detail', comment.forum.id)  # กลับไปที่หน้า Forum เดิม
        else:
            return HttpResponseForbidden("ไม่สามารถบันทึกความคิดเห็นว่างได้")

    # Render แบบ GET เพื่อแสดงแบบฟอร์ม
    return render(request, 'core/community/edit_comment.html', {'comment': comment})

@login_required
def add_review(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)

    # ตรวจสอบว่าผู้ใช้ได้รีวิวร้านอาหารนี้ไปแล้วหรือไม่
    if Review.objects.filter(restaurant=restaurant, user=request.user).exists():
        messages.error(request, "คุณได้รีวิวร้านนี้ไปแล้ว")
        return redirect('restaurant_detail', id=restaurant.id)  # กลับไปยังหน้ารายละเอียดร้าน

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user  # เชื่อมโยงรีวิวกับผู้ใช้ที่ล็อกอิน
            review.restaurant = restaurant  # เชื่อมโยงรีวิวกับร้านอาหาร
            review.save()
            messages.success(request, "รีวิวของคุณถูกบันทึกแล้ว")
            return redirect('restaurant_detail', id=restaurant.id)  # กลับไปยังหน้ารายละเอียดร้าน
    else:
        form = ReviewForm()

    return render(request, 'core/food/add_review.html', {
        'form': form,
        'restaurant': restaurant,
    })

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    if request.user == review.user or request.user.is_superuser:
        review.delete()
    return redirect('restaurant_detail', id=review.restaurant.id)

@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    # อนุญาตให้แก้ไขได้เฉพาะเจ้าของรีวิวหรือ Super Admin
    if request.user != review.user and not request.user.is_superuser:
        messages.error(request, "คุณไม่มีสิทธิ์แก้ไขรีวิวนี้")
        return redirect('restaurant_detail', id=review.restaurant.id)

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "รีวิวของคุณถูกแก้ไขเรียบร้อยแล้ว!")
            return redirect('restaurant_detail', id=review.restaurant.id)
    else:
        form = ReviewForm(instance=review)

    return render(request, 'core/food/edit_review.html', {'form': form, 'review': review})


@login_required
def toggle_save_restaurant(request, restaurant_id):
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)

    if request.user in restaurant.saved_by.all():
        # ยกเลิกการบันทึก
        restaurant.saved_by.remove(request.user)
        messages.success(request, 'ยกเลิกการบันทึกร้านอาหารเรียบร้อยแล้ว!')
    else:
        # บันทึกร้านอาหาร
        restaurant.saved_by.add(request.user)
        messages.success(request, 'บันทึกร้านอาหารเรียบร้อยแล้ว!')

    return redirect('restaurant_detail', id=restaurant_id)

@login_required
def toggle_save_forum(request, forum_id):
    forum = get_object_or_404(Forum, id=forum_id)

    if request.user in forum.saved_by.all():
        # ยกเลิกการบันทึก
        forum.saved_by.remove(request.user)
        messages.success(request, 'ยกเลิกการบันทึกกระทู้เรียบร้อยแล้ว!')
    else:
        # บันทึกกระทู้
        forum.saved_by.add(request.user)
        messages.success(request, 'บันทึกกระทู้เรียบร้อยแล้ว!')

    return redirect('forum_detail', forum_id=forum_id)

# ฟังก์ชันการแสดงแดชบอร์ด Admin
@login_required
def admin_dashboard(request):
    if request.user.is_superuser:  # ตรวจสอบว่า user เป็น superuser หรือไม่
        # ดึงข้อมูลจำนวนผู้ใช้ทั้งหมดในระบบ
        total_users = User.objects.count()

        # ดึงข้อมูลจำนวนร้านอาหารทั้งหมดในระบบ
        total_restaurants = Restaurant.objects.count()

        # ดึงข้อมูลจำนวนกระทู้ทั้งหมดในระบบ
        total_forums = Forum.objects.count()

        # ส่งข้อมูลไปที่ Template
        return render(request, 'core/adminpage/admin_dashboard.html', {
            'total_users': total_users,
            'total_restaurants': total_restaurants,
            'total_forums': total_forums
        })
    else:
        return render(request, 'core/adminpage/access_denied.html')  # หากไม่ใช่ superuser แสดงหน้าไม่อนุญาต



@login_required
def manage_users(request):
    if request.user.is_superuser:
        # ดึงข้อมูลผู้ใช้ทั้งหมด
        users = User.objects.all()

        # ตรวจสอบว่ามีการค้นหาหรือไม่
        search = request.GET.get('search', '')  # ดึงค่าจากฟอร์มค้นหา

        if search:
            # ถ้ามีการค้นหาให้กรองตามชื่อผู้ใช้หรืออีเมล
            users = users.filter(username__icontains=search) | users.filter(email__icontains=search)

        # ตรวจสอบฟิลเตอร์สถานะผู้ใช้
        status = request.GET.get('status', '')
        if status == 'active':
            users = users.filter(is_active=True)
        elif status == 'inactive':
            users = users.filter(is_active=False)

        return render(request, 'core/adminpage/manage_users.html', {'users': users})

    else:
        messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงหน้านี้")
        return redirect('home')  # เปลี่ยนเป็นหน้าหลักของแอปพลิเคชัน


@login_required
def edit_user(request, user_id):
    if request.user.is_superuser:
        user = get_object_or_404(User, id=user_id)
        if request.method == "POST":
            # อัปเดตข้อมูลผู้ใช้ที่เลือก เช่น อัปเดตบทบาท
            user.is_active = request.POST.get('is_active') == 'on'
            user.is_staff = request.POST.get('is_staff') == 'on'
            user.save()
            messages.success(request, f"ข้อมูลของ {user.username} ได้รับการอัปเดตแล้ว")
            return redirect('manage_users')  # เปลี่ยนไปหน้า manage users
        return render(request, 'core/adminpage/edit_user.html', {'user': user})
    else:
        messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงหน้านี้")
        return redirect('home')  # เปลี่ยนเป็นหน้าหลักของแอปพลิเคชัน

@login_required
def delete_user(request, user_id):
    if request.user.is_superuser:
        user = get_object_or_404(User, id=user_id)
        user.delete()
        messages.success(request, f"ผู้ใช้ {user.username} ถูกลบออกจากระบบแล้ว")
        return redirect('manage_users')
    else:
        messages.error(request, "คุณไม่มีสิทธิ์ลบผู้ใช้นี้")
        return redirect('home')


@login_required
def manage_restaurants(request):
    if request.user.is_superuser:
        # ดึงข้อมูลคำค้นหาจากฟอร์ม
        query = request.GET.get('search', '')

        # ค้นหาจากชื่อร้านและรายละเอียด
        if query:
            restaurants = Restaurant.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
        else:
            restaurants = Restaurant.objects.all()

        return render(request, 'core/adminpage/manage_restaurants.html', {'restaurants': restaurants})
    else:
        messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงหน้านี้")
        return redirect('home')  # เปลี่ยนเป็นหน้าหลักของแอปพลิเคชัน

@login_required
def admin_edit_restaurant(request, restaurant_id):
    if request.user.is_superuser:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)

        if request.method == "POST":
            form = RestaurantForm(request.POST, instance=restaurant)
            if form.is_valid():
                form.save()
                messages.success(request, "แก้ไขร้านอาหารเรียบร้อยแล้ว!")
                return redirect('manage_restaurants')
        else:
            form = RestaurantForm(instance=restaurant)
        return render(request, 'core/adminpage/edit_restaurant.html', {'form': form, 'restaurant': restaurant})
    else:
        messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงหน้านี้")
        return redirect('home')


def is_superuser(user):
    return user.is_superuser

@login_required
@user_passes_test(is_superuser)
def admin_delete_restaurant(request, restaurant_id):
    if request.method == 'POST':
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
        restaurant.delete()
        messages.success(request, "ลบร้านอาหารเรียบร้อยแล้ว!")
        return redirect('manage_restaurants')
    return redirect('manage_restaurants')


@login_required
def manage_forums(request):
   if request.user.is_superuser:
       # ดึงกระทู้ทั้งหมด
       forums = Forum.objects.all().order_by('-created_at')  # เรียงจากใหม่ไปเก่า

       # ค้นหากระทู้
       search_query = request.GET.get('search', '')
       if search_query:
           forums = forums.filter(
               Q(title__icontains=search_query) |  # ค้นหาจากชื่อ
               Q(user__username__icontains=search_query)  # ค้นหาจากชื่อผู้ใช้
           )

       # Pagination (ถ้าต้องการ)
       paginator = Paginator(forums, 10)  # แสดง 10 รายการต่อหน้า
       page_number = request.GET.get('page')
       page_obj = paginator.get_page(page_number)

       context = {
           'forums': page_obj,
           'search_query': search_query,
       }

       return render(request, 'core/adminpage/manage_forums.html', context)
   else:
       messages.error(request, "คุณไม่มีสิทธิ์ในการเข้าถึงหน้านี้")
       return redirect('home')

@login_required
def admin_edit_forum(request, forum_id):
    if request.user.is_superuser:
        forum = get_object_or_404(Forum, id=forum_id)

        if request.method == 'POST':
            form = ForumForm(request.POST, instance=forum)
            if form.is_valid():
                form.save()
                messages.success(request, 'แก้ไขกระทู้เรียบร้อย!')
                return redirect('manage_forums')
        else:
            form = ForumForm(instance=forum)

        return render(request, 'core/adminpage/edit_forum.html', {'form': form, 'forum': forum})
    else:
        messages.error(request, "คุณไม่มีสิทธิ์ในการเข้าถึงหน้านี้")
        return redirect('home')

@login_required
@require_http_methods(["POST"])
def admin_delete_forum(request, forum_id):
    if request.user.is_superuser:
        forum = get_object_or_404(Forum, id=forum_id)
        forum.delete()
        messages.success(request, 'ลบกระทู้เรียบร้อยแล้ว!')
        return redirect('manage_forums')
    else:
        messages.error(request, "คุณไม่มีสิทธิ์ในการลบกระทู้นี้")
        return redirect('home')


def food_detail(request, id):
    food = get_object_or_404(Food, id=id)
    return render(request, 'core/food_detail.html', {'food': food})

@login_required
def recommend_food(request):
    user = request.user
    liked_foods = LikeDislikeFood.objects.filter(user=user)  # ดึงข้อมูลอาหารที่เคยชอบ/ไม่ชอบ

    if not liked_foods.exists():
        messages.warning(request, "คุณยังไม่มีข้อมูลการชอบ/ไม่ชอบอาหาร กรุณาให้คะแนนอาหารก่อน!")
        return render(request, 'core/recommend_food.html', {'recommendations': []})

    # 🔹 1. เตรียมข้อมูล Feature ของอาหาร
    foods = Food.objects.all()
    food_data = []
    food_labels = []
    food_ids = []
    category_list = set()  # เก็บหมวดหมู่ทั้งหมดสำหรับ One-Hot Encoding

    for log in liked_foods:
        food = log.food
        category_names = [c.name for c in food.category.all()]
        category_list.update(category_names)  # เพิ่มชื่อหมวดหมู่เข้าเซ็ต
        food_data.append([food.price, *category_names])
        food_labels.append(1 if log.liked else 0)  # 1 = ชอบ, 0 = ไม่ชอบ
        food_ids.append(food.id)

    if len(food_data) < 5:  # ข้อมูลน้อยเกินไป
        messages.warning(request, "ข้อมูลที่เคยให้คะแนนมีน้อยเกินไป แนะนำให้ให้คะแนนอาหารเพิ่มก่อน!")
        return render(request, 'core/recommend_food.html', {'recommendations': []})

    # 🔹 2. ใช้ One-Hot Encoding กับหมวดหมู่อาหาร
    encoder = OneHotEncoder(handle_unknown='ignore')  # ✅ แก้ไขตรงนี้!
    category_array = np.array(list(category_list)).reshape(-1, 1)
    encoder.fit(category_array)  # Fit ด้วยค่าหมวดหมู่ที่รู้จัก

    transformed_data = []
    for food in food_data:
        price = food[0]
        category_vector = encoder.transform(np.array(food[1:]).reshape(-1, 1)).toarray().sum(axis=0)  # One-Hot
        transformed_data.append([price] + list(category_vector))

    # 🔹 3. ใช้ MinMaxScaler เพื่อให้ค่าราคาอยู่ในช่วง 0-1
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(transformed_data)

    # 🔹 4. เทรนโมเดล RandomForest
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(scaled_data, food_labels)

    # 🔹 5. คัดกรองอาหารที่ยังไม่เคยถูกให้คะแนน
    unseen_foods = foods.exclude(id__in=food_ids)
    if not unseen_foods.exists():
        messages.warning(request, "ไม่มีอาหารที่ยังไม่ได้ให้คะแนน")
        return render(request, 'core/recommend_food.html', {'recommendations': []})

    unseen_data = []
    unseen_food_list = []

    for food in unseen_foods:
        category_names = [c.name for c in food.category.all()]
        category_vector = encoder.transform(np.array(category_names).reshape(-1, 1)).toarray().sum(axis=0)  # One-Hot
        unseen_data.append([food.price] + list(category_vector))
        unseen_food_list.append(food)

    scaled_unseen_data = scaler.transform(unseen_data)  # Normalize ข้อมูลใหม่

    # 🔹 6. ใช้โมเดลคาดเดา และเลือกอาหารที่โมเดลคิดว่าผู้ใช้น่าจะชอบ
    predictions = clf.predict_proba(scaled_unseen_data)[:, 1]  # ใช้ค่าความน่าจะเป็นของการ "ชอบ"
    sorted_indices = np.argsort(predictions)[::-1]  # เรียงจากค่าความน่าจะเป็นสูงสุด
    recommended_foods = [unseen_food_list[i] for i in sorted_indices[:5]]  # แนะนำ 5 อันดับแรก

    return render(request, 'core/recommend_food.html', {
        'recommendations': recommended_foods
    })