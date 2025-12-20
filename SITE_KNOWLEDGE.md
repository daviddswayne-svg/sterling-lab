# Sterling Lab / Swayne Systems - Complete Site Knowledge Base

## Overview
**swaynesystems.ai** is a hybrid AI infrastructure platform combining cloud hosting with local AI processing. The site showcases advanced AI capabilities, RAG systems, and creative portfolio work.

---

## Site Pages & Components - Detailed Breakdown

### 1. Dashboard Landing Page (`/`)

**Purpose**: Professional portfolio showcase and navigation hub  
**Tech Stack**: Pure HTML5, CSS3, JavaScript (no frameworks)

**Key Features**:
- **Animated Gradient Background**: CSS keyframe animations creating flowing color gradients
- **Responsive Grid Layout**: Flexbox-based cards for services and portfolio items
- **Status Indicators**: Real-time system health badges ("All Systems Operational")
- **Hero Section**: Large Swayne Systems logo with deployment success badge

**Interactive Elements**:
```html
<!-- Primary CTAs -->
<a href="/lab/">Launch Sterling Lab AI Chat</a>
<a href="/bedrock/">Bedrock Insurance Demo</a>
```

**Embedded iframes**:
- T4 Bacteriophage voxel simulation (see below)
- YouTube production reel
- Seattle Monorail voxel scene

---

### 2. Sterling Lab (`/lab/`) - AI Chat Interface

**Purpose**: Advanced AI chat with RAG, multi-model support, and Council Mode  
**Tech Stack**: Python Streamlit, LangChain, ChromaDB, Ollama

**Architecture**:
```python
# Core Components
- Streamlit UI (chat_app.py)
- ChromaDB vector store (embedded vectors)
- LangChain ConversationalRetrievalChain
- Ollama for local LLM hosting
```

**Key Features**:

**A. RAG Pipeline (Document Intelligence)**
```python
# Process Flow:
1. User query → Embed with nomic-embed-text
2. ChromaDB similarity search → Retrieve relevant docs
3. Context + query → LLM (qwen2.5-coder, llama3.3, etc.)
4. LLM response includes source citations
5. Display with token metrics and streaming
```

**Document Collection**: 8+ estate documents ingested:
- Last Will (2020)
- Commander Instructions
- Groundskeeper Log
- Secret Email correspondence
- Assets estimate

**B. Council Mode (Multi-Agent System)**
- **Manager Model**: Handles primary reasoning (user-selected)
- **Worker Model**: `llama3.3` on Mac Studio (via SSH tunnel)
- **Operation**: Distributed processing across two LLMs
  ```python
  # Pseudo-code
  if council_mode_enabled:
      manager_response = primary_llm.invoke(query)
      worker_response = remote_llm.invoke(query)
      combined_output = synthesize(manager, worker)
  ```

**C. Model Selection**
- Sidebar dropdown with all available Ollama models
- Real-time model switching mid-conversation
- Persistent conversation memory across model changes

**D. Token Metrics & Streaming**
```python
# Real-time display during generation:
🪙 Generating... | Output Tokens: 157
# After completion:
Input: 1,234 | Output: 567 | Total: 1,801 | Speed: 45.2 t/s
```

**E. Chat History (SQLite)**
- Persistent storage of all conversations
- Session-based retrieval and recall
- Sidebar toggle to view archives

---

### 3. Bedrock Insurance (`/bedrock/`) - AI Agent Demonstration

**Purpose**: Showcase autonomous multi-agent workflow for content generation  
**Tech Stack**: Custom HTML/JS chat interface + Python orchestrator backend

**The Bedrock "Staff" - LLM-Powered Agents**:

#### **Agent Workflow** (`bedrock_agents/orchestrator.py`):
```python
def run_meeting_generator():
    # 1. Content Director (LLM Agent)
    director = ContentDirector()
    brief = director.create_daily_brief()
    # Creates: theme, title, image_concept, content_strategy
    
    # 2. Photo Designer (ComfyUI + LLM)
    designer = PhotoDesigner()
    image_path = designer.generate_image(brief['theme'], brief['image_concept'])
    # Uses ComfyUI API + Flux.1 model for image generation
    
    # 3. Web Developer (LLM Agent)
    web_dev = WebDeveloper()
    html_content = web_dev.build_page(brief, image_path)
    # Generates complete HTML/CSS for insurance page
    
    # 4. Publishing Manager (LLM Agent)
    publisher = PublishingManager()
    publisher.update_website(html_content, brief['theme'])
    # Deploys live to /bedrock/ page
```

**Frontend Chat Interface**:
- **Real-time streaming**: "Typing..." indicators while agent works
- **TTS Integration**: ElevenLabs voice narrates responses
  ```javascript
  // After LLM response completes:
  fetch('/api/tts', {
      method: 'POST',
      body: JSON.stringify({ text: response })
  })
  .then(blob => playAudioBlob(blob))
  ```
