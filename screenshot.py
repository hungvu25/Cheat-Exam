"""
Screenshot module for capturing screen images
"""
import mss
from PIL import Image
from typing import Optional, Tuple


def capture_screen() -> Image.Image:
    """
    Capture the entire screen
    
    Returns:
        PIL Image object of the screenshot
    """
    with mss.mss() as sct:
        # Get the primary monitor
        monitor = sct.monitors[1]  # monitors[0] is all monitors, monitors[1] is primary
        screenshot = sct.grab(monitor)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return img


def capture_region(x: int, y: int, width: int, height: int) -> Image.Image:
    """
    Capture a specific region of the screen
    
    Args:
        x: X coordinate of top-left corner
        y: Y coordinate of top-left corner
        width: Width of the region
        height: Height of the region
    
    Returns:
        PIL Image object of the screenshot
    """
    with mss.mss() as sct:
        monitor = {
            "top": y,
            "left": x,
            "width": width,
            "height": height
        }
        screenshot = sct.grab(monitor)
        
        # Convert to PIL Image
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return img


def get_screen_size() -> Tuple[int, int]:
    """
    Get the screen size
    
    Returns:
        Tuple of (width, height)
    """
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        return (monitor["width"], monitor["height"])
