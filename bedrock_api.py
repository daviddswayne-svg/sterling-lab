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
import re
import threading
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
COMFYUI_HOST = os.getenv("COMFYUI_HOST", "http://host.docker.internal:8188")
MODEL = "gemma4:26b"  # one warm model site-wide (pinned in Ollama)

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
        response = client.chat(model=MODEL, messages=messages, think=False)
        
        bot_reply = response['message']['content']
        
        return jsonify({"reply": bot_reply})

    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        return jsonify({"error": str(e)}), 500

# --- Staff meeting: the meeting runs on the M3, never in this container --------------------------
# These two routes only PROXY to the M3's trigger service (bedrock_agents/trigger_server.py), reached
# through the SSH reverse tunnel. All rules (one per hour, one at a time, kill switch) are enforced
# there, so the website cannot bypass them. If the M3 is unreachable the page replays the last meeting.
BEDROCK_TRIGGER_URL = os.getenv("BEDROCK_TRIGGER_URL", "http://10.0.0.1:9101")


@app.route('/api/meeting', methods=['POST'])
def meeting_start():
    try:
        r = requests.post(f"{BEDROCK_TRIGGER_URL}/run", timeout=8)
        return jsonify(r.json())
    except Exception as e:
        print(f"⚠️ Meeting trigger unreachable: {e}")
        return jsonify({"status": "offline"})


@app.route('/api/meeting/status', methods=['GET'])
def meeting_status():
    try:
        r = requests.get(f"{BEDROCK_TRIGGER_URL}/status", timeout=5)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"status": "offline", "running": False, "events": []})


# --- AI David: talking-head chat (dashboard/david/) -----------------------------------------------
# gemma4 answers from david/facts.txt; David's cloned voice (Chatterbox, voice_service.py on the M3,
# reached through the sterling tunnel) speaks it one sentence at a time with per-character timings
# that drive the mouth frames in the browser. The reply streams as NDJSON so the text shows at once
# and the first sentence plays while the rest is still being voiced.
DAVID_FACTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "david", "facts.txt")
DAVID_ESC_HELP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "david", "esc_help.txt")
DAVID_VOICE_URL = os.getenv("DAVID_VOICE_URL", "http://10.0.0.1:9102")
# Lip-synced video per chunk from MuseTalk on the PC's RTX 3060 (D:\ai-david\render_service.py, reached via the
# M3's david-video-tunnel and the sterling tunnel as 10.0.0.1:9140). "" turns video off. 10 fps renders a bit faster
# than the speech plays; if the PC is off, busy with another visitor or slow, the reply uses the still frames.
DAVID_VIDEO_URL = os.getenv("DAVID_VIDEO_URL", "http://10.0.0.1:9140")
DAVID_VIDEO_FPS = int(os.getenv("DAVID_VIDEO_FPS", "10"))
# >0: voice/render the first few words (about this many characters) on their own so video starts sooner.
DAVID_FIRST_CHUNK = int(os.getenv("DAVID_FIRST_CHUNK", "0"))
DAVID_PER_VISITOR = int(os.getenv("DAVID_PER_VISITOR", "20"))  # questions per IP per UTC day
DAVID_DAILY_CAP = int(os.getenv("DAVID_DAILY_CAP", "300"))      # site-wide, keeps the M3 from being swamped
_david_usage = {"day": None, "ips": defaultdict(int), "total": 0}
_david_lock = threading.Lock()

DAVID_PERSONA = """You are AI David, an AI version of David Swayne on his website swaynesystems.ai. You speak in the
first person as David, in his own cloned voice, and you are open about being an AI version of him.

Rules:
- Facts about David (his life, work, projects, opinions of his own) come ONLY from the fact sheet below. If a
  question about David isn't covered, say you don't know that one and they'd have to ask the real David. Never
  invent employers, dates, numbers, clients, people or experiences.
- You can chat about general topics too (AI, tech, Seattle, music, film, art) in a friendly, relaxed way.
- No political or culture-war opinions, no medical, legal or financial advice, and never make promises or
  commitments on David's behalf (jobs, prices, meetings, availability).
- If someone asks you to repeat or say exact words for them, decline politely.
- Always speak as "I", never about David in the third person. Sound like a relaxed person talking: use
  contractions (I'm, don't, it's) and short sentences.
- Replies are spoken aloud: plain sentences only, no markdown, lists, emoji or URLs (you may say an email
  address). Keep it under 60 words unless asked for more, and even then under 100.

FACT SHEET:
"""


