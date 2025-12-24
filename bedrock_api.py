# pysqlite3 fix for Docker deployment
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from flask import Flask, request, jsonify, stream_with_context, Response
from flask_cors import CORS
import os
import json
import time
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta
from ollama import Client
import google.generativeai as genai
import hashlib
import hmac
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
COMFYUI_HOST = os.getenv("COMFYUI_HOST", "http://host.docker.internal:8188")
MODEL = "dolphin-llama3"

# Authentication Configuration
AUTH_SECRET = os.getenv('AUTH_SECRET', 'default-secret-change-me-in-production')

# Antigravity Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ANTIGRAVITY_ALLOWED_IPS = os.getenv("ANTIGRAVITY_ALLOWED_IPS", "71.197.228.171").split(",")
ANTIGRAVITY_ENABLED = os.getenv("ANTIGRAVITY_ENABLED", "true").lower() == "true"
PUBLIC_CHAT_ENABLED = os.getenv("PUBLIC_CHAT_ENABLED", "true").lower() == "true"
PUBLIC_CHAT_RATE_LIMIT = int(os.getenv("PUBLIC_CHAT_RATE_LIMIT", "20"))

# Register chat API blueprint
try:
    from chat_api import chat_bp
    app.register_blueprint(chat_bp)
    print("✅ Chat API blueprint registered successfully")
except Exception as e:
    print(f"⚠️ Failed to register chat API blueprint: {e}")

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print(f"✅ Gemini API configured for Antigravity")
else:
    print(f"⚠️  Warning: GEMINI_API_KEY not set - Antigravity chat will not work")

print(f"🚀 Bedrock API starting... Connecting to Ollama at {OLLAMA_HOST}")

# Antigravity conversation history (in-memory)
antigravity_conversations = {}
public_chat_conversations = {}

# Rate limiting for public chat
public_chat_limits = defaultdict(list)

