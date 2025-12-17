import os

# Configuration for Bedrock Insurance Agents

# Local Ollama Instance
OLLAMA_HOST = "http://localhost:11434"

# Local ComfyUI Instance
# Assuming standard ComfyUI port, can be overridden if Night Shift uses different one
COMFYUI_HOST = "http://127.0.0.1:8188" 

# Models (Aligned with Swayne Systems standards)
MODELS = {
    "director": "llama3.3",       # Strategic planning
    "writer": "qwen2.5-coder:32b", # Technical writing/HTML
    "marketing": "dolphin-llama3", # Promotional copy
    "reviewer": "verify-llm",     # Compliance (Placeholder)
    "designer": "llama3.3"        # Image Prompting
}

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # .../sterling_lab/bedrock_agents
PROJECT_ROOT = os.path.dirname(BASE_DIR) # .../sterling_lab
DASHBOARD_DIR = os.path.join(PROJECT_ROOT, "dashboard")
DATA_DIR = os.path.join(BASE_DIR, "data") # Inside bedrock_agents/data
ASSETS_DIR = os.path.join(DASHBOARD_DIR, "assets") # New directory for images

# Git Config
GIT_REMOTE = "live"
GIT_BRANCH = "main"

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)
