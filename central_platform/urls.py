# central_platform/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from core.views import home

urlpatterns = [
    path("admin/", admin.site.urls),

    # Core / Home
    path("", home, name="home"),

    # Apps
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("blogs/", include("blogs.urls", namespace="blogs")),
    path("dashboard/", include("dashboard.urls", namespace="dashboard")),
    path("adminpanel/", include("adminpanel.urls", namespace="adminpanel")),
]

# Media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)