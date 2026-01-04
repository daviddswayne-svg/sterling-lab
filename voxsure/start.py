import subprocess
import time
import sys
import os

# New Ports
FE_PORT = 12345
BE_PORT = 12346

def main():
    print("🧹 Cleaning up old processes...")
    os.system("lsof -ti:12345,12346 | xargs kill -9 > /dev/null 2>&1")
    time.sleep(1) # Give the OS a second to release the ports

    print("🚀 Starting VoxSure Forensic Suite...")
    
    # Paths
    base_dir = "/Users/daviddswayne/.gemini/antigravity/scratch/voxsure"
    be_dir = os.path.join(base_dir, "backend")
    fe_dir = os.path.join(base_dir, "app")

    # Start Backend
    print(f"📡 Starting Backend on http://127.0.0.1:{BE_PORT}...")
    be_proc = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=be_dir
    )

    # Start Frontend
    print(f"🌐 Starting Frontend on http://127.0.0.1:{FE_PORT}...")
    fe_proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(FE_PORT), "--bind", "127.0.0.1"],
        cwd=fe_dir
    )

    print("\n✅ VoxSure is officially LIVE!")
    print(f"📍 Application URL: http://127.0.0.1:{FE_PORT}")
    print("------------------------------------------------")
    print("KEEP THIS WINDOW OPEN to stay connected.")
    print("Press Ctrl+C to shut down.")

    try:
        while True:
            time.sleep(1)
            # Check if processes are still alive
            if be_proc.poll() is not None:
                print("❌ Backend crashed! Check terminal output.")
                break
            if fe_proc.poll() is not None:
                print("❌ Frontend crashed! Check terminal output.")
                break
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        be_proc.terminate()
        fe_proc.terminate()

if __name__ == "__main__":
    main()
