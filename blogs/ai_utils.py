import os
import httpx
import random  # ✅ ADDED THIS IMPORT
import uuid
from dotenv import load_dotenv
import urllib.parse
from django.conf import settings
import time

# Load .env file
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ========================================
# HUGGING FACE SETTINGS
# ========================================
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")

# ✅ FIX: Use the new supported SDXL model
HF_IMAGE_MODEL = os.getenv("HF_IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")

# ✅ The correct router endpoint
HF_IMAGE_URL = f"https://router.huggingface.co/hf-inference/models/{HF_IMAGE_MODEL}"

# ========================================
# GROQ AI FUNCTIONS
# ========================================

def generate_blog(topic: str, tone: str = "Professional yet friendly", word_count: int = 1500) -> dict:
    if not GROQ_API_KEY:
        return {"success": False, "content": "", "error": "GROQ_API_KEY missing in .env"}

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": f"You are an expert blog writer. Write in {tone} tone. Use Markdown."},
            {"role": "user", "content": f"Write a complete blog about: {topic}"}
        ],
        "temperature": 0.7,
        "max_tokens": 4000,
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(GROQ_URL, json=payload, headers=headers)
            if response.status_code != 200:
                return {"success": False, "content": "", "error": f"Groq Error: {response.text}"}
            
            data = response.json()
            return {"success": True, "content": data["choices"][0]["message"]["content"], "error": None}
    except Exception as e:
        return {"success": False, "content": "", "error": str(e)}


def generate_blog_title(topic: str) -> dict:
    if not GROQ_API_KEY: 
        return {"success": False, "titles": [], "error": "No API key"}
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "user", "content": f"Give me 5 catchy blog titles for: {topic}. Return only the titles."}
        ],
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(GROQ_URL, json=payload, headers=headers)
            data = response.json()
            titles = data["choices"][0]["message"]["content"].strip().split("\n")
            return {"success": True, "titles": titles, "error": None}
    except Exception as e:
        return {"success": False, "titles": [], "error": str(e)}


def suggest_categories(content: str) -> dict:
    """AI suggests categories from YOUR EXISTING CATEGORY LIST"""
    from .models import Blog
    
    if not GROQ_API_KEY:
        return {"success": False, "categories": [], "error": "No API key"}

    ALL_CATEGORIES = [cat[0] for cat in Blog.CATEGORY_CHOICES]

    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": f"""You are a category expert.
            Analyze the blog content and return EXACTLY 3 most relevant categories FROM THIS LIST ONLY:
            {ALL_CATEGORIES}
            
            RULES:
            1. Return ONLY the category names, one per line
            2. No numbering, no extra text, no explanations
            3. Never make up a category not in the list
            4. If unsure return General
            """},
            {"role": "user", "content": f"Blog content:\n\n{content[:2000]}"}
        ],
        "temperature": 0.1,
        "max_tokens": 100,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(GROQ_URL, json=payload, headers=headers)
            if response.status_code != 200:
                return {"success": False, "categories": [], "error": response.text}
            
            data = response.json()
            categories_text = data["choices"][0]["message"]["content"]
            
            categories = []
            for cat in categories_text.strip().split("\n"):
                clean_cat = cat.strip()
                if clean_cat in ALL_CATEGORIES and clean_cat not in categories:
                    categories.append(clean_cat)
            
            if "General" not in categories:
                categories.append("General")

            return {"success": True, "categories": categories[:3], "error": None}
    except Exception as e:
        return {"success": False, "categories": [], "error": str(e)}


# ========================================
# POLLINATIONS.AI IMAGE GENERATION
# ========================================
def _save_bytes_to_media(image_bytes: bytes, ext: str = "png") -> dict:
    filename = f"{uuid.uuid4().hex[:16]}.{ext}"
    file_path = os.path.join("blog_images", filename)
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)

    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "wb") as f:
        f.write(image_bytes)

    return {
        "success": True,
        "image_url": f"/media/{file_path}",  # browser-friendly URL
        "file_path": file_path,
        "error": None,
    }


def generate_and_save_image(prompt: str, style: str = "photorealistic", width: int = 768, height: int = 768) -> dict:
    """
    Reliable server-side image generation using Hugging Face Inference API.
    Saves to MEDIA_ROOT/blog_images and returns /media/... URL.
    """

    style_keywords = {
        "photorealistic": "high quality, highly detailed, realistic, professional photography, 4k",
        "digital-art": "digital art, highly detailed, vibrant colors, concept art",
        "anime": "anime style, manga, detailed illustration",
        "illustration": "illustration, detailed, clean lines, artstation",
        "cinematic": "cinematic lighting, ultra detailed, film still",
        "minimalist": "minimalist, clean, simple composition",
    }

    style_suffix = style_keywords.get(style, style_keywords["photorealistic"])
    full_prompt = f"{prompt}, {style_suffix}"

    if not HUGGINGFACE_API_KEY:
        return {
            "success": False,
            "image_url": None,
            "file_path": None,
            "error": "HUGGINGFACE_API_KEY missing in .env (Pollinations is failing with 530, so HF is required)."
        }

    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Accept": "image/png",
        "User-Agent": "Mozilla/5.0",
    }

    payload = {
        "inputs": full_prompt,
        "parameters": {
            "width": width,
            "height": height,
            # You can add: "num_inference_steps": 25, "guidance_scale": 7.5
        }
    }

    # HuggingFace sometimes returns 503 while the model is loading.
    # We'll retry a few times.
    try:
        with httpx.Client(timeout=180.0, follow_redirects=True) as client:
            for attempt in range(1, 5):
                r = client.post(HF_IMAGE_URL, headers=headers, json=payload)

                ct = r.headers.get("content-type", "")
                if r.status_code == 200 and ct.startswith("image/") and len(r.content) > 1000:
                    return _save_bytes_to_media(r.content, ext="png")

                # model loading / queue
                if r.status_code in (503, 529):
                    wait_s = 8
                    try:
                        j = r.json()
                        wait_s = int(j.get("estimated_time", wait_s))
                    except Exception:
                        pass
                    time.sleep(min(wait_s, 15))
                    continue

                # other error
                err_text = r.text
                return {
                    "success": False,
                    "image_url": None,
                    "file_path": None,
                    "error": f"HF error {r.status_code}: {err_text[:300]}"
                }

        return {
            "success": False,
            "image_url": None,
            "file_path": None,
            "error": "HF failed after retries."
        }

    except Exception as e:
        return {
            "success": False,
            "image_url": None,
            "file_path": None,
            "error": str(e)
        }

def enhance_prompt_with_ai(basic_prompt: str) -> str:
    """Uses GROQ AI to enhance a basic image prompt"""
    if not GROQ_API_KEY:
        return basic_prompt
    
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {
                "role": "system", 
                "content": "You are an expert at writing image generation prompts. Enhance the user's basic prompt into a detailed, vivid description. Keep it under 100 words."
            },
            {
                "role": "user", 
                "content": f"Enhance this image prompt: {basic_prompt}"
            }
        ],
        "temperature": 0.8,
        "max_tokens": 150,
    }
    
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(GROQ_URL, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json()
                enhanced = data["choices"][0]["message"]["content"].strip()
                return enhanced
            else:
                return basic_prompt
    except:
        return basic_prompt