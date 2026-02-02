import os
import re
import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def get_unique_filename(filename):
    """
    If file exists, append a counter to the filename.
    e.g., image.png -> image_1.png -> image_2.png
    """
    if not os.path.exists(filename):
        return filename
    
    base_name, ext = os.path.splitext(filename)
    counter = 1
    
    while True:
        new_filename = f"{base_name}_{counter}{ext}"
        if not os.path.exists(new_filename):
            return new_filename
        counter += 1

def get_image_url(content):
    """
    Extract image URL from bot response content.
    """
    # Regex for markdown image
    markdown_regex = r"!\[.*?\]\((.*?)\)"
    match = re.search(markdown_regex, content)
    if match:
        return match.group(1)
    
    # Regex for raw URL (http/https)
    url_regex = r"(https?://[^\s)]+)"
    match = re.search(url_regex, content)
    if match:
        return match.group(1)
    
    return None

def download_image(url, output_path):
    """
    Download image from URL and save to output_path.
    Returns True if successful, False otherwise.
    """
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Failed to download image: {e}")
        return False

def create_client(api_key=None, timeout=None):
    if not api_key:
        api_key = os.getenv("POE_API_KEY")
    
    if not api_key:
        raise ValueError("POE_API_KEY not found in environment or arguments.")

    return OpenAI(
        api_key=api_key,
        base_url="https://api.poe.com/v1",
        timeout=timeout
    )
