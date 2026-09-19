from flask import Flask, request, jsonify, stream_with_context, Response
from flask_cors import CORS
import os
import json
import time
from functools import wraps
from collections import defaultdict
from datetime import datetime, timedelta
from ollama import Client
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

# Register chat API blueprint
try:
    from chat_api import chat_bp
    app.register_blueprint(chat_bp)
    print("✅ Chat API blueprint registered successfully")
except Exception as e:
    print(f"⚠️ Failed to register chat API blueprint: {e}")

print(f"🚀 Bedrock API starting... Connecting to Ollama at {OLLAMA_HOST}")

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