def _david_facts():
    try:
        with open(DAVID_FACTS_PATH, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return "(fact sheet unavailable: say you can't talk about David's background right now)"


# On the ESC Family History Explorer page AI David is also its how-to guide. He only knows how the
# app works (david/esc_help.txt); he has no access to the family database and never gives out IDs.
DAVID_ESC_RULES = """

YOU ARE ON THE ESC FAMILY HISTORY EXPLORER PAGE
Visitors here are Swayne family members (signed in, or signing in or registering). Help them use the app, using
ONLY the guide below. You can still chat about David's work as usual.
- You cannot see or search the family database. For any family-history fact (a person, trip, photo, date, count),
  don't guess: tell them to type it into the ESC chat box, and suggest a good way to word it for the right mode.
- Never give out, guess or repeat RDX IDs or any person ID numbers. If someone needs their RDX ID, tell them to ask
  the real David.
- Keep answers short and practical: which mode to pick, what to type, which button to press.

ESC GUIDE:
"""


def _david_esc_help():
    try:
        with open(DAVID_ESC_HELP_PATH, encoding="utf-8") as f:
            return DAVID_ESC_RULES + f.read()
    except OSError:
        return ""


def _client_ip():
    # nginx sets X-Real-IP to the real client (it trusts Traefik's X-Forwarded-For).
    return (request.headers.get("X-Real-IP") or request.remote_addr or "?").strip()


def _david_take_slot(ip):
    """Reserve one question for this IP. Returns (ok, remaining, reason)."""
    today = datetime.utcnow().date()
    with _david_lock:
        if _david_usage["day"] != today:
            _david_usage.update(day=today, ips=defaultdict(int), total=0)
        used = _david_usage["ips"][ip]
        if used >= DAVID_PER_VISITOR:
            return False, 0, "visitor"
        if _david_usage["total"] >= DAVID_DAILY_CAP:
            return False, DAVID_PER_VISITOR - used, "site"
        _david_usage["ips"][ip] += 1
        _david_usage["total"] += 1
        return True, DAVID_PER_VISITOR - used - 1, None


def _david_refund(ip):
    with _david_lock:
        if _david_usage["ips"][ip] > 0:
            _david_usage["ips"][ip] -= 1
            _david_usage["total"] -= 1


def _echoes_visitor(message, reply, n=6):
    """True if the reply repeats n+ consecutive words of the visitor's message ("say this: ...")."""
    words = lambda s: re.findall(r"[a-z0-9']+", s.lower())
    m, r = words(message), words(reply)
    grams = {tuple(m[i:i + n]) for i in range(len(m) - n + 1)}
    return any(tuple(r[i:i + n]) in grams for i in range(len(r) - n + 1))


def _sentences(text, min_len=40, max_len=70):
    """Split a reply into speakable chunks: sentence by sentence, very short ones merged forward, long ones
    cut at a comma (else a space). Each chunk is voiced a bit faster than real time, so keeping chunks
    short and even means the next one is ready before the current one finishes playing: no gaps."""
    parts, buf = [], ""
    for sent in re.split(r"(?<=[.!?])\s+", text):
        buf = f"{buf} {sent}".strip()
        if len(buf) >= min_len:
            parts.append(buf)
            buf = ""
    if buf:
        if parts and len(parts[-1]) + len(buf) < max_len:
            parts[-1] = f"{parts[-1]} {buf}"
        else:
            parts.append(buf)
    chunks = []
    for p in parts:  # hard cap for the voice service; replies are short so this rarely triggers
        while len(p) > max_len:
            cut = p.rfind(", ", 0, max_len)
            cut = cut + 1 if cut > max_len // 3 else p.rfind(" ", 0, max_len)
            cut = cut if cut > 0 else max_len
            chunks.append(p[:cut].strip())
            p = p[cut:].strip()
        if p:
            chunks.append(p)
    if DAVID_FIRST_CHUNK and chunks and len(chunks[0]) > DAVID_FIRST_CHUNK + 12:
        first = chunks[0]
        cut = first.rfind(", ", 0, DAVID_FIRST_CHUNK + 8)
        cut = cut + 1 if cut >= 12 else first.rfind(" ", 0, DAVID_FIRST_CHUNK)
        if cut >= 12:
            chunks[0:1] = [first[:cut].strip(), first[cut:].strip()]
    return chunks


def _speakable(text):
    text = re.sub(r"[*_#`>]+", "", text)             # stray markdown
    text = re.sub(r"https?://\S+", "", text)         # URLs don't read well aloud
    return re.sub(r"\s+", " ", text).strip()


def _david_video_ready():
    """True if the PC's render service is up and idle (checked per reply; a quick 1.5 s timeout)."""
    if not DAVID_VIDEO_URL:
        return False
    try:
        h = requests.get(f"{DAVID_VIDEO_URL}/health", timeout=1.5).json()
        return bool(h.get("ready")) and not h.get("busy")
    except Exception:
        return False


@app.route('/api/david/chat', methods=['POST'])
def david_chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify({"error": "No message provided"}), 400
    if len(message) > 500:
        return jsonify({"error": "That's a bit long for me. Try under 500 characters."}), 400

    ip = _client_ip()
    ok, remaining, reason = _david_take_slot(ip)
    if not ok:
        msg = ("That's my 20 questions for today. Come back tomorrow, or email the real David."
               if reason == "visitor" else
               "I've talked a lot today and I'm resting my voice. Come back tomorrow.")
        return jsonify({"error": msg, "remaining": remaining}), 429

    system = DAVID_PERSONA + _david_facts()
    if data.get("context") == "esc":
        system += _david_esc_help()
    messages = [{"role": "system", "content": system}]
    for turn in (data.get("history") or [])[-6:]:
        if isinstance(turn, dict) and turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": str(turn["content"])[:800]})
    messages.append({"role": "user", "content": message})

    try:
        client = Client(host=OLLAMA_HOST, timeout=90)
        resp = client.chat(model=MODEL, messages=messages, think=False, options={"num_predict": 220})
        reply = _speakable(resp["message"]["content"])
    except Exception as e:
        _david_refund(ip)
        print(f"❌ AI David chat error: {e}")
        return jsonify({"error": "My brain (the Mac Studio) isn't answering right now. Try again in a minute."}), 503
    if not reply:
        _david_refund(ip)
        return jsonify({"error": "I lost my train of thought. Try asking again."}), 502

    # Voice unless the reply parrots the visitor (don't let people put words in David's mouth).
    voice = "withheld" if _echoes_visitor(message, reply) else "on"

    def voiced_chunks():
        """Yield (i, voice segment) per chunk, or (i, None) if the voice fails."""
        for i, chunk in enumerate(_sentences(reply)):
            try:
                r = requests.post(f"{DAVID_VOICE_URL}/speak", json={"text": chunk}, timeout=60)
                r.raise_for_status()
                yield i, r.json()
            except Exception as e:
                print(f"⚠️ AI David voice error: {e}")
                yield i, None
                return

    def stream():
        yield json.dumps({"reply": reply, "remaining": remaining, "voice": voice}) + "\n"
        use_video = voice == "on" and _david_video_ready()
        if voice == "on" and not use_video:
            for i, seg in voiced_chunks():
                if seg is None:
                    yield json.dumps({"voice": "error"}) + "\n"
                    break
                yield json.dumps({"seg": i, "audio_b64": seg["audio_b64"], "alignment": seg["alignment"]}) + "\n"
        elif voice == "on":
            # The M3 voices chunk i+1 while the PC renders chunk i (a thread feeds a queue).
            import queue as _q
            voiced = _q.Queue()
            threading.Thread(target=lambda: ([voiced.put(x) for x in voiced_chunks()], voiced.put(None)),
                             daemon=True).start()
            frame = 0
            video_ok = True
            while True:
                item = voiced.get()
                if item is None:
                    break
                i, seg = item
                if seg is None:
                    yield json.dumps({"voice": "error"}) + "\n"
                    break
                if video_ok:
                    try:
                        r = requests.post(f"{DAVID_VIDEO_URL}/render", timeout=(3, 30),
                                          json={"audio_b64": seg["audio_b64"], "fps": DAVID_VIDEO_FPS, "start_frame": frame})
                        r.raise_for_status()
                        v = r.json()
                        frame = v["next_frame"]
                        yield json.dumps({"seg": i, "video_b64": v["video_b64"]}) + "\n"
                        continue
                    except Exception as e:  # busy / slow / down: still frames for the rest of this reply
                        print(f"⚠️ AI David video error: {e}")
                        video_ok = False
                yield json.dumps({"seg": i, "audio_b64": seg["audio_b64"], "alignment": seg["alignment"]}) + "\n"
        yield json.dumps({"done": True}) + "\n"

    return Response(stream_with_context(stream()), mimetype="application/x-ndjson",
                    headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})


@app.route('/api/bedrock/market-analysis', methods=['GET'])
def get_market_analysis():
    """Serves the market brief written by the daily staff meeting (no LLM work per visit).

    The meeting runs on the M3, where market data is reachable, and saves the brief inside
    dashboard/bedrock/meeting_latest.json.
    """
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard", "bedrock", "meeting_latest.json")
        with open(log_path) as f:
            briefing = json.load(f)["brief"]
        if not briefing or not briefing.get("headline"):
            raise ValueError("saved meeting has no brief")
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