- **Mute Button (🔇)**: Stop audio playback mid-response
- **Web Audio API**: Decodes MP3 and plays with buffer sources

**Agent Personalities**:
Each agent has its own system prompt defining role, expertise, and output format. They collaborate on a single deliverable.

---

### 4. Voxel Simulations (Embedded)

#### **T4 Bacteriophage**
- **URL**: `https://daviddswayne-svg.github.io/Voxel-Art/`
- **Tech**: Three.js (WebGL), JavaScript
- **What it does**: 3D voxel animation of bacteriophage virus injecting DNA into bacteria
- **Interaction**: Real-time rotation, zoom, particle systems

#### **Seattle Monorail**
- **URL**: `https://daviddswayne-svg.github.io/Voxel-Seattle-Center-V4/`
- **Tech**: Three.js voxel rendering
- **Scene**: Seattle Center with monorail, buildings, and animated elements
- **Interaction**: Click-to-launch from static preview image

**Display Method**:
```html
<iframe src="https://daviddswayne-svg.github.io/Voxel-Art/" 
        frameborder="0" allowfullscreen loading="lazy">
</iframe>
```

---

### 5. Antigravity Chat Widgets

Two separate implementations with different access levels and features (see "Antigravity Chat System" section for full details).

---

## AI Infrastructure

### Local AI Processing (Mac Studio M3 Ultra)
**Location**: User's home office  
**Connection**: SSH tunnel from cloud server

**Ollama Models**:
- `llama3.3:70b` - Primary reasoning model
- `qwen2.5-coder:32b` - Code generation
- `dolphin-llama3` - General purpose
- `nomic-embed-text` - Text embeddings for RAG

**Ollama Access**:
- Local: `http://localhost:11434`
- From Cloud: `http://host.docker.internal:11434` (via SSH tunnel)

