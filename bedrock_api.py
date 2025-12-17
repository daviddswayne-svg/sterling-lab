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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