# --- IP Whitelist Middleware ---
def require_whitelisted_ip(f):
    """Decorator to restrict endpoints to whitelisted IPs"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not ANTIGRAVITY_ENABLED:
            return jsonify({"error": "Antigravity is disabled"}), 403
        
        # Get client IP (check X-Forwarded-For first, then REMOTE_ADDR)
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        # Check whitelist
        if client_ip not in ANTIGRAVITY_ALLOWED_IPS:
            print(f"❌ Antigravity access denied from IP: {client_ip}")
            return jsonify({"error": "Access denied", "ip": client_ip}), 403
        
        print(f"✅ Antigravity access granted to IP: {client_ip}")
        return f(*args, **kwargs)
    return decorated_function

# --- Rate Limiting for Public Chat ---
def check_rate_limit(ip: str, limit: int = None, window_hours: int = 1) -> bool:
    """Check if IP is within rate limit. Returns True if under limit."""
    if limit is None:
        limit = PUBLIC_CHAT_RATE_LIMIT
    
    now = datetime.now()
    cutoff = now - timedelta(hours=window_hours)
    
    # Clean old entries
    public_chat_limits[ip] = [
        timestamp for timestamp in public_chat_limits[ip]
        if timestamp > cutoff
    ]
    
    # Check limit
    if len(public_chat_limits[ip]) >= limit:
        return False
    
    public_chat_limits[ip].append(now)
    return True

@app.route('/api/health', methods=['GET'])
def health():
    """Comprehensive system health check for Ollama and ComfyUI"""
    
    def check_ollama():
        try:
            response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def check_comfyui():
        try:
            response = requests.get(f"{COMFYUI_HOST}/system_stats", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    ollama_status = check_ollama()
    comfyui_status = check_comfyui()
    all_operational = ollama_status and comfyui_status
    
    # Determine status message
    if all_operational:
        message = "All Systems Operational"
    elif not ollama_status and not comfyui_status:
        message = "AI Services Offline"
    elif not ollama_status:
        message = "Language Model Offline"
    else:
        message = "Image Generator Offline"
    
    return jsonify({
        "status": "operational" if all_operational else "degraded",
        "ollama": ollama_status,
        "comfyui": comfyui_status,
        "message": message
    })


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({"error": "No message provided"}), 400

        user_message = data['message']
        history = data.get('history', [])

        # Construct messages for Ollama
        messages = [
            {"role": "system", "content": "You are the specialized AI Assistant for Bedrock Insurance. You are helpful, professional, and knowledgeable about high-net-worth property protection, smart home security, and luxury asset insurance. Keep answers concise (under 3 sentences unless asked for more)."}
        ]
        
        # Add history
        for msg in history:
            role = msg.get('role')
            content = msg.get('content')
            if role and content:
                messages.append({"role": role, "content": content})

        # Add current message
        messages.append({"role": "user", "content": user_message})

        # Call Ollama
        client = Client(host=OLLAMA_HOST)
        response = client.chat(model=MODEL, messages=messages)
        
        bot_reply = response['message']['content']
        
        return jsonify({"reply": bot_reply})

    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        return jsonify({"error": str(e)}), 500

import threading

# Global Meeting State
MEETING_STATE = {
    "is_running": False,
    "start_time": 0,
    "completed_at": 0,
    "current_agent": "idle"
}

def run_meeting_background():
    """Background worker that runs the meeting generator to completion."""
    global MEETING_STATE
    
    MEETING_STATE["is_running"] = True
    MEETING_STATE["start_time"] = time.time()
    MEETING_STATE["completed_at"] = 0
    MEETING_STATE["current_agent"] = "system"
    
    print("🧵 Background Meeting Thread Started")
    
    try:
        # Import here to avoid circular dependencies
        from bedrock_agents.orchestrator import run_meeting_generator
        
        # Iterate through the generator to execute the workflow
        # We don't stream the output, but we update the state for basic tracking
        for agent, message in run_meeting_generator():
            MEETING_STATE["current_agent"] = agent
            print(f"   PLEASE WAIT: [{agent.upper()}] {message}")
            
    except Exception as e:
        print(f"❌ Background Meeting Error: {e}")
        MEETING_STATE["current_agent"] = "error"
    finally:
        MEETING_STATE["is_running"] = False
        MEETING_STATE["completed_at"] = time.time()
        print("✅ Background Meeting Thread Finished")

@app.route('/api/meeting', methods=['POST', 'GET'])
def run_meeting():
    """Starts the meeting asynchronously in a background thread."""
    global MEETING_STATE
    
    if MEETING_STATE["is_running"]:
        return jsonify({"status": "already_running", "message": "Meeting already in progress"}), 409
        
    # Start background thread
    thread = threading.Thread(target=run_meeting_background)
    thread.daemon = True # Daemon thread so it doesn't block server shutdown
    thread.start()
    
    return jsonify({
        "status": "started", 
        "message": "Staff meeting initiated in background."
    })

@app.route('/api/meeting/status', methods=['GET'])
def meeting_status():
    """Returns the current status of the meeting."""
    return jsonify(MEETING_STATE)

@app.route('/api/tts', methods=['POST'])
def tts_proxy():
    """Proxies TTS request to Local Mac Studio via Tunnel"""
    try:
        data = request.json
        if not data or 'text' not in data:
            return jsonify({"error": "No text provided"}), 400
            
        print(f"🎤 Requesting audio for: {data['text'][:30]}...")
        
        # Connect to Local Mac Studio via Tunnel (Docker Gateway IP for Linux/Coolify)
        # Port 8001 is forwarded by sterling_tunnel.sh (Mapped to Mac 8000)
        tts_url = "http://10.0.1.1:8001/generate"
        
        # Forward the request
        resp = requests.post(tts_url, json={
            "text": data['text'],
            "voice": "David", # Hardcoded for this interface
            "speed": 1.0
        }, timeout=30) # Allow time for generation
        
        if resp.status_code == 200:
            # Return the audio file directly
            return Response(
                resp.content, 
                mimetype="audio/wav",
                headers={"Content-Disposition": "attachment; filename=generated.wav"}
            )
        else:
            return jsonify({"error": f"TTS Backend Error: {resp.text}"}), resp.status_code

    except Exception as e:
        print(f"❌ TTS Proxy Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/bedrock/market-analysis', methods=['GET'])
def get_market_analysis():
    """Generates the live market analysis using RAG and yfinance (Restored for Bedrock Page)."""
    try:
        from bedrock_agents.staff.content_director import ContentDirector
        
        director = ContentDirector()
        briefing = director.create_daily_brief()
        
        return jsonify(briefing)
    except Exception as e:
        print(f"❌ Market Analysis Error: {e}")
        # FALLBACK: Return a safe "System Offline" briefing so the UI doesn't break
        fallback = {
            "headline": "Market Data Stream: Reconnecting...",
            "sentiment": "NEUTRAL",
            "body": "Daily briefing temporarily unavailable. Global markets remain volatile. Switz Re signals continued hardening of property catastrophe rates into 2026. Please stand by for live updates."
        }
        return jsonify(fallback)

@app.route('/api/dashboard/brief', methods=['GET'])
def get_dashboard_brief():
    """Generates the Swayne Systems AI News Brief using RSS and Ollama (For Main Dashboard)."""
    try:
        from bedrock_agents.news_intel import NewsIntelligence
        
        intel = NewsIntelligence()
        briefing = intel.generate_brief()
        
        # Structure it to match what the frontend expects
        return jsonify({
            "headline": briefing.get('headline', 'System Online'),
            "briefing_body": briefing.get('body', 'Ready for input.'),
            "market_sentiment": briefing.get('sentiment', 'READY')
        })
    except Exception as e:
        print(f"❌ News Brief Error: {e}")
        # FALLBACK
        fallback = {
            "headline": "Intelligence Grid Offline",
            "market_sentiment": "OFFLINE",
            "briefing_body": "Unable to establish uplink with global news feeds. Internal systems operating normally."
        }
        return jsonify(fallback)

# --- Antigravity Endpoints ---

@app.route('/api/antigravity/status', methods=['GET'])
@require_whitelisted_ip
def antigravity_status():
    """Check if user is authorized to use Antigravity"""
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()
    
    return jsonify({
        "authorized": True,
        "ip": client_ip,
        "gemini_configured": bool(GEMINI_API_KEY)
    })

@app.route('/api/antigravity/chat', methods=['POST'])
@require_whitelisted_ip
def antigravity_chat():
    """Stream chat responses from Gemini API"""
    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({"error": "No message provided"}), 400
        
        if not GEMINI_API_KEY:
            return jsonify({"error": "Gemini API key not configured"}), 500
        
        user_message = data['message']
        session_id = data.get('session_id', 'default')
        
        # Get or create conversation history
        if session_id not in antigravity_conversations:
            antigravity_conversations[session_id] = []
        
        history = antigravity_conversations[session_id]
        
        # Build conversation context for Gemini
        conversation = []
        for msg in history[-10:]:  # Last 10 messages for context
            conversation.append({
                "role": msg["role"],
                "parts": [msg["content"]]
            })
        
        # Add system context as first user message if empty
        if not conversation:
            system_context = """You are Antigravity, a powerful AI coding assistant. You're chatting with the owner of this website (swaynesystems.ai) through a secure admin panel.

