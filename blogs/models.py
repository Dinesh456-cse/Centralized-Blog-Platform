# blogs/models.py
import json
from django.conf import settings
from django.db import models


class Blog(models.Model):

    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending', 'Pending Review'),
        ('published', 'Published'),
        ('rejected', 'Rejected'),
    )

    CATEGORY_CHOICES = (
        ("Technology", "Technology"),
        ("Education", "Education"),
        ("Health", "Health"),
        ("Travel", "Travel"),
        ("Business", "Business"),
        ("Lifestyle", "Lifestyle"),
        ("Sports", "Sports"),
        ("General", "General"),
    )

    title = models.CharField(max_length=255)
    content = models.TextField()

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default="General",
        blank=True
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blogs",
    )

    # Traditional image upload (optional)
    image = models.ImageField(
        upload_to="blog_images/",
        blank=True,
        null=True
    )

    # Cover image URL - Changed to TextField to handle both URLs and file paths
    cover_image_url = models.TextField(
        blank=True,
        null=True,
        help_text="URL or path of cover image"
    )
    
    cover_image_alt = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Alt text for accessibility"
    )

    # JSON field for ALL images (manual uploads + AI generated)
    all_images = models.TextField(
        blank=True,
        default='[]',
        help_text="JSON array of all blog images"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )

    # Approval tracking
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_blogs"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Rejection reason
    rejection_reason = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    # ═══════════════════════════════════════════════════════════════
    # 🖼️ IMAGE HELPER PROPERTIES
    # ═══════════════════════════════════════════════════════════════

    @property
    def images_list(self):
        """Parse the JSON images field and return as list of dicts"""
        try:
            if self.all_images:
                return json.loads(self.all_images)
            return []
        except (json.JSONDecodeError, TypeError):
            return []

    @property
    def has_cover_image(self):
        """Check if blog has any cover image"""
        if self.cover_image_url:
            # Don't count base64 strings as valid cover images
            if not self.cover_image_url.startswith('data:'):
                return True
        if self.image and self.image.name:
            return True
        return False

    @property
    def get_cover_image_url(self):
        """Get the primary cover image URL safely"""
        # First check cover_image_url (but skip base64 strings)
        if self.cover_image_url:
            if not self.cover_image_url.startswith('data:'):
                return self.cover_image_url
        
        # Then check traditional image field
        if self.image and self.image.name:
            try:
                return self.image.url
            except ValueError:
                pass
        
        # Finally, try to get from images_list
        images = self.images_list
        if images:
            for img in images:
                src = img.get('src', '')
                if src and not src.startswith('data:'):
                    if img.get('isCover', False):
                        return src
            # If no cover marked, return first valid image
            for img in images:
                src = img.get('src', '')
                if src and not src.startswith('data:'):
                    return src
        
        return None


class Notification(models.Model):
    """Notification model for blog-related alerts"""
    
    NOTIFICATION_TYPES = (
        ('blog_submitted', 'Blog Submitted for Review'),
        ('blog_published', 'Blog Published'),
        ('blog_rejected', 'Blog Rejected'),
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_notifications",
        null=True,
        blank=True
    )
    
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES
    )
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    blog = models.ForeignKey(
        'Blog',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.notification_type} - {self.title}"

    @classmethod
    def notify_admins_blog_submitted(cls, blog):
        """Notify all admin users when a blog is submitted"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        admins = User.objects.filter(is_staff=True)
        notifications = []
        
        for admin in admins:
            notifications.append(cls(
                recipient=admin,
                sender=blog.author,
                notification_type='blog_submitted',
                title=f'New Blog: {blog.title[:50]}',
                message=f'{blog.author.username} submitted "{blog.title}" for review.',
                blog=blog
            ))
        
        if notifications:
            cls.objects.bulk_create(notifications)
        
        return len(notifications)

    @classmethod
    def notify_author_blog_published(cls, blog, published_by):
        """Notify author when blog is published"""
        return cls.objects.create(
            recipient=blog.author,
            sender=published_by,
            notification_type='blog_published',
            title='Your Blog is Published! 🎉',
            message=f'Your blog "{blog.title}" has been published.',
            blog=blog
        )

    @classmethod
    def notify_author_blog_rejected(cls, blog, rejected_by, reason=''):
        """Notify author when blog is rejected"""
        message = f'Your blog "{blog.title}" was rejected.'
        if reason:
            message += f' Reason: {reason}'
        
        return cls.objects.create(
            recipient=blog.author,
            sender=rejected_by,
            notification_type='blog_rejected',
            title='Blog Rejected',
            message=message,
            blog=blog
        )