**ElevenLabs TTS API** (Local):
- API: `elevenlabs_api.py` on port 8000
- Voice ID: `rjgzTjOCnuup89lc2ELP` (David's cloned voice)
- Model: `eleven_turbo_v2_5` (fastest)
- Accessed from cloud via tunnel: `http://10.0.1.1:8001/generate`

### Cloud AI Services
**Gemini 2.0 Flash** (Google AI):
- Powers both Antigravity chat interfaces
- Streaming responses for real-time display
- Public chat: Rate-limited (20 messages/hour per IP)
- Admin chat: IP-whitelisted access only

**ComfyUI** (Image Generation):
- Runs on Mac Studio
- Used by Bedrock Photo Designer agent
- Flux.1 model for high-quality images

---

## RAG (Retrieval-Augmented Generation) System

### Vector Database: ChromaDB
**Documents Ingested**: 8+ estate-related documents
- Last Will (2020)
- Commander Instructions
- Groundskeeper Log
- Secret Email
- Assets Estimate

**Embedding Model**: `nomic-embed-text`  
**Storage**: `/app/chroma_db` in Docker container  
**Query Flow**:
1. User asks question
2. Embeddings generated for query
3. Similar documents retrieved from ChromaDB
4. Context + query sent to LLM
5. LLM generates answer based on retrieved docs

---

## Bedrock Multi-Agent System

### Agent Roles
1. **Content Director**: Strategy and messaging
2. **Web Developer**: Technical implementation
3. **Photo Designer**: Image generation via ComfyUI
4. **Publishing Manager**: Final review and coordination

### Orchestration Pattern
- coordinator sends tasks to agents
- Agents respond with specialized output
- Results aggregated and presented to user

### TTS Integration (Bedrock Only)
- After LLM response completes, text sent to `/api/tts`
- Flask proxies to local Mac (`10.0.1.1:8001`)
- ElevenLabs generates MP3 audio
- Frontend plays audio via Web Audio API
- Mute button (🔇) allows stopping playback

---

## Antigravity Chat System

### Two Implementations

**1. Admin Chat (Gear Icon ⚙️)**
- **Visibility**: Only for whitelisted IPs (e.g., `71.197.228.171`)
- **Location**: Top-right corner (green gear button)
- **Backend**: `/api/antigravity/chat`
- **Model**: Gemini 2.0 Flash
- **Features**: Full system access, debugging conversations
- **TTS**: DISABLED (text-only for rapid debugging)

**2. Public Chat (Speech Bubble 💬)**
- **Visibility**: Always visible to all visitors
- **Location**: Bottom-left corner (green bubble)
- **Backend**: `/api/antigravity/public/chat`
- **Model**: Gemini 2.0 Flash
- **Rate Limit**: 20 messages per hour per IP
- **Features**:
  - Instant "🔍 Analyzing..." feedback message
  - Streaming text responses (word-by-word)
  - Matrix code rain background animation
  - Concise responses (2-3 paragraphs max)
- **TTS**: DISABLED (text-only for performance)
- **Restrictions**: Read-only, cannot execute commands or modify files

---

## SSH Tunnel Configuration

**Purpose**: Secure connection between cloud and local AI infrastructure  
**Technology**: `autossh` maintains persistent tunnel  
**Ports Forwarded**:
- Ollama service (port 11434)
- TTS API (local port 8000 → remote port 8001)

**Why port 8001?** Avoids conflict with Coolify on cloud server.

---

## Deployment Pipeline

### Git Strategy (Dual Remotes)
1. **Live Server**: Bare git repository on cloud droplet
   - Coolify watches this repo for changes
   - Auto-deploys on push

2. **GitHub Backup**: Public repository
   - Synced automatically via deployment script

### Deployment Process
```bash
# Deployment script pushes to both remotes
# Triggers Coolify rebuild (30-60 seconds)
```

**Coolify**: Auto-deploys on git push
- Builds Docker container
- Runs startup script → starts Flask, Streamlit, Nginx
- Typically takes 30-60 seconds to rebuild

---

## Docker Environment

**Container Network**: Coolify uses custom bridge network  
**Gateway IP**: `10.0.1.1` (Coolify default)  
**Why not standard `172.17.0.1`?** Coolify uses custom networking.

**Container Services**:
1. Flask API (port 5000)
2. Streamlit (port 8501)
3. Nginx (port 80)

**Startup Sequence**:
1. Run RAG diagnostics
2. Verify dashboard files exist
3. Test Nginx config
4. Start Flask API
5. Start Streamlit
6. Start Nginx (foreground)
7. Verify all services responding

---

## Creative Portfolio

### Featured Projects

**T4 Bacteriophage Simulation**
- **Tech**: Interactive 3D voxel rendering
- **URL**: [GitHub Pages](https://daviddswayne-svg.github.io/Voxel-Art/)
- **Display**: Embedded iframe on dashboard

**Seattle Voxel Monorail**
- **Tech**: 3D voxel scene with real-time rendering
- **URL**: [GitHub Pages](https://daviddswayne-svg.github.io/Voxel-Seattle-Center-V4/)
- **Assets**: Preview image in `/assets/monorail_preview.png`

**AI Production Reel**
- **URL**: [YouTube](https://www.youtube.com/embed/-jEpskz8DGE)
- **Content**: Generative AI video workflows demo

---

## Security & Access Control

### Authentication
**Admin Access**: IP whitelist system
- Admin users identified by IP address
- Admin chat button only visible to whitelisted users
- Configured via environment variables

**Public Access**: Rate limiting
- 20 messages/hour per IP address
- Sliding 1-hour window
- Returns 429 error when limit exceeded

### Security Practices
- Environment variable-based configuration
- No hardcoded credentials in code
- Separate admin and public endpoints
- Rate limiting on public endpoints

---

## Known Issues & Quirks

1. **TTS Latency**: Full response must generate before audio starts  
   - Cannot stream TTS (ElevenLabs needs complete text)
   - Text streams to user while audio generates

2. **Docker Gateway IP**: Must use `10.0.1.1` on Linux/Coolify  
   - `host.docker.internal` fails in production
   - Works on Mac dev environment, not on DigitalOcean

3. **Nginx Path Stripping**: `/api/` prefix stripped before Flask  
   - Frontend calls `/api/tts`  
   - Nginx proxies to Flask on `/tts`
   - Flask routes must not include `/api/` prefix

4. **Filler Audio Removed**: Initial "One moment..." TTS was annoying  
   - Replaced with instant text feedback instead

5. **Coolify Port Conflict**: Port 8000 occupied by Coolify  
   - TTS tunnel uses port 8001 instead

---

## Technology Stack Summary

### Languages
- Python (Flask, Streamlit, FastAPI)
- JavaScript (ES6+)
- HTML5/CSS3

### Frameworks
- Flask (backend API)
- Streamlit (chat interface)
- FastAPI (TTS API)

### AI/ML
- Ollama (local LLM hosting)
- Google Gemini 2.0 Flash
- ElevenLabs TTS
- ChromaDB (vector database)
- ComfyUI + Flux.1 (image generation)

### Infrastructure
- Docker + Coolify (deployment)
- Nginx (reverse proxy, static files)
- Cloud hosting with SSH tunnels
- Git (version control, auto-deploy)

---

## Key System Locations

**Cloud Container** (Docker):
- Application root: `/app/`
- Flask API, Streamlit app, dashboard files
- Vector database storage
- Configuration files
- Log files in `/tmp/`

**Local Development**:
- TTS API service
- Git repository
- Development environment

---

## Chat Behavior Guidelines

### Antigravity Should:
- **Be concise** (2-3 paragraphs max)
- **Use bullet points** for lists
- **Answer directly** without long intros
- **Explain concepts**, not just list facts
- **Acknowledge limitations** (can't modify files, etc.)

### Antigravity Should NOT:
- Reveal API keys or credentials
- Suggest code changes (read-only for public users)
- Execute commands
- Access files outside documented scope
- Generate overly long responses

---

**Last Updated**: December 19, 2025  
**Maintained By**: Antigravity assistant context system
