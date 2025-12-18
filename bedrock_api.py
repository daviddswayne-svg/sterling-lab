from flask import Flask, request, jsonify, stream_with_context, Response
from flask_cors import CORS
import os
import json
import time
from functools import wraps
from ollama import Client
import google.generativeai as genai

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
MODEL = "dolphin-llama3"

# Antigravity Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
ANTIGRAVITY_ALLOWED_IPS = os.getenv("ANTIGRAVITY_ALLOWED_IPS", "71.197.228.171").split(",")
ANTIGRAVITY_ENABLED = os.getenv("ANTIGRAVITY_ENABLED", "true").lower() == "true"

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print(f"✅ Gemini API configured for Antigravity")
else:
    print(f"⚠️  Warning: GEMINI_API_KEY not set - Antigravity chat will not work")

print(f"🚀 Bedrock API starting... Connecting to Ollama at {OLLAMA_HOST}")

# Antigravity conversation history (in-memory)
antigravity_conversations = {}

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

    from flask import stream_with_context, Response
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
