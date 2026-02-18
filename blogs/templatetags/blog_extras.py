from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter(name='clean_markdown')
def clean_markdown(value):
    """
    Template filter to remove markdown symbols from text.
    Usage: {{ blog.content|clean_markdown|linebreaks }}
    """
    if not value:
        return value
    
    import re
    
    # Remove headers
    text = re.sub(r'^#{1,6}\s+', '', value, flags=re.MULTILINE)
    
    # Remove bold
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'__(.+?)__', r'\1', text, flags=re.DOTALL)
    
    # Remove italic (careful not to remove single asterisks in math)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text, flags=re.DOTALL)
    
    # Remove bullet points
    text = re.sub(r'^[\*\-\+]\s+', '', text, flags=re.MULTILINE)
    
    # Remove numbered lists
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # Remove blockquotes
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    
    # Remove links [text](url) -> text
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    
    # Remove images ![alt](url) -> alt text
    text = re.sub(r'!\[(.*?)\]\(.+?\)', r'\1', text)
    
    # Remove code blocks
    text = re.sub(r'```[\w]*\n', '', text)
    text = re.sub(r'```', '', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    
    # Clean extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

@register.filter(name='clean_and_linebreaks')
def clean_and_linebreaks(value):
    """
    Clean markdown AND convert linebreaks to <br> or <p> tags
    Usage: {{ blog.content|clean_and_linebreaks }}
    """
    from django.utils.html import linebreaks
    cleaned = clean_markdown(value)
    return mark_safe(linebreaks(cleaned))