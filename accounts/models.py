# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    Adds:
      - email (unique)
      - role: 'user' or 'admin'
      - profile_image: optional avatar
    """
    ROLE_CHOICES = (
        ('user', 'User'),
        ('admin', 'Admin'),
    )

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    profile_image = models.ImageField(
        upload_to='profile_images/', blank=True, null=True
    )

    def save(self, *args, **kwargs):
        # Ensure is_staff is in sync with role for admin panel access
        if self.role == 'admin':
            self.is_staff = True
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"