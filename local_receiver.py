import requests
import pyautogui
import time
import sys

# CONFIGURATION
# --------------------------
# PASTE YOUR RENDER URL HERE (Ensure it starts with https://)
BACKEND_URL = "https://your-app-name-here.onrender.com" 
# --------------------------

def main():
    print(f"--- Mouse & Keyboard Local Receiver ---")
    print(f"Connecting to: {BACKEND_URL}")
    print(f"Press Ctrl+C to stop.")
    
    # Fail fast if default URL is not changed
    if "your-app-name-here" in BACKEND_URL:
        url = input("Please enter your Render Backend URL: ").strip()
        if url:
            global BACKEND_URL
            BACKEND_URL = url
    
    # Get Screen Size
    screen_w, screen_h = pyautogui.size()
    print(f"Screen Resolution: {screen_w}x{screen_h}")

    last_error_time = 0

    while True:
        try:
            # Poll the backend for cursor state
            resp = requests.get(f"{BACKEND_URL}/api/cursor", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                
                # Logic:
                # Backend sends normX, normY (0.0 to 1.0)
                # We map to local screen size
                
                # 'x' and 'y' might come as None or 0 if never set
                norm_x = data.get("x", 0)
                norm_y = data.get("y", 0)
                should_click = data.get("click", False)

                # Convert to pixels
                target_x = int(norm_x * screen_w)
                target_y = int(norm_y * screen_h)

                # Move Mouse
                # 'tween' makes it smoother but slower. 0 = instant.
                pyautogui.moveTo(target_x, target_y, duration=0)

                if should_click:
                    print("Click!")
                    pyautogui.click()

            time.sleep(0.05) # Poll ~20 times a second

        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit()
        except Exception as e:
            # Don't spam errors
            if time.time() - last_error_time > 2:
                print(f"Connection Error: {e}")
                last_error_time = time.time()
            time.sleep(1)

if __name__ == "__main__":
    main()
