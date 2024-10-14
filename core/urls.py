from django.contrib.auth import views as auth_views
from django.urls import path
from core import views
from django.conf import settings
from django.conf.urls.static import static

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


    #สุ่มอาหาร
    path('random-food/', views.random_food, name='random_food'),

    #ร้านอาหาร
    path('restaurants/', views.restaurant_list, name='restaurant_list'),


    #กระทู้
    path('forum/', views.forum, name='forum'),



]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

