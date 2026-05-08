"""
Overlay module for displaying answer on screen
"""
import tkinter as tk
import threading
from typing import Optional
from config import (
    OVERLAY_DISPLAY_TIME,
    OVERLAY_POSITION,
    OVERLAY_FONT_SIZE,
    OVERLAY_COLOR
)
from screenshot import get_screen_size


class AnswerOverlay:
    """Class to display answer overlay on screen"""
    
    def __init__(self):
        self.root: Optional[tk.Tk] = None
        self.label: Optional[tk.Label] = None
    
    def _calculate_position(self, window_width: int, window_height: int) -> tuple:
        """
        Calculate window position based on configuration
        
        Args:
            window_width: Width of the overlay window
            window_height: Height of the overlay window
        
        Returns:
            Tuple of (x, y) coordinates
        """
        screen_width, screen_height = get_screen_size()
        
        # If OVERLAY_POSITION is a tuple (x, y), use it directly
        if isinstance(OVERLAY_POSITION, tuple) and len(OVERLAY_POSITION) == 2:
            x, y = OVERLAY_POSITION
            print(f"[DEBUG] Using custom position: ({x}, {y})")
            return (x, y)
        
        # Otherwise, use preset positions
        if OVERLAY_POSITION == "top-right":
            x = screen_width - window_width - 20
            y = 20
        elif OVERLAY_POSITION == "top-left":
            x = 20
            y = 20
        elif OVERLAY_POSITION == "bottom-right":
            x = screen_width - window_width - 20
            y = screen_height - window_height - 20
        elif OVERLAY_POSITION == "bottom-left":
            x = 20
            y = screen_height - window_height - 20
        else:  # default to top-right
            x = screen_width - window_width - 20
            y = 20
        
        return (x, y)
    
    def show(self, answer: str):
        """
        Display answer overlay on screen
        
        Args:
            answer: Answer string (e.g., "A", "AB", "ABC") - can be single or multiple answers
        """
        # Hide existing overlay if any
        if self.root:
            self.hide()
        
        # Run overlay in a separate thread to avoid blocking
        thread = threading.Thread(target=self._show_overlay, args=(answer,), daemon=True)
        thread.start()
    
    def _show_overlay(self, answer: str):
        """
        Internal method to show overlay (runs in separate thread)
        
        Args:
            answer: Answer letter (A, B, C, or D)
        """
        try:
            print(f"[DEBUG] Showing overlay with answer: {answer}")
            
            # Create root window
            self.root = tk.Tk()
            self.root.overrideredirect(True)  # Remove window decorations
            self.root.attributes("-topmost", True)  # Always on top
            self.root.lift()  # Bring to front
            self.root.focus_force()  # Force focus
            
            # Use visible background to ensure overlay is always seen
            # Try transparent first, but fallback to visible semi-transparent black
            use_transparent = False
            transparent_color = "gray15"
            
            try:
                self.root.configure(bg=transparent_color)
                self.root.attributes("-transparentcolor", transparent_color)
                use_transparent = True
                label_bg = transparent_color
                print(f"[DEBUG] Using transparent background")
            except Exception as e:
                # Fallback: semi-transparent black background (always visible)
                print(f"[DEBUG] Transparent failed, using visible semi-transparent background: {e}")
                self.root.configure(bg="black")
                try:
                    self.root.attributes("-alpha", 0.7)  # 70% opacity - visible but not too intrusive
                except:
                    pass  # If alpha not supported, use solid black
                label_bg = "black"
                use_transparent = False
            
            # Create label with answer
            # Format answer for display (add spaces between letters if multiple)
            if len(answer) > 1:
                # Multiple answers: display as "A B" or "A B C"
                display_text = ' '.join(answer)
            else:
                # Single answer: display as "A"
                display_text = answer
            
            self.label = tk.Label(
                self.root,
                text=display_text,
                font=("Arial", OVERLAY_FONT_SIZE, "normal"),
                fg=OVERLAY_COLOR,
                bg=label_bg,
                padx=10,
                pady=5
            )
            print(f"[DEBUG] Label created: text='{display_text}' (original: '{answer}'), font_size={OVERLAY_FONT_SIZE}, fg='{OVERLAY_COLOR}', bg='{label_bg}'")
            self.label.pack()
            
            # Update to get window size
            self.root.update_idletasks()
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            # Calculate and set position
            x, y = self._calculate_position(window_width, window_height)
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
            print(f"[DEBUG] Overlay positioned at ({x}, {y}), size: {window_width}x{window_height}")
            
            # Auto-hide after specified time
            self.root.after(OVERLAY_DISPLAY_TIME * 1000, self.hide)
            
            # Hide on click
            self.label.bind("<Button-1>", lambda e: self.hide())
            self.root.bind("<Button-1>", lambda e: self.hide())
            
            # Make sure window is visible and on top
            self.root.deiconify()
            self.root.update()
            self.root.lift()
            self.root.attributes("-topmost", True)
            
            # Force update to ensure visibility
            self.root.update_idletasks()
            self.root.update()
            
            print(f"[DEBUG] Overlay displayed at ({x}, {y}), size: {window_width}x{window_height}")
            print(f"[DEBUG] Will hide in {OVERLAY_DISPLAY_TIME} seconds")
            print(f"[DEBUG] Window visible: {self.root.winfo_viewable()}")
            
            # Start main loop
            self.root.mainloop()
            
        except Exception as e:
            print(f"[ERROR] Failed to show overlay: {e}")
            import traceback
            traceback.print_exc()
    
    def hide(self):
        """Hide and destroy the overlay"""
        if self.root:
            try:
                self.root.destroy()
            except:
                pass
            self.root = None
            self.label = None
