from django.contrib.auth import views as auth_views
from django.urls import path, include
from core import views
from django.conf import settings
from django.conf.urls.static import static

from core.views import app_to_pdf

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('register/', views.register, name='register'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('', views.home, name='home'),  # หน้าแรก

    # ลืมรหัสผ่าน
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='core/resetpassword/password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='core/resetpassword/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='core/resetpassword/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='core/resetpassword/password_reset_complete.html'), name='password_reset_complete'),

    # หน้าโปรไฟล์
    path('profile/', views.profile_view, name='profile_view'),  # ชื่อ profile_view
    # แก้ไขโปรไฟล์
    path('profile/edit/', views.profile_edit, name='profile_edit'),  # ชื่อ profile_edit

    # สุ่มอาหาร
    path('random-food/', views.random_food, name='random_food'),

    # ร้านอาหาร
    path('restaurants/', views.restaurant_list, name='restaurant_list'),
    path('restaurant/create/', views.restaurant_create, name='restaurant_create'),
    path('restaurant/<int:id>/', views.restaurant_detail, name='restaurant_detail'),
    path('restaurant/<int:id>/edit/', views.restaurant_edit, name='restaurant_edit'),
    path('restaurant/<int:pk>/delete/', views.delete_restaurant, name='delete_restaurant'),
    path('restaurant/<int:restaurant_id>/delete_image/<int:image_id>/', views.delete_image, name='delete_image'),

    path('restaurant/<int:restaurant_id>/add_image/', views.add_restaurant_image, name='add_restaurant_image'),


    # เพิ่ม URL สำหรับการจัดการเมนูอาหาร
    path('restaurant/<int:restaurant_id>/add_food/', views.add_food, name='add_food'),  # เพิ่มเมนูอาหาร
    path('restaurant/<int:restaurant_id>/edit_food/<int:food_id>/', views.edit_food, name='edit_food'),  # แก้ไขเมนูอาหาร
    path('restaurant/<int:restaurant_id>/delete_food/<int:food_id>/', views.delete_food, name='delete_food'),
    path('choose_food/<int:food_id>/', views.choose_food, name='choose_food'),
    path('foods/', views.food_list, name='food_list'),  # เพิ่มบรรทัดนี้

    # กระทู้
    path('forum/', views.forum_list, name='forum'),
    path('forum/create/', views.create_forum, name='forum_create'),
    path('forum/<int:forum_id>/', views.forum_detail, name='forum_detail'),
    #path('forum/<int:forum_id>/edit/', views.edit_forum, name='edit_forum'),
   # path('forum/<int:forum_id>/delete/', views.delete_forum, name='delete_forum'),
    path('forum/my/', views.my_forums, name='my_forums'),
    path('forum/<int:forum_id>/edit/', views.forum_edit, name='forum_edit'),
    path('forum/<int:pk>/delete/', views.forum_delete, name='forum_delete'),
    path('forum/<int:forum_id>/comment/', views.add_comment, name='add_comment'),  # ส่งความคิดเห็น
    path('comments/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    path('comments/<int:comment_id>/edit/', views.edit_comment, name='edit_comment'),
    path("select2/", include("django_select2.urls")),
    path('restaurant/<int:restaurant_id>/review/', views.add_review, name='add_review'),
    path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    path('review/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('restaurant/<int:restaurant_id>/toggle-save/', views.toggle_save_restaurant, name='toggle_save_restaurant'),
    path('forum/<int:forum_id>/toggle_save/', views.toggle_save_forum, name='toggle_save_forum'),


    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('manage-users/', views.manage_users, name='manage_users'),  # หน้าแสดงผู้ใช้ทั้งหมด
    path('edit-user/<int:user_id>/', views.edit_user, name='edit_user'),  # หน้าแก้ไขข้อมูลผู้ใช้
    path('delete-user/<int:user_id>/', views.delete_user, name='delete_user'),  # ลบผู้ใช้
    path('manage-restaurants/', views.manage_restaurants, name='manage_restaurants'),
    path('superuser/edit-restaurant/<int:restaurant_id>/', views.admin_edit_restaurant, name='edit_restaurant'),
    path('superuser/restaurant/<int:restaurant_id>/delete/', views.admin_delete_restaurant, name='admin_delete_restaurant'),
    path('manage-forums/', views.manage_forums, name='manage_forums'),  # หน้าจัดการกระทู้
    path('superuser/edit-forum/<int:forum_id>/', views.admin_edit_forum, name='edit_forum'),  # แก้ไขกระทู้
    path('superuser/delete-forum/<int:forum_id>/', views.admin_delete_forum, name='delete_forum'),  # ลบกระทู้
    path('recommend-food/', views.recommend_food, name='recommend_food'),

    path('recommend-food2/', views.recommend_food2, name='recommend_food2'),
    path('food/<int:id>/', views.food_detail, name='food_detail'),
    path('update-location/', views.update_location, name='update_location'),
    path('export-code/<str:app_name>/', app_to_pdf, name='export_code'),
    path('feedback-food/<int:food_id>/', views.feedback_food, name='feedback_food'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
