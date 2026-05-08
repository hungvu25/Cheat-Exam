"""
Configuration module for Screenshot AI Answer Tool
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gemini WebAPI Configuration (using cookies like bot.py)
# Gemini models:
# - gemini-2.5-flash (latest)
# - gemini-2.0-flash-exp
# - gemini-1.5-pro
# Set to None to let Gemini choose account default model automatically.
GEMINI_MODEL = None

# Gemini CLI mode (recommended for better stability than web cookie flow)
USE_GEMINI_CLI = True
GEMINI_CLI_COMMAND = "gemini.cmd"  # Use .cmd on Windows to avoid PowerShell policy issues
GEMINI_CLI_TIMEOUT = 90  # seconds
GEMINI_CLI_FALLBACK_TO_WEBAPI = False
GEMINI_CLI_APPROVAL_MODE = "yolo"  # auto-approve tools to avoid hidden interactive waits
# Use a stable fast model to reduce 429/capacity retry stalls.
GEMINI_CLI_MODEL = "gemini-2.5-flash-lite"
# Hard cap for total WebAPI request duration to avoid indefinite blocking.
GEMINI_WEBAPI_TIMEOUT = 45  # seconds

# Gemini Cookies - Get from browser (like bot.py)
# Option 1: Set in .env file (recommended)
#   GEMINI_SECURE_1PSID=g.a000...
#   GEMINI_SECURE_1PSIDTS=sidts-...
# Option 2: Set directly here
GEMINI_SECURE_1PSID = "g.a0008wgaN4G_3JT-tjjHrwpk5btL6PSpJpDs5NLIGJR1rO62jXzddn7_ZJ1s28UcxHkzqr7cgQACgYKAU0SARQSFQHGX2MiDtz4FQtZ8LQ1hQpdZYgLRRoVAUF8yKpDLYAwvpAZAhvQkzN1xuYI0076"
GEMINI_SECURE_1PSIDTS = "sidts-CjYBWhotCUKCwki9T3oj62dYb74dptOmOeutPgfdJ9EJpGBgPAgSw2SVFAKA3cZuOCUjqDRRnLEQAA"

# Image settings tuned for lower latency.
# Smaller image + JPEG usually improves upload and model processing speed.
IMAGE_MAX_WIDTH = 800
IMAGE_MAX_HEIGHT = 800
IMAGE_QUALITY = 60
USE_PNG = False

def get_gemini_cookies() -> Optional[dict]:
    """Get Gemini cookies from environment variable, .env file, or direct config"""
    # Try environment variables first
    secure_1psid = os.environ.get("GEMINI_SECURE_1PSID") or GEMINI_SECURE_1PSID
    secure_1psidts = os.environ.get("GEMINI_SECURE_1PSIDTS") or GEMINI_SECURE_1PSIDTS
    
    if secure_1psid and secure_1psidts:
        return {
            "Secure_1PSID": secure_1psid,
            "Secure_1PSIDTS": secure_1psidts
        }
    
    return None

# Backward compatibility - keep get_api_key for main.py check
def get_api_key() -> Optional[str]:
    """Compatibility wrapper - returns Secure_1PSID if cookies are set"""
    cookies = get_gemini_cookies()
    return cookies["Secure_1PSID"] if cookies else None

# Prompt template for AI
PROMPT_TEMPLATE = """Đọc đề trắc nghiệm trong ảnh này và chọn đáp án đúng.

QUAN TRỌNG: 
- Nếu chỉ có 1 đáp án đúng: trả về 1 chữ cái (A, B, C hoặc D)
- Nếu có nhiều đáp án đúng: trả về tất cả các đáp án đúng, cách nhau bằng dấu phẩy hoặc không có dấu (ví dụ: "AB" hoặc "A,B" hoặc "A B")
- KHÔNG giải thích
- KHÔNG thêm text nào khác
- Chỉ trả về các chữ cái A, B, C, D

Ví dụ:
- 1 đáp án: A
- Nhiều đáp án: AB hoặc A,B hoặc A B"""

# Hotkey configuration
# Note: Changed from ctrl+shift+s to avoid conflict with Windows Snipping Tool
# DEFAULT_HOTKEY = "ctrl+alt+s"
DEFAULT_HOTKEY = "z"
# Overlay configuration
OVERLAY_DISPLAY_TIME = 7  # seconds

# Overlay position - Có 2 cách:
# Cách 1: Dùng vị trí có sẵn (string)
# OVERLAY_POSITION = "bottom-right"  # top-right, top-left, bottom-right, bottom-left

# Cách 2: Tùy chỉnh pixel chính xác (tuple: (x, y))
# OVERLAY_POSITION = (100, 100)  # Ví dụ: (100, 100) = 100px từ trái, 100px từ trên
# OVERLAY_POSITION = (1800, 50)  # Góc trên phải
# OVERLAY_POSITION = (50, 1000)  # Góc dưới trái
OVERLAY_POSITION = (1800, 1040)  # Góc dưới phải (màn 1920x1080)

OVERLAY_FONT_SIZE = 12  # Small font size like date/time display
OVERLAY_COLOR = "#000000"  # Black color for answer (visible on white background)
