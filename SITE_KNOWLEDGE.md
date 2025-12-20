# Sterling Lab / Swayne Systems - Complete Site Knowledge Base

## Overview
**swaynesystems.ai** is a hybrid AI infrastructure platform combining cloud hosting with local AI processing. The site showcases advanced AI capabilities, RAG systems, and creative portfolio work.

---

## Site Architecture

### Frontend Structure
- **Dashboard (/)**: Main landing page with portfolio showcase
  - Built with: HTML, CSS, JavaScript
  - Features: Animated gradient background, status indicators, featured content
  - CTA buttons: "Launch Sterling Lab AI Chat" → `/lab/`, "Bedrock Insurance" → `/bedrock/`

- **Sterling Lab (/lab/)**: Primary AI chat interface  
  - Built with: Streamlit (Python web framework)
  - Real-time AI chat with document intelligence
  - RAG (Retrieval-Augmented Generation) pipeline
  - Council Mode (multi-agent AI system)

- **Bedrock Insurance (/bedrock/)**: AI agent demonstration
  - Built with: Custom HTML/CSS/JS chat interface
  - Multi-agent workflow system
  - **TTS Enabled**: Responses play with cloned voice (ElevenLabs)
  - Features orchestrated AI agents for insurance workflows

### Backend Services

**Flask API (`bedrock_api.py`) - Port 5000**
Routes:
- `/health` - Health check
- `/chat` - Bedrock agent chat
- `/api/tts` - Text-to-speech proxy to local Mac
- `/api/antigravity/status` - Admin auth check
- `/api/antigravity/chat` - Admin-only chat (IP whitelisted)
- `/api/antigravity/public/chat` - Public chat (rate-limited)

**Web Server**: Nginx on port 80
- Serves static dashboard
- Proxies `/lab/` to Streamlit (port 8501)
- Proxies `/api/` to Flask (port 5000)
- Handles SSL/TLS termination

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

**Script**: `sterling_tunnel.sh`  
**Tunnel**: `autossh` keeps connection alive  
**Ports Forwarded**:
- `11434` (Ollama) - Mac → Cloud
- `8001` (TTS API) - Mac port 8000 → Cloud port 8001  
  (Port 8001 used to avoid conflict with Coolify on 8000)

**Connection**: `root@165.22.146.182`  
**Key**: `~/.ssh/sterling_tunnel`

---

## Deployment Pipeline

### Git Strategy (Dual Remotes)
1. **Live Server**: `root@165.22.146.182:/var/www/swaynesystems.ai.git`
   - Bare repo on DigitalOcean droplet
   - Coolify watches this repo

2. **GitHub Backup**: `github.com/daviddswayne-svg/sterling-lab.git`
   - Public backup/portfolio
   - Synced automatically via `deploy.sh`

### Deployment Script (`deploy.sh`)
```bash
git push live main    # Triggers Coolify rebuild
git push origin main  # Syncs to GitHub
```

**Coolify**: Auto-deploys on git push
- Builds Docker container
- Runs `start.sh` → starts Flask, Streamlit, Nginx
- Typically takes 30-60 seconds to rebuild

---

##

 Docker Environment

**Container Network**: Coolify bridge (`10.0.1.1` Gateway IP)  
**Why not `172.17.0.1`**:  
- Standard Docker uses `172.17.0.1`
- Coolify uses custom bridge with `10.0.1.1`
- Code explicitly uses `10.0.1.1` for TTS proxy

**Container Services**:
1. Flask API (port 5000)
2. Streamlit (port 8501)
3. Nginx (port 80)

**Startup Sequence** (`start.sh`):
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
**Admin Access**: IP whitelist
- Allowed IPs in `ANTIGRAVITY_ALLOWED_IPS` env var
- Default: `71.197.228.171`
- Admin button only visible to whitelisted IPs

**Public Access**: Rate limiting
- 20 messages/hour per IP
- Sliding window (1 hour)
- 429 error when exceeded

### Secrets Management
- `AUTH_SECRET` (not currently used in auth flow)
- `GEMINI_API_KEY` for Google AI
- `ELEVENLABS_API_KEY` in local `elevenlabs_api.py`

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
- DigitalOcean (cloud hosting)
- SSH tunnels (local AI access)
- Git (version control, auto-deploy)

---

## Environment Variables (Production)

```bash
OLLAMA_HOST=http://10.0.0.1:11434  # Docker gateway to tunnel
GEMINI_API_KEY=<secret>
ANTIGRAVITY_ALLOWED_IPS=71.197.228.171
ANTIGRAVITY_ENABLED=true
PUBLIC_CHAT_ENABLED=true
PUBLIC_CHAT_RATE_LIMIT=20
```

---

## File Locations (Key Paths)

**Cloud Container**:
- `/app/bedrock_api.py` - Flask API
- `/app/chat_app.py` - Streamlit app
- `/app/dashboard/` - Static site files
- `/app/dashboard/bedrock/` - Bedrock chat UI
- `/app/chroma_db/` - Vector database
- `/app/nginx.conf` - Web server config
- `/tmp/bedrock_api.log` - Flask logs
- `/tmp/streamlit.log` - Streamlit logs

**Local Mac Studio**:
- `/Users/daviddswayne/.gemini/antigravity/scratch/f5-tts-mlx/elevenlabs_api.py`
- `/Users/daviddswayne/.gemini/antigravity/scratch/sterling_lab/` - Main repo

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
