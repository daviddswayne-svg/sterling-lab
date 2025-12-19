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

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
MODEL = "dolphin-llama3"

# Authentication Configuration
AUTH_SECRET = os.getenv('AUTH_SECRET', 'default-secret-change-me-in-production')

# Antigravity Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ANTIGRAVITY_ALLOWED_IPS = os.getenv("ANTIGRAVITY_ALLOWED_IPS", "71.197.228.171").split(",")
ANTIGRAVITY_ENABLED = os.getenv("ANTIGRAVITY_ENABLED", "true").lower() == "true"
PUBLIC_CHAT_ENABLED = os.getenv("PUBLIC_CHAT_ENABLED", "true").lower() == "true"
PUBLIC_CHAT_RATE_LIMIT = int(os.getenv("PUBLIC_CHAT_RATE_LIMIT", "20"))

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

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "model": MODEL})

@app.route('/chat', methods=['POST'])
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

@app.route('/meeting', methods=['GET'])
def run_meeting():
    def generate():
        try:
            # Import here to avoid circular dependencies if any
            from bedrock_agents.orchestrator import run_meeting_generator
            import json
            import time
            
            # Initial Connection Message
            yield f"data: {json.dumps({'agent': 'system', 'message': 'Connection Stable. Agents convening...'})}\n\n"
            
            # Use a generator that we can pulse
            meeting = run_meeting_generator()
            
            while True:
                try:
                    agent, message = next(meeting)
                    data = json.dumps({"agent": agent, "message": message})
                    yield f"data: {data}\n\n"
                except StopIteration:
                    break
        except Exception as e:
            yield f"data: {{\"agent\": \"error\", \"message\": \"{str(e)}\"}}\n\n"

    return Response(
        stream_with_context(generate()), 
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Transfer-Encoding': 'chunked',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no' # Tell Nginx specifically
        }
    )

@app.route('/api/tts', methods=['POST'])
def tts_proxy():
    """Proxies TTS request to Local Mac Studio via Tunnel"""
    try:
        data = request.json
        if not data or 'text' not in data:
            return jsonify({"error": "No text provided"}), 400
            
        print(f"🎤 Requesting audio for: {data['text'][:30]}...")
        
        # Connect to Local Mac Studio via Tunnel (host.docker.internal)
        # Port 8000 is forwarded by sterling_tunnel.sh
        tts_url = "http://host.docker.internal:8000/generate"
        
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

# --- Antigravity Endpoints ---

@app.route('/antigravity/status', methods=['GET'])
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

@app.route('/antigravity/chat', methods=['POST'])
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

@app.route('/antigravity/context', methods=['GET'])
@require_whitelisted_ip
def antigravity_context():
    """Get conversation history"""
    session_id = request.args.get('session_id', 'default')
    history = antigravity_conversations.get(session_id, [])
    return jsonify({"history": history})

@app.route('/antigravity/apply', methods=['POST'])
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

@app.route('/antigravity/public/chat', methods=['POST'])
def antigravity_public_chat():
    """Public chat - read-only, rate-limited, no code access"""
    try:
        if not PUBLIC_CHAT_ENABLED:
            return jsonify({"error": "Public chat is disabled"}), 403
        
        if not GEMINI_API_KEY:
            return jsonify({"error": "Chat service unavailable"}), 500
        
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
        
        # Build conversation context for Gemini
        conversation = []
        for msg in history[-5:]:  # Shorter context for public (5 vs 10)
            conversation.append({
                "role": msg["role"],
                "parts": [msg["content"]]
            })
        
        # Add public system context
        if not conversation:
            system_context = """You are Antigravity, an AI assistant for Sterling Lab at swaynesystems.ai.

WHAT YOU KNOW ABOUT STERLING LAB:

**Technology Stack:**
- Backend: Flask API (bedrock_api.py) running on port 5000
- Frontend: Streamlit app (chat_app.py) running on port 8501
- Web Server: Nginx on port 80 routing traffic
- Deployment: Docker containers via Coolify on DigitalOcean
- Version Control: Dual git remotes (GitHub backup + live server deployment)

**AI Models & Services:**
- Primary LLM: Ollama running on Mac Studio M3 Ultra via SSH tunnel
  - Models: llama3.3:70b, qwen2.5-coder:32b, dolphin-llama3
- Embeddings: nomic-embed-text (for RAG)
- This Chat: Gemini 2.0 Flash (Google AI)
- Vector Database: ChromaDB for document storage
- Chat History: SQLite database

**Key Features:**
- RAG Pipeline: Retrieval-Augmented Generation using ChromaDB
- Council Mode: Multi-agent AI system with specialized personas
- Real-time Streaming: Live AI responses with token counting
- Distributed Architecture: Remote AI processing via SSH tunnel
- Document Intelligence: Ingests estate documents for Q&A

**Architecture:**
- Static dashboard at / (this page)
- Streamlit interface at /lab (main chat app)
- Flask API at /api/ for various services
- Bedrock Insurance demo at /bedrock/

**Bedrock Agents System:**
- Multi-agent framework with specialized AI roles
- Agents: Content Director, Web Developer, Photo Designer, Publishing Manager
- Uses orchestrator pattern for coordinated workflows
- Integrated with ComfyUI for image generation

**What Makes Sterling Lab Special:**
- Hybrid deployment (cloud frontend + local AI backend)
- Estate intelligence focus (document analysis, asset management)
- Real-time model switching and streaming
- Privacy-focused (data stays local on Mac Studio)

YOU CAN:
- Explain the architecture and how components work
- Discuss the LLMs, models, and AI stack in detail
- Answer technical questions about implementation
- Describe features and capabilities
- Explain the RAG pipeline and document processing
- Discuss deployment and infrastructure

YOU CANNOT:
- Make code changes or suggest edits
- Reveal API keys, passwords, or credentials
- Execute commands or file operations
- Access admin-only features
- Modify any files or configurations

Keep responses informative but concise. If someone asks about specific code, explain what it does conceptually without revealing sensitive implementation details like API keys."""
            
            conversation.append({
                "role": "user",
                "parts": [system_context]
            })
            conversation.append({
                "role": "model",
                "parts": ["Hi! I'm Antigravity, the AI assistant for Sterling Lab. I can answer detailed questions about our AI technology stack, the models we use, our architecture, and how everything works. What would you like to know?"]
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
                
                # Log public chat usage
                print(f"📊 Public chat from {client_ip}: {len(full_response)} chars")
                
                yield f"data: {json.dumps({'done': True})}\n\n"
                
            except Exception as e:
                print(f"❌ Public chat error: {e}")
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
        print(f"❌ Error in public chat: {e}")
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
