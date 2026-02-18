# accounts/views.py
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse

from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    UserUpdateForm,
    ProfileUpdateForm,
)


def register_view(request):
    """
    Handle new user registration.
    On success, log the user in and redirect to dashboard.
    """
    if request.user.is_authenticated:
        return redirect("dashboard:dashboard")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Registration successful. You are now logged in.")
            login(request, user)
            return redirect("dashboard:dashboard")
    else:
        form = UserRegistrationForm()

    return render(request, "register.html", {"form": form})


def login_view(request):
    """
    Handle user login.
    """
    if request.user.is_authenticated:
        return redirect("dashboard:dashboard")

    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "Logged in successfully.")
            next_url = request.GET.get("next") or reverse("dashboard:dashboard")
            return redirect(next_url)
    else:
        form = UserLoginForm(request)

    return render(request, "login.html", {"form": form})


@login_required
def logout_view(request):
    """
    Log out current user.
    """
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


@login_required
def profile_update_view(request):
    """
    Update user profile information and profile image.
    """
    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(
            request.POST, request.FILES, instance=request.user
        )
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("accounts:profile")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user)

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
    }
    return render(request, "profile.html", context)