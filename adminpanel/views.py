# adminpanel/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from blogs.models import Blog

from accounts.models import CustomUser


@login_required
def user_list(request):
    """
    Admin panel: list all users and allow:
      - activate/deactivate users
      - change user role
    """
    if request.user.role != "admin":
        return HttpResponseForbidden("Admins only.")

    users = CustomUser.objects.all().order_by("-date_joined")

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        action = request.POST.get("action")
        target_user = get_object_or_404(CustomUser, id=user_id)

        # Prevent admin from deactivating themselves accidentally
        if target_user == request.user and action == "toggle_active":
            messages.error(request, "You cannot deactivate your own account.")
            return redirect("adminpanel:user_list")

        if action == "toggle_active":
            target_user.is_active = not target_user.is_active
            target_user.save()
            state = "activated" if target_user.is_active else "deactivated"
            messages.success(request, f"User {target_user.username} {state}.")
        elif action == "change_role":
            new_role = request.POST.get("role")
            valid_roles = [choice[0] for choice in CustomUser.ROLE_CHOICES]
            if new_role in valid_roles:
                target_user.role = new_role
                target_user.save()
                messages.success(
                    request,
                    f"Role for {target_user.username} changed to {new_role}.",
                )
            else:
                messages.error(request, "Invalid role selected.")

        return redirect("adminpanel:user_list")

    context = {
        "users": users,
        "role_choices": CustomUser.ROLE_CHOICES,
    }
    return render(request, "user_list.html", context)


@login_required
def approve_blog(request, blog_id):
    """
    Admin approves a pending blog
    """
    if request.user.role != "admin":
        return HttpResponseForbidden("Admins only.")

    blog = get_object_or_404(Blog, id=blog_id)

    blog.status = "published"
    blog.approved_by = request.user
    blog.approved_at = timezone.now()
    blog.save()

    messages.success(request, f"Blog '{blog.title}' approved successfully.")
    return redirect("adminpanel:pending_blogs")


@login_required
def reject_blog(request, blog_id):
    """
    Admin rejects a blog
    """
    if request.user.role != "admin":
        return HttpResponseForbidden("Admins only.")

    blog = get_object_or_404(Blog, id=blog_id)

    blog.status = "rejected"
    blog.save()

    messages.warning(request, f"Blog '{blog.title}' rejected.")
    return redirect("adminpanel:pending_blogs")


@staff_member_required
def admin_dashboard(request):

    pending_blogs = Blog.objects.filter(status="pending").order_by("-created_at")

    published_blogs = Blog.objects.filter(status="published").order_by("-created_at")

    rejected_blogs = Blog.objects.filter(status="rejected").order_by("-created_at")

    context = {
        "pending_blogs": pending_blogs,
        "published_blogs": published_blogs,
        "rejected_blogs": rejected_blogs,
    }

    return render(request, "admin_dashboard.html", context)