# blogs/views.py
import json
import base64
import uuid
import os
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt

from .ai_utils import generate_blog, generate_blog_title, suggest_categories, generate_and_save_image
from .forms import BlogForm
from .models import Blog, Notification
from .utils import clean_markdown_content  # <-- ADD THIS IMPORT


# ═══════════════════════════════════════════════════════════════
# 🖼️ IMAGE PROCESSING UTILITIES
# ═══════════════════════════════════════════════════════════════

def save_base64_image(base64_string, folder='blog_images'):
    """
    Save a base64 encoded image to the media folder.
    Returns the URL path to the saved image, or the original string if it's already a URL.
    """
    if not base64_string:
        return None
    
    # If it's already a URL, return as-is
    if base64_string.startswith('http://') or base64_string.startswith('https://'):
        return base64_string
    
    # If it's already a saved media path, return as-is
    if base64_string.startswith('/media/'):
        return base64_string
    
    # Check if it's a base64 string
    if not base64_string.startswith('data:image'):
        print(f"[DEBUG] Invalid image format, skipping")
        return None
    
    try:
        # Parse: "data:image/png;base64,iVBORw0KGgo..."
        header, encoded = base64_string.split(';base64,')
        
        # Get file extension
        ext = header.split('/')[-1].lower()
        if ext == 'jpeg':
            ext = 'jpg'
        elif ext not in ['jpg', 'png', 'gif', 'webp', 'bmp']:
            ext = 'png'
        
        # Generate unique filename
        filename = f"{uuid.uuid4().hex[:16]}.{ext}"
        
        # Create folder path
        folder_path = os.path.join(settings.MEDIA_ROOT, folder)
        os.makedirs(folder_path, exist_ok=True)
        
        # Full file path
        file_path = os.path.join(folder_path, filename)
        
        # Decode and save
        image_data = base64.b64decode(encoded)
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        # Return the URL path
        saved_url = f"/media/{folder}/{filename}"
        print(f"[DEBUG] ✅ Saved image: {saved_url} ({len(image_data)} bytes)")
        return saved_url
        
    except Exception as e:
        print(f"[ERROR] ❌ Failed to save base64 image: {e}")
        return None


def process_blog_images(blog, all_images_json):
    """
    Process all blog images from JSON.
    - Converts base64 images to files
    - Keeps external URLs as-is
    - Updates blog.all_images with processed URLs
    - Sets cover image
    
    Returns: (processed_images_list, cover_url)
    """
    processed_images = []
    cover_url = None
    cover_alt = blog.title
    
    # Parse images JSON
    try:
        images_list = json.loads(all_images_json) if all_images_json else []
    except (json.JSONDecodeError, TypeError) as e:
        print(f"[ERROR] Failed to parse images JSON: {e}")
        images_list = []
    
    print(f"[DEBUG] Processing {len(images_list)} images...")
    
    for index, img_data in enumerate(images_list):
        src = img_data.get('src', '')
        img_type = img_data.get('type', 'manual')
        img_name = img_data.get('name', f'Image {index + 1}')
        is_cover = img_data.get('isCover', False)
        
        if not src:
            continue
        
        # Process the image source
        if src.startswith('data:image'):
            # Base64 image - save to file
            saved_url = save_base64_image(src, 'blog_images')
            if not saved_url:
                print(f"[DEBUG] ⚠️ Failed to save image {index + 1}")
                continue
        else:
            # Already a URL or path - keep as-is
            saved_url = src
        
        # Add to processed list
        processed_images.append({
            'src': saved_url,
            'type': img_type,
            'name': img_name,
            'isCover': is_cover
        })
        
        # Track cover image
        if is_cover:
            cover_url = saved_url
            cover_alt = img_name
        elif cover_url is None and index == 0:
            # Use first image as cover if none marked
            cover_url = saved_url
            cover_alt = img_name
    
    # Update blog fields
    blog.all_images = json.dumps(processed_images)
    
    if cover_url:
        blog.cover_image_url = cover_url
        blog.cover_image_alt = cover_alt
    
    print(f"[DEBUG] ✅ Processed {len(processed_images)} images, cover: {cover_url}")
    return processed_images, cover_url


# ═══════════════════════════════════════════════════════════════
# 📝 BLOG CRUD VIEWS
# ═══════════════════════════════════════════════════════════════

