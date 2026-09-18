"""
capture_gif.py — Takes screenshots of the dashboard every second
and saves them as an animated GIF for PPT embedding.

Requirements:
    pip install pillow

Usage:
    1. Start simulation:  python run.py
    2. Open browser:      http://localhost:8080
    3. Run this script:   python capture_gif.py
    4. File saved as:     amr_simulation.gif
"""

import time
import sys

try:
    import PIL
except ImportError:
    print("Installing Pillow...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow"])

from PIL import ImageGrab, Image
import os

OUTPUT_FILE = "amr_simulation.gif"
SCREENSHOTS = 20          # number of frames
INTERVAL_SEC = 0.8        # seconds between frames
RESIZE_TO = (960, 540)    # resize for smaller file size

print("=" * 50)
print("  AMRoboSync — GIF Capture Tool")
print("=" * 50)
print(f"\nCapturing {SCREENSHOTS} frames every {INTERVAL_SEC}s...")
print("Make sure http://localhost:8080 is open in browser!\n")
print("Starting in 3 seconds...")
time.sleep(3)

frames = []
for i in range(SCREENSHOTS):
    # Grab full screen
    img = ImageGrab.grab()
    img = img.resize(RESIZE_TO, Image.LANCZOS)
    frames.append(img)
    print(f"  Frame {i+1}/{SCREENSHOTS} captured")
    time.sleep(INTERVAL_SEC)

# Save as animated GIF
print(f"\nSaving GIF → {OUTPUT_FILE} ...")
frames[0].save(
    OUTPUT_FILE,
    save_all=True,
    append_images=frames[1:],
    optimize=True,
    duration=int(INTERVAL_SEC * 1000),
    loop=0
)

size_kb = os.path.getsize(OUTPUT_FILE) // 1024
print(f"\nDone! File: {OUTPUT_FILE}  ({size_kb} KB)")
print("\nPPT madhe add karnyasathi:")
print("  Insert → Pictures → This Device → amr_simulation.gif")
print("  YA")
print("  Insert → Video → This Device → (screen recording)")
