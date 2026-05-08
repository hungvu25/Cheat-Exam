"""
Main entry point for Screenshot AI Answer Tool
"""
import keyboard
import sys
import threading
from screenshot import capture_screen
from ai_client import analyze_question
from overlay import AnswerOverlay
from config import DEFAULT_HOTKEY, get_api_key, OVERLAY_DISPLAY_TIME


class ScreenshotAITool:
    """Main class for the screenshot AI tool"""
    
    def __init__(self):
        self.overlay = AnswerOverlay()
        self.processing = False
    
    def check_api_key(self):
        """Check if Gemini cookies are configured"""
        api_key = get_api_key()
        if not api_key:
            print("ERROR: Gemini cookies not found!")
            print("Please set them in config.py or .env file:")
            print("  config.py: Edit GEMINI_SECURE_1PSID and GEMINI_SECURE_1PSIDTS")
            print("  .env file: GEMINI_SECURE_1PSID=g.a000...")
            print("             GEMINI_SECURE_1PSIDTS=sidts-...")
            print("")
            print("How to get cookies:")
            print("  1. Open gemini.google.com in browser")
            print("  2. Login and open DevTools (F12)")
            print("  3. Go to Application > Cookies > https://gemini.google.com")
            print("  4. Copy __Secure-1PSID and __Secure-1PSIDTS values")
            return False
        return True
    
    def process_screenshot(self):
        """Process screenshot and display answer"""
        if self.processing:
            print("⚠ Already processing a request. Please wait...")
            return
        
        self.processing = True
        
        try:
            print("\n" + "="*50)
            print("📸 Capturing screenshot...")
            # Capture screen
            screenshot = capture_screen()
            print(f"✓ Screenshot captured: {screenshot.size[0]}x{screenshot.size[1]} pixels")
            
            print("🤖 Sending to AI for analysis...")
            # Analyze with AI
            answer = analyze_question(screenshot)
            
            if answer:
                print(f"✅ Answer received: {answer}")
                print("🖼️  Displaying overlay...")
                # Display overlay
                self.overlay.show(answer)
                print(f"✓ Overlay should be visible now! (Bottom-right corner, {OVERLAY_DISPLAY_TIME} seconds)")
            else:
                print("❌ Could not determine answer. Please try again.")
                print("   Make sure the question and options A/B/C/D are clearly visible in the screenshot.")
                # Show error overlay
                print("🖼️  Displaying error overlay...")
                self.overlay.show("?")
        
        except KeyboardInterrupt:
            print("\n⚠ Interrupted by user")
            self.processing = False
            return
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            print("🖼️  Displaying error overlay...")
            try:
                self.overlay.show("!")
            except:
                print("⚠ Could not display error overlay")
        
        finally:
            self.processing = False
            print("="*50 + "\n")
    
    def on_hotkey_pressed(self):
        """Callback when hotkey is pressed"""
        print("\n>>> Hotkey detected! Processing...")
        # Run in separate thread to avoid blocking keyboard listener
        try:
            thread = threading.Thread(target=self.process_screenshot, daemon=True)
            thread.start()
        except Exception as e:
            print(f"Error starting processing thread: {e}")
            import traceback
            traceback.print_exc()
            self.processing = False
    
    def start(self):
        """Start the tool and listen for hotkey"""
        if not self.check_api_key():
            sys.exit(1)
        
        print(f"Screenshot AI Answer Tool started!")
        print(f"Press {DEFAULT_HOTKEY} to capture and analyze a question.")
        print("Press Ctrl+C to exit.")
        print()
        
        # Register hotkey
        try:
            keyboard.add_hotkey(DEFAULT_HOTKEY, self.on_hotkey_pressed)
            print(f"✓ Hotkey '{DEFAULT_HOTKEY}' registered successfully!")
            print("Waiting for hotkey press...\n")
        except Exception as e:
            print(f"✗ Error registering hotkey: {e}")
            print("Make sure you're running as Administrator!")
            sys.exit(1)
        
        # Keep the program running
        try:
            keyboard.wait()
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


def main():
    """Main function"""
    tool = ScreenshotAITool()
    tool.start()


if __name__ == "__main__":
    main()