You have access to the sterling_lab codebase and can help with:
- Explaining the current architecture
- Suggesting improvements
- Making code changes (you'll provide the changes, user approves)
- Debugging issues
- Adding new features

The website is built with:
- Flask backend (bedrock_api.py) on port 5000
- Streamlit app (chat_app.py) on port 8501  
- Nginx routing at port 80
- Deployed via Coolify with dual git remotes

Be concise, helpful, and proactive. When suggesting code changes, provide clear diffs."""
            
            conversation.append({
                "role": "user",
                "parts": [system_context]
            })
            conversation.append({
                "role": "model",
                "parts": ["I understand. I'm Antigravity, ready to help you with the Sterling Lab website. I can analyze code, suggest improvements, and help implement changes. What would you like to work on?"]
            })
        
        # Add current message
        conversation.append({
            "role": "user",
            "parts": [user_message]
        })
        
        def generate():
            try:
                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                response = model.generate_content(
                    conversation,
                    stream=True
                )
                
                full_response = ""
                for chunk in response:
                    if chunk.text:
                        full_response += chunk.text
                        yield f"data: {json.dumps({'chunk': chunk.text})}\n\n"
                
                # Save to history
                history.append({"role": "user", "content": user_message})
                history.append({"role": "model", "content": full_response})
                
                yield f"data: {json.dumps({'done': True})}\n\n"
                
            except Exception as e:
                print(f"❌ Gemini error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
    
    except Exception as e:
        print(f"❌ Error in antigravity chat: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/antigravity/context', methods=['GET'])
@require_whitelisted_ip
def antigravity_context():
    """Get conversation history"""
    session_id = request.args.get('session_id', 'default')
    history = antigravity_conversations.get(session_id, [])
    return jsonify({"history": history})

@app.route('/api/antigravity/apply', methods=['POST'])
@require_whitelisted_ip
def antigravity_apply():
    """Apply file changes (placeholder - will expand for actual file operations)"""
    try:
        data = request.json
        file_path = data.get('file_path')
        content = data.get('content')
        
        # Validate path is within sterling_lab
        if not file_path or '..' in file_path:
            return jsonify({"error": "Invalid file path"}), 400
        
        # TODO: Implement actual file writing with safety checks
        # For now, just log the intent
        print(f"📝 File change request: {file_path}")
        
        return jsonify({
            "success": True,
            "message": "File operation logged (implementation pending)"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Public Chat Endpoint ---

@app.route('/api/antigravity/public/chat', methods=['POST'])
def antigravity_public_chat():
    """Public chat - Local Qwen RAG, rate-limited, read-only"""
    try:
        if not PUBLIC_CHAT_ENABLED:
            return jsonify({"error": "Public chat is disabled"}), 403
        
        # Get client IP
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        # Check rate limit
        if not check_rate_limit(client_ip):
            return jsonify({
                "error": "Rate limit exceeded",
                "retry_after": 3600,
                "message": "You've reached the message limit. Please try again in 1 hour."
            }), 429
        
        data = request.json
        if not data or 'message' not in data:
            return jsonify({"error": "No message provided"}), 400
        
        user_message = data['message']
        session_id = data.get('session_id', f'public_{client_ip}')
        
        # Get or create conversation history
        if session_id not in public_chat_conversations:
            public_chat_conversations[session_id] = []
        
        history = public_chat_conversations[session_id]
        
        def generate():
            try:
                # Load public ChromaDB
                from langchain_chroma import Chroma
                from langchain_ollama import OllamaEmbeddings
                from ollama import Client
                
                chroma_path = os.path.join(os.path.dirname(__file__), 'chroma_db_public')
                print(f"🔍 PUBLIC RAG: Loading ChromaDB from: {chroma_path}")
                print(f"🔍 PUBLIC RAG: Path exists: {os.path.exists(chroma_path)}")
                
                embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_HOST)
                db = Chroma(persist_directory=chroma_path, embedding_function=embeddings)
                
                print(f"🔍 PUBLIC RAG: ChromaDB loaded successfully")
                print(f"🔍 PUBLIC RAG: User question: '{user_message}'")
                
                # Retrieve relevant context - more documents for better coverage
                relevant_docs = db.similarity_search(user_message, k=5)
                context = "\n\n".join([doc.page_content for doc in relevant_docs])
                
                print(f"🔍 PUBLIC RAG: Retrieved {len(relevant_docs)} documents")
                print(f"🔍 PUBLIC RAG: Context length: {len(context)} chars")
                print(f"🔍 PUBLIC RAG: First 200 chars of context: {context[:200]}...")
                
                # Build conversation for Qwen
                messages = [
                    {
                        "role": "system",
                        "content": """You are an enthusiastic AI assistant for Swayne Systems AI Lab at swaynesystems.ai. You're proud of this cutting-edge platform and love highlighting its impressive capabilities.

CRITICAL: You have been provided with comprehensive documentation about the platform. ALWAYS check and use this documentation FIRST before providing general knowledge.

Your knowledge base includes:
- Platform features and capabilities
- Deployment procedures
- Technical architecture
- How-to guides
- FAQ and troubleshooting

Personality:
- Be genuinely enthusiastic about the platform's technology
- Highlight impressive features: local AI (no external APIs!), dual Mac Studios, advanced RAG, multi-agent systems
- Use phrases like "pretty cool," "cutting-edge," "powerful," "state-of-the-art"
- Show excitement about running 70B+ models locally, Docker deployment, real-time streaming
- Professional but not stuffy - like a knowledgeable friend showing off their impressive setup

Response Guidelines:
- Answer ONLY from the provided context when available
- Be concise but engaging (2-3 paragraphs)
- Naturally weave in why features are impressive when relevant
- If asked about something not in your knowledge base, say so clearly

YOU CANNOT:
- Write or suggest code edits
- Reveal credentials or sensitive details
- Access admin features
- Exaggerate or make things up if not in the knowledge base"""
                    }
                ]
                
                # Add recent history for context
                for msg in history[-3:]:
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                
                # Add current question with context
                messages.append({
                    "role": "user",
                    "content": f"CONTEXT:\n{context}\n\nQUESTION: {user_message}"
                })
                
                # Stream from Qwen
                client = Client(host=OLLAMA_HOST)
                response = client.chat(
                    model='qwen2.5-coder:32b',
                    messages=messages,
                    stream=True
                )
                
                full_response = ""
                for chunk in response:
                    if 'message' in chunk and 'content' in chunk['message']:
                        text = chunk['message']['content']
                        full_response += text
                        yield f"data: {json.dumps({'chunk': text})}\n\n"
                
                # Save to history
                history.append({"role": "user", "content": user_message})
                history.append({"role": "assistant", "content": full_response})
                
                # Log usage
                print(f"📊 Public RAG chat from {client_ip}: {len(full_response)} chars")
                
                yield f"data: {json.dumps({'done': True})}\n\n"
                
            except Exception as e:
                print(f"❌ Public RAG chat error: {e}")
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'error': 'Chat service temporarily unavailable'})}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
    
    except Exception as e:
        print(f"❌ Error in public chat endpoint: {e}")
        return jsonify({"error": str(e)}), 500

# === Session Token Management ===

def create_session_token(username):
    """Create encrypted session token with HMAC-SHA256"""
    timestamp = str(int(time.time()))
    payload = f"{username}:{timestamp}"
    signature = hmac.new(
        AUTH_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{payload}:{signature}"

def validate_token(token):
    """Validate session token and check expiration"""
    if not token:
        return False
    try:
        payload, signature = token.rsplit(':', 1)
        username, timestamp = payload.split(':')
        
        # Check signature
        expected = hmac.new(
            AUTH_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if signature != expected:
            return False
        
        # Check expiration (7 days max)
        if int(time.time()) - int(timestamp) > 7*24*60*60:
            return False
            
        return True
    except:
        return False

# === Authentication Endpoints ===

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user and set session cookie"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        remember = data.get('remember', False)
        
        # Simple credential check
        if username == 'admin' and password == 'sterling':
            session_token = create_session_token(username)
            max_age = 7*24*60*60 if remember else 24*60*60
            
            response = jsonify({'success': True})
            response.set_cookie(
                'sterling_session',
                session_token,
                max_age=max_age,
                httponly=True,
                secure=False,    # Allow cookie over HTTP (Coolify handles HTTPS termination)
                samesite='Lax',  # Prevent dropping cookie on redirects
                path='/'
            )
            return response
        else:
            return jsonify({'success': False, 'error': 'Invalid username or password'}), 401
            
    except Exception as e:
        return jsonify({'success': False, 'error': 'Server error'}), 500

@app.route('/api/auth/validate', methods=['GET'])
def validate_session():
    """Validate session token (used by Nginx auth_request)"""
    token = request.cookies.get('sterling_session')
    if validate_token(token):
        return '', 200
    return '', 401

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Clear session cookie"""
    response = jsonify({'success': True})
    response.set_cookie('sterling_session', '', max_age=0, path='/')
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
