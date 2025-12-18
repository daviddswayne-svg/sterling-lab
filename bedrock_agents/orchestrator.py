import sys
import time
import socket
import subprocess
import os
from .staff.content_director import ContentDirector
from .staff.web_developer import WebDeveloper
from .staff.publishing_manager import PublishingManager
from .staff.photo_designer import PhotoDesigner

COMFY_DIR = "/Users/daviddswayne/.gemini/antigravity/scratch/night_shift_studio"

def check_and_start_comfyui():
    """Checks if ComfyUI is running on port 8188, starts it if not."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', 8188))
    sock.close()
    
    if result == 0:
        print("✅ ComfyUI is already running.")
        return

    print("⚠️ ComfyUI is NOT running. Starting it now...")
    try:
        # Start ComfyUI in background
        subprocess.Popen(
            ["python3", "main.py", "--listen", "--port", "8188"],
            cwd=COMFY_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("⏳ Waiting for ComfyUI to initialize (10s)...")
        time.sleep(10)
        print("✅ ComfyUI started.")
    except Exception as e:
        print(f"❌ Failed to start ComfyUI: {e}")

def run_meeting_generator():
    """Yields (agent_name, status_message) tuples for streaming."""
    yield "system", "Checking visual cortex (ComfyUI)..."
    check_and_start_comfyui()
    
    # 1. Content Director Plans
    director = ContentDirector()
    try:
        yield "director", "Analyzing market trends & drafting brief..."
        brief = director.create_daily_brief()
        yield "director", f"Theme selected: {brief['theme']}"
    except Exception as e:
        yield "error", f"Director Failed: {e}"
        return

    # 2. Photo Designer Creates Assets
    designer = PhotoDesigner()
    image_path = None
    try:
        yield "designer", "Composing high-fidelity imagery..."
        # Extract concept if available, otherwise use title
        concept = brief.get('image_concept', brief['title'])
        image_path = designer.generate_image(brief['theme'], concept)
        yield "designer", "Image rendering complete."
    except Exception as e:
        yield "designer", f"Rendering failed (Using Stock): {e}"

    # 3. Web Developer Builds (with Image)
    web_dev = WebDeveloper()
    try:
        yield "developer", "Coding responsive HTML structure..."
        html_content = web_dev.build_page(brief, image_path)
        yield "developer", "Frontend code compiled."
    except Exception as e:
        yield "error", f"Web Dev Failed: {e}"
        return

    # 4. Publishing Manager Deploys
    publisher = PublishingManager()
    try:
        yield "publisher", "Deploying to production container..."
        publisher.update_website(html_content, brief['theme'])
        yield "publisher", "Live deployment successful."
    except Exception as e:
        yield "error", f"Publisher Failed: {e}"

    yield "system", "Meeting Adjourned"

def main():
    print("========================================")
    print("🏢 Bedrock Insurance - Daily Cycle Start")
    print("========================================")
    
    # Simple wrapper for CLI usage
    for agent, msg in run_meeting_generator():
        print(f"[{agent.upper()}] {msg}")

if __name__ == "__main__":
    main()
