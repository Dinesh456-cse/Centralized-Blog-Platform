# blogs/utils.py
import re

def clean_markdown_content(content):
    """
    Remove markdown symbols from AI-generated content while preserving readability.
    """
    if not content:
        return ""

    # Remove headers (### Header -> Header)
    content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)

    # Remove bold (**text** -> text)
    content = re.sub(r'\*\*(.+?)\*\*', r'\1', content, flags=re.DOTALL)
    content = re.sub(r'__(.+?)__', r'\1', content, flags=re.DOTALL)

    # Remove italic (*text* -> text)
    content = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', content, flags=re.DOTALL)
    content = re.sub(r'_(.+?)_', r'\1', content, flags=re.DOTALL)

    # Remove bullet lists (* item -> item)
    content = re.sub(r'^[\*\-\+]\s+', '', content, flags=re.MULTILINE)

    # Remove numbered lists (1. item -> item)
    content = re.sub(r'^\d+\.\s+', '', content, flags=re.MULTILINE)

    # Remove blockquotes (> quote -> quote)
    content = re.sub(r'^>\s+', '', content, flags=re.MULTILINE)

    # Remove links [text](url) -> text
    content = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', content)

    # Remove images ![alt](url) -> alt
    content = re.sub(r'!\[(.*?)\]\(.+?\)', r'\1', content)

    # Remove code blocks
    content = re.sub(r'```[\w]*\n', '', content)
    content = re.sub(r'```', '', content)
    content = re.sub(r'`(.+?)`', r'\1', content)

    # Clean extra whitespace
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r'^\s+$', '', content, flags=re.MULTILINE)

    return content.strip()