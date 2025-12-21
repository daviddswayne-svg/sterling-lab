"""
Bedrock Insurance Advisor Chat API
Handles customer verification, AI chat, and policy retrieval
"""

import json
import os
from flask import Blueprint, request, jsonify
import ollama

# Load mock customer data
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CUSTOMERS_FILE = os.path.join(DATA_DIR, "data", "mock_customers.json")

with open(CUSTOMERS_FILE, 'r') as f:
    CUSTOMER_DB = json.load(f)['customers']

# Create Blueprint
chat_bp = Blueprint('chat', __name__)

# Ollama client
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
ollama_client = ollama.Client(host=OLLAMA_HOST)


@chat_bp.route('/api/insurance/verify', methods=['POST'])
def verify_identity():
    """Verify customer identity and return customer data"""
    data = request.json
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    policy_number = data.get('policyNumber', '').strip()
    
    # Search for customer
    customer = None
    
    # Try by name and phone
    if name and phone:
        for c in CUSTOMER_DB:
            if c['name'].lower() == name.lower() and c['phone'] == phone:
                customer = c
                break
    
    # Try by policy number
    if not customer and policy_number:
        for c in CUSTOMER_DB:
            for policy in c['policies']:
                if policy['number'] == policy_number:
                    customer = c
                    break
            if customer:
                break
    
    if customer:
        return jsonify({
            'success': True,
            'customer': customer
        })
    else:
        return jsonify({
            'success': False,
            'message': 'We could not verify your identity. Please check your information and try again.'
        }), 404


@chat_bp.route('/api/insurance/chat', methods=['POST'])
def chat():
    """Handle AI chat with customer context"""
    data = request.json
    message = data.get('message', '')
    customer_id = data.get('customer_id', '')
    
    # Find customer
    customer = next((c for c in CUSTOMER_DB if c['id'] == customer_id), None)
    
    if not customer:
        return jsonify({'response': "I'm sorry, I couldn't find your account information."}), 400
    
    # Build context for AI
    context = build_customer_context(customer)
    
    # Create AI prompt with context
    system_prompt = f"""You are a helpful and professional insurance advisor for Bedrock Insurance. 

CUSTOMER CONTEXT:
{context}

Guidelines:
- Be friendly, professional, and empathetic
- Reference their specific policies when relevant
- Provide accurate information based on their coverage
- If they ask about filing a claim, guide them through the process
- If you don't know something, admit it and offer to connect them with a specialist
- Keep responses concise (2-3 paragraphs max)

Customer question: {message}"""
    
    try:
        response = ollama_client.chat(
            model='qwen',  # Fast 2.3GB model for quick chat responses
            messages=[
                {'role': 'system', 'content': 'You are a professional insurance advisor at Bedrock Insurance.'},
                {'role': 'user', 'content': system_prompt}
            ]
        )
        
        ai_response = response['message']['content']
        
        return jsonify({
            'response': ai_response
        })
        
    except Exception as e:
        print(f"Error in chat: {e}")
        return jsonify({
            'response': "I apologize, but I'm experiencing technical difficulties. Please try again or contact our support team."
        }), 500


def build_customer_context(customer):
    """Build formatted context string for AI"""
    context = f"Customer Name: {customer['name']}\n"
    context += f"Email: {customer['email']}\n\n"
    
    context += "ACTIVE POLICIES:\n"
    for policy in customer['policies']:
        context += f"\n{policy['type'].upper()} Insurance - {policy['number']}\n"
        context += f"  Coverage: {policy['coverage']}\n"
        context += f"  Premium: {policy['premium']}\n"
        context += f"  Deductible: {policy['deductible']}\n"
        context += f"  Status: {policy['status']}\n"
        
        if policy['type'] == 'home':
            context += f"  Address: {policy['address']}\n"
        elif policy['type'] == 'auto':
            context += f"  Vehicle: {policy['vehicle']}\n"
        
        context += f"  Features: {', '.join(policy['features'])}\n"
        context += f"  Renewal: {policy['renewal_date']}\n"
    
    if customer['claims']:
        context += "\n\nRECENT CLAIMS:\n"
        for claim in customer['claims']:
            context += f"\nClaim #{claim['number']} ({claim['type']})\n"
            context += f"  Date: {claim['date']}\n"
            context += f"  Status: {claim['status']}\n"
            context += f"  Amount: {claim['amount']}\n"
            context += f"  Description: {claim['description']}\n"
    
    return context


@chat_bp.route('/api/insurance/policies/<customer_id>', methods=['GET'])
def get_policies(customer_id):
    """Get all policies for a customer"""
    customer = next((c for c in CUSTOMER_DB if c['id'] == customer_id), None)
    
    if customer:
        return jsonify({
            'success': True,
            'policies': customer['policies']
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Customer not found'
        }), 404


@chat_bp.route('/api/insurance/claims/submit', methods=['POST'])
def submit_claim():
    """Submit a new claim (POC - just returns success)"""
    data = request.json
    
    # In production, this would create an actual claim record
    return jsonify({
        'success': True,
        'message': 'Claim submitted successfully. A claims adjuster will contact you within 24 hours.',
        'claim_number': f"CLM-2025-{os.urandom(3).hex().upper()}"
    })
