from django.urls import path
from . import views

app_name = 'blogs'

urlpatterns = [
    # Blog CRUD
    path('', views.blog_list, name='blog_list'),
    path('create/', views.create_blog, name='blog_create'),  # Fixed: was create_blog, now blog_create
    path('<int:pk>/', views.blog_detail, name='blog_detail'),
    path('<int:pk>/edit/', views.blog_update, name='blog_update'),
    path('<int:pk>/delete/', views.blog_delete, name='blog_delete'),
    
    # Notifications
    path('notifications/', views.notifications_list, name='notifications'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_read'),
    path('notifications/count/', views.get_notification_count, name='notification_count'),
    
    # Admin Review
    path('admin/review/', views.admin_review_panel, name='admin_review'),
    path('admin/quick-approve/<int:pk>/', views.quick_approve, name='quick_approve'),
    path('admin/quick-reject/<int:pk>/', views.quick_reject, name='quick_reject'),
    
    # AI Endpoints
    path('ai/generate-blog/', views.ai_generate_blog, name='ai_generate_blog'),
    path('ai/generate-titles/', views.ai_generate_titles, name='ai_generate_titles'),
    path('ai/generate-image/', views.ai_generate_image, name='ai_generate_image'),
    path('ai/suggest-categories/', views.ai_suggest_categories, name='ai_suggest_categories'),
]