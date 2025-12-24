
import sys
import os

# Ensure we can import from current directory
sys.path.append(os.getcwd())

try:
    print("🚀 Starting Manual Meeting Debug...")
    from bedrock_agents.orchestrator import run_meeting_generator
    
    for agent, message in run_meeting_generator():
        print(f"[{agent}] {message}")
        
    print("✅ Meeting Finished Successfully")
except Exception as e:
    print(f"❌ MEETING CRASHED: {e}")
    import traceback
    traceback.print_exc()
