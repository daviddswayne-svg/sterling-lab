import os

# Configuration for Bedrock Insurance Agents

# Local Ollama Instance
# Use OLLAMA_HOST env var, default to localhost if not set (but in Docker it's usually host.docker.internal)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://10.0.1.1:11434")

# Local ComfyUI Instance
# Set COMFYUI_HOST environment variable to point to your ComfyUI instance
# Examples: http://10.10.10.3:8188 or http://localhost:8188
COMFYUI_HOST = os.getenv("COMFYUI_HOST", "http://10.0.1.1:8188") 

# Models (Aligned with Swayne Systems standards)
MODELS = {
    "director": "llama3.3",       # Strategic planning
    "writer": "dolphin-llama3",       # Technical writing/HTML
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

# Bedrock Specific Config
BEDROCK_CHROMA_PATH = os.path.join(DATA_DIR, "chroma_bedrock_intel")
TICKERS = ["KIE", "CB", "PGR", "AON"] # Insurance ETF and Major Carriers
