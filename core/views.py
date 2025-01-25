from django.contrib.messages import success
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.utils.html import strip_tags
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods
import re
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
    foods = Food.objects.all()  # เริ่มต้น QuerySet ทั้งหมด

    # กรองอาหารตามเงื่อนไขที่ผู้ใช้กรอก
    if form.is_valid() and request.GET:
        category = form.cleaned_data.get('category')
        min_price = form.cleaned_data.get('min_price')
        max_price = form.cleaned_data.get('max_price')

        if category:
            foods = foods.filter(category__in=category)
        if min_price:
            foods = foods.filter(price__gte=min_price)
        if max_price:
            foods = foods.filter(price__lte=max_price)

        # สุ่มอาหารใหม่และบันทึกลง Session
        if foods.exists():
            food = random.choice(list(foods))
            request.session['selected_food_id'] = food.id  # เก็บ ID อาหารที่สุ่มได้
        else:
            request.session.pop('selected_food_id', None)
            messages.warning(request, "ไม่พบอาหารที่ตรงกับเงื่อนไขการกรอง")

    # การจัดการ POST: รับ food_id จาก hidden field
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, "กรุณาเข้าสู่ระบบก่อน")
            return redirect('login')

        food_id = request.POST.get('food_id')  # ดึง ID จาก hidden field
        try:
            food = Food.objects.get(id=food_id)  # ตรวจสอบว่ามีอาหารนี้หรือไม่
            action = request.POST.get('action')
            liked_status = action == 'like'

            # บันทึกเป็น log ใหม่ทุกครั้ง
            LikeDislikeFood.objects.create(
                user=request.user,
                food=food,
                liked=liked_status,
                timestamp=timezone.now()
            )
            messages.success(request, f"คุณ{'ชอบ' if liked_status else 'ไม่ชอบ'}อาหาร {food.name} แล้ว!")
            return redirect(request.path)  # รีเฟรชหน้า
        except Food.DoesNotExist:
            messages.error(request, "ไม่พบอาหารที่คุณเลือก กรุณาลองใหม่")

    return render(request, 'core/random_food.html', {'food': food, 'form': form})
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

    # คำนวณคะแนนเฉลี่ยดาวของร้านอาหาร
    average_rating = reviews.aggregate(average=Avg('rating'))['average']

    return render(request, 'core/food/restaurant_detail.html', {
        'restaurant': restaurant,
        'foods': foods,
        'categories': categories,
        'reviews': reviews,  # ส่งข้อมูลรีวิวไปยังเทมเพลต
        'user_reviewed': user_reviewed,  # ส่งตัวแปรตรวจสอบการรีวิวไปยังเทมเพลต
        'average_rating': average_rating,  # ส่งคะแนนเฉลี่ยไปยังเทมเพลต
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

        if form.is_valid():
            # บันทึกข้อมูลหลักของร้าน
            restaurant = form.save()

            # อัปเดตหมวดหมู่ (categories)
            categories = request.POST.getlist('categories')
            restaurant.categories.set(categories)

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

    # ตรวจสอบว่าผู้ใช้เป็นเจ้าของความคิดเห็น
    if comment.user != request.user:
        return HttpResponseForbidden("คุณไม่มีสิทธิ์ลบความคิดเห็นนี้")

    forum_id = comment.forum.id
    comment.delete()
    return redirect('forum_detail', forum_id=forum_id)

@login_required
def edit_comment(request, comment_id):
    """View สำหรับการแก้ไขความคิดเห็น"""
    comment = get_object_or_404(ForumComment, id=comment_id)

    # ตรวจสอบว่าผู้ใช้งานเป็นเจ้าของความคิดเห็น
    if comment.user != request.user:
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
    if request.user == review.user:  # ตรวจสอบว่าเป็นเจ้าของรีวิว
        review.delete()
    return redirect('restaurant_detail', id=review.restaurant.id)

@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    if request.user != review.user:  # อนุญาตให้แก้ไขได้เฉพาะเจ้าของรีวิว
        return redirect('restaurant_detail', id=review.restaurant.id)

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            return redirect('restaurant_detail', id=review.restaurant.id)
    else:
        form = ReviewForm(instance=review)

    return render(request, 'core/food/edit_review.html', {'form': form, 'review': review})