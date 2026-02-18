# adminpanel/urls.py
from django.urls import path
from . import views

app_name = "adminpanel"

urlpatterns = [
    path("users/", views.user_list, name="user_list"),
    path('approve/<int:blog_id>/', views.approve_blog, name="approve_blog"),
    path('reject/<int:blog_id>/', views.reject_blog, name="reject_blog"),
    path('', views.admin_dashboard, name="admin_dashboard"),
]