def blog_list(request):
    """List blogs with pagination and search."""
    blogs = Blog.objects.all().order_by("-created_at")

    # Non-staff users only see published blogs
    if not request.user.is_authenticated or not request.user.is_staff:
        blogs = blogs.filter(status="published")

    # Search
    query = request.GET.get("q")
    if query:
        blogs = blogs.filter(
            Q(title__icontains=query) | 
            Q(content__icontains=query) |
            Q(category__icontains=query)
        )

    # Category filter
    category = request.GET.get("category")
    if category:
        blogs = blogs.filter(category=category)

    # Status filter (admin only)
    if request.user.is_authenticated and request.user.is_staff:
        status = request.GET.get("status")
        if status:
            blogs = blogs.filter(status=status)

    # Pagination
    paginator = Paginator(blogs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Pending count for admin badge
    pending_count = 0
    if request.user.is_authenticated and request.user.is_staff:
        pending_count = Blog.objects.filter(status="pending").count()

    return render(request, "blog_list.html", {
        "blogs": page_obj,
        "page_obj": page_obj,
        "query": query or "",
        "pending_count": pending_count,
        "categories": Blog.CATEGORY_CHOICES,
    })


def blog_detail(request, pk):
    """Show a single blog."""
    blog = get_object_or_404(Blog, pk=pk)

    # Check permissions for non-published blogs
    if blog.status != "published":
        if not request.user.is_authenticated:
            raise Http404("Blog not found")
        if request.user != blog.author and not request.user.is_staff:
            raise Http404("Blog not found")

    return render(request, "blog_detail.html", {"blog": blog})


@login_required
def create_blog(request):
    """Create a new blog."""
    if request.method == "POST":
        form = BlogForm(request.POST, request.FILES, user=request.user)
        
        if form.is_valid():
            blog = form.save(commit=False)
            blog.author = request.user

            # 🧹 CLEAN MARKDOWN FROM CONTENT
            blog.content = clean_markdown_content(blog.content)

            # Get action from form button
            action = request.POST.get("action", "")
            print(f"[DEBUG] Create - Action: '{action}', is_staff: {request.user.is_staff}")

            # Set status based on role and action
            if request.user.is_staff:
                if action == "publish":
                    blog.status = "published"
                    blog.approved_by = request.user
                    blog.approved_at = timezone.now()
                elif action == "draft":
                    blog.status = "draft"
                else:
                    blog.status = form.cleaned_data.get('status', 'published')
            else:
                # Normal user
                if action == "draft":
                    blog.status = "draft"
                else:  # action == "submit" or default
                    blog.status = "pending"

            # Save blog first to get an ID
            blog.save()
            print(f"[DEBUG] Blog created - ID: {blog.pk}")

            # ═══════════════════════════════════════════════════════════════
            # 🖼️ PROCESS AND SAVE IMAGES
            # ═══════════════════════════════════════════════════════════════
            all_images_json = request.POST.get('all_images', '[]')
            print(f"[DEBUG] all_images JSON length: {len(all_images_json)}")
            
            if all_images_json and all_images_json != '[]':
                processed_images, cover_url = process_blog_images(blog, all_images_json)
                blog.save()  # Save with updated image data

            # Handle traditional file upload if provided
            if 'image' in request.FILES:
                blog.image = request.FILES['image']
                blog.save()
                print(f"[DEBUG] Traditional image uploaded")

            print(f"[DEBUG] Blog saved - ID: {blog.pk}, Status: {blog.status}")

            # Notifications
            if blog.status == "pending":
                notify_count = Notification.notify_admins_blog_submitted(blog)
                messages.success(request, f"Blog submitted for review! {notify_count} admin(s) notified.")
            elif blog.status == "published":
                messages.success(request, "Blog published successfully!")
            else:
                messages.success(request, "Blog saved as draft.")

            return redirect("blogs:blog_detail", pk=blog.pk)
        else:
            print(f"[DEBUG] Form errors: {form.errors}")
            messages.error(request, "Please fix the errors below.")
    else:
        form = BlogForm(user=request.user)

    return render(request, "blog_form.html", {
        "form": form,
        "form_title": "Create New Blog"
    })


@login_required
def blog_update(request, pk):
    """Update a blog."""
    blog = get_object_or_404(Blog, pk=pk)
    old_status = blog.status

    # Permission check
    if request.user != blog.author and not request.user.is_staff:
        return HttpResponseForbidden("You are not allowed to edit this blog.")

    if request.method == "POST":
        form = BlogForm(request.POST, request.FILES, instance=blog, user=request.user)

        if form.is_valid():
            blog = form.save(commit=False)
            
            # 🧹 CLEAN MARKDOWN FROM CONTENT
            blog.content = clean_markdown_content(blog.content)
            
            action = request.POST.get("action", "")
            print(f"[DEBUG] Update - Action: '{action}'")

            # Handle status based on role and action
            if request.user.is_staff:
                if action == "publish":
                    blog.status = "published"
                    blog.approved_by = request.user
                    blog.approved_at = timezone.now()
                    blog.rejection_reason = None
                    if old_status != "published":
                        Notification.notify_author_blog_published(blog, request.user)
                        messages.success(request, "Blog published! Author notified.")
                    else:
                        messages.success(request, "Blog updated.")
                elif action == "reject":
                    blog.status = "rejected"
                    blog.approved_by = request.user
                    blog.approved_at = timezone.now()
                    rejection_reason = request.POST.get("rejection_reason", "")
                    blog.rejection_reason = rejection_reason
                    Notification.notify_author_blog_rejected(blog, request.user, rejection_reason)
                    messages.warning(request, "Blog rejected. Author notified.")
                elif action == "draft":
                    blog.status = "draft"
                    messages.info(request, "Saved as draft.")
                else:
                    messages.success(request, "Blog updated.")
            else:
                # Normal user
                if action == "submit":
                    blog.status = "pending"
                    if old_status != "pending":
                        notify_count = Notification.notify_admins_blog_submitted(blog)
                        messages.success(request, f"Submitted for review! {notify_count} admin(s) notified.")
                    else:
                        messages.success(request, "Blog updated.")
                elif action == "draft":
                    blog.status = "draft"
                    messages.info(request, "Saved as draft.")
                else:
                    messages.success(request, "Blog updated.")

                # Ensure normal users can't set invalid status
                if blog.status not in ["draft", "pending"]:
                    blog.status = "pending"

            # ═══════════════════════════════════════════════════════════════
            # 🖼️ PROCESS AND SAVE IMAGES
            # ═══════════════════════════════════════════════════════════════
            all_images_json = request.POST.get('all_images', '')
            print(f"[DEBUG] all_images JSON length: {len(all_images_json)}")
            
            if all_images_json and all_images_json != '[]':
                processed_images, cover_url = process_blog_images(blog, all_images_json)

            # Handle traditional file upload
            if 'image' in request.FILES:
                blog.image = request.FILES['image']

            blog.save()
            print(f"[DEBUG] Blog updated - ID: {blog.pk}, Status: {blog.status}")
            return redirect("blogs:blog_detail", pk=blog.pk)
        else:
            print(f"[DEBUG] Form errors: {form.errors}")
            messages.error(request, "Please fix the errors.")
    else:
        form = BlogForm(instance=blog, user=request.user)

    # Get existing images for the form
    existing_images = blog.images_list if blog.all_images else []

    return render(request, "blog_form.html", {
        "form": form,
        "form_title": "Edit Blog",
        "blog": blog,
        "existing_images_json": json.dumps(existing_images),
    })


@login_required
def blog_delete(request, pk):
    """Delete a blog."""
    blog = get_object_or_404(Blog, pk=pk)

    if request.user != blog.author and not request.user.is_staff:
        return HttpResponseForbidden("You are not allowed to delete this blog.")

    if request.method == "POST":
        blog.delete()
        messages.success(request, "Blog deleted successfully.")
        return redirect("blogs:blog_list")

    return redirect("blogs:blog_detail", pk=pk)


# ═══════════════════════════════════════════════════════════════
# 🔔 NOTIFICATION VIEWS
# ═══════════════════════════════════════════════════════════════

@login_required
def notifications_list(request):
    """Show all notifications for current user"""
    notifications = Notification.objects.filter(recipient=request.user)
    
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'unread':
        notifications = notifications.filter(is_read=False)
    
    unread_count = Notification.objects.filter(
        recipient=request.user, 
        is_read=False
    ).count()
    
    return render(request, "notifications.html", {
        "notifications": notifications[:50],
        "unread_count": unread_count,
        "filter_type": filter_type,
    })


@login_required
def mark_notification_read(request, pk):
    """Mark notification as read"""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save()
    
    if notification.blog:
        return redirect("blogs:blog_detail", pk=notification.blog.pk)
    
    return redirect("blogs:notifications")


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(
        recipient=request.user, 
        is_read=False
    ).update(is_read=True)
    
    messages.success(request, "All notifications marked as read.")
    return redirect("blogs:notifications")


@login_required
def get_notification_count(request):
    """AJAX: Get unread notification count"""
    count = Notification.objects.filter(
        recipient=request.user, 
        is_read=False
    ).count()
    
    response = {"count": count}
    
    if request.user.is_staff:
        pending_count = Blog.objects.filter(status="pending").count()
        response["pending_count"] = pending_count
    
    return JsonResponse(response)


# ═══════════════════════════════════════════════════════════════
# 👨‍💼 ADMIN REVIEW VIEWS
# ═══════════════════════════════════════════════════════════════

@login_required
def admin_review_panel(request):
    """Admin panel to review pending blogs"""
    if not request.user.is_staff:
        return HttpResponseForbidden("Admin access only.")
    
    pending_blogs = Blog.objects.filter(status="pending").order_by("-created_at")
    
    stats = {
        'pending': Blog.objects.filter(status="pending").count(),
        'published': Blog.objects.filter(status="published").count(),
        'rejected': Blog.objects.filter(status="rejected").count(),
        'draft': Blog.objects.filter(status="draft").count(),
    }
    
    return render(request, "admin_review.html", {
        "pending_blogs": pending_blogs,
        "stats": stats,
    })


@login_required
@require_http_methods(["POST"])
def quick_approve(request, pk):
    """Quick approve a blog"""
    if not request.user.is_staff:
        return JsonResponse({"success": False, "error": "Admin only."})
    
    blog = get_object_or_404(Blog, pk=pk)
    blog.status = "published"
    blog.approved_by = request.user
    blog.approved_at = timezone.now()
    blog.save()
    
    Notification.notify_author_blog_published(blog, request.user)
    
    return JsonResponse({
        "success": True,
        "message": f"'{blog.title}' published!"
    })


@login_required
@require_http_methods(["POST"])
def quick_reject(request, pk):
    """Quick reject a blog"""
    if not request.user.is_staff:
        return JsonResponse({"success": False, "error": "Admin only."})
    
    blog = get_object_or_404(Blog, pk=pk)
    reason = request.POST.get("reason", "")
    
    blog.status = "rejected"
    blog.approved_by = request.user
    blog.approved_at = timezone.now()
    blog.rejection_reason = reason
    blog.save()
    
    Notification.notify_author_blog_rejected(blog, request.user, reason)
    
    return JsonResponse({
        "success": True,
        "message": f"'{blog.title}' rejected."
    })


# ═══════════════════════════════════════════════════════════════
# 🤖 AI ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@require_http_methods(["POST"])
def ai_generate_blog(request):
    topic = request.POST.get("topic", "").strip()
    tone = request.POST.get("tone", "Professional yet friendly")

    if not topic:
        return JsonResponse({"success": False, "error": "Please enter a topic."})

    result = generate_blog(topic, tone)

    # 🧹 CLEAN MARKDOWN FROM AI RESPONSE BEFORE SENDING TO FRONTEND
    if result.get("success") and "content" in result:
        result["content"] = clean_markdown_content(result["content"])

    return JsonResponse(result)


@require_http_methods(["POST"])
def ai_generate_titles(request):
    topic = request.POST.get("topic", "").strip()

    if not topic:
        return JsonResponse({"success": False, "error": "Please enter a topic."})

    result = generate_blog_title(topic)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["POST"])
def ai_generate_image(request):
    prompt = request.POST.get("prompt", "").strip()
    style = request.POST.get("style", "photorealistic")

    if not prompt:
        return JsonResponse({"success": False, "error": "Please enter a prompt."}, status=400)

    result = generate_and_save_image(prompt, style)

    if result["success"]:
        return JsonResponse({
            "success": True,
            "image_url": result["image_url"],  # This is now /media/blog_images/xxx.png
            "file_path": result["file_path"],
            "media_url": result["image_url"],  # Same as image_url
            "prompt": prompt,
            "style": style
        })
    else:
        return JsonResponse({"success": False, "error": result["error"]}, status=500) 

@require_http_methods(["POST"])
def ai_suggest_categories(request):
    content = request.POST.get("content", "").strip()

    if not content or len(content) < 100:
        return JsonResponse({
            "success": False,
            "error": "Write at least 100 characters for AI to analyze."
        })

    result = suggest_categories(content)
    return JsonResponse(result)