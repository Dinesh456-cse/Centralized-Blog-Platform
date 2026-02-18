# dashboard/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from accounts.models import CustomUser
from blogs.models import Blog


@login_required
def dashboard_view(request):
    """
    Dashboard for both admin and regular user.
    - Admin: total users, total blogs, recent blogs.
    - User: list of their own blogs.
    """
    if request.user.role == "admin":
        total_users = CustomUser.objects.count()
        total_blogs = Blog.objects.count()
        recent_blogs = Blog.objects.order_by("-created_at")[:5]

        context = {
            "total_users": total_users,
            "total_blogs": total_blogs,
            "recent_blogs": recent_blogs,
        }
        template_name = "admin_dashboard.html"
    else:
        user_blogs = Blog.objects.filter(author=request.user).order_by("-created_at")
        context = {
            "user_blogs": user_blogs,
        }
        template_name = "user_dashboard.html"

    return render(request, template_name, context)