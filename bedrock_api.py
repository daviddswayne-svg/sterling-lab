from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from ollama import Client

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
MODEL = "dolphin-llama3"

print(f"🚀 Bedrock API starting... Connecting to Ollama at {OLLAMA_HOST}")

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
