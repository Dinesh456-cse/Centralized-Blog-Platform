# core/views.py
from django.shortcuts import render
from blogs.models import Blog


def home(request):
    """
    Home page: show latest published blogs.
    """
    latest_blogs = Blog.objects.filter(status="published").order_by("-created_at")[:5]
    return render(request, "home.html", {"latest_blogs": latest_blogs})