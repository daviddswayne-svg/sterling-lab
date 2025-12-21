// Bedrock Insurance Advisor Chat
let currentCustomer = null;
let chatEventSource = null;

// Open chat modal
function openInsuranceChat() {
    document.getElementById('insuranceChatModal').classList.add('active');
    document.getElementById('insuranceVerifyStep').classList.add('active');
    document.getElementById('insuranceChatStep').classList.remove('active');
}

// Close chat modal
function closeInsuranceChat() {
    document.getElementById('insuranceChatModal').classList.remove('active');
    document.getElementById('insuranceVerifyStep').classList.remove('active');
    document.getElementById('insuranceChatStep').classList.remove('active');

    // Close SSE connection if open
    if (chatEventSource) {
        chatEventSource.close();
        chatEventSource = null;
    }

    // Reset state
    currentCustomer = null;
    document.getElementById('chatMessages').innerHTML = '';
    document.getElementById('verifyForm').reset();
}

// Verify customer identity
async function verifyIdentity(event) {
    event.preventDefault();

    const name = document.getElementById('customerName').value.trim();
    const phone = document.getElementById('customerPhone').value.trim();
    const policyNumber = document.getElementById('policyNumber').value.trim();

    // Hide previous errors
    document.getElementById('verifyError').style.display = 'none';

    try {
        const response = await fetch('/api/insurance/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, phone, policyNumber })
        });

        const data = await response.json();

        if (data.success) {
            currentCustomer = data.customer;
            showChatInterface();
        } else {
            showError(data.message || 'Unable to verify identity. Please check your information.');
        }
    } catch (error) {
        showError('Connection error. Please try again.');
    }
}

function showError(message) {
    const errorDiv = document.getElementById('verifyError');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

// Show chat interface after successful verification
function showChatInterface() {
    document.getElementById('insuranceVerifyStep').classList.remove('active');
    document.getElementById('insuranceChatStep').classList.add('active');

    // Show welcome message
    const welcomeDiv = document.getElementById('customerWelcome');
    welcomeDiv.innerHTML = `
        <h4>Welcome back, ${currentCustomer.name.split(' ')[0]}! 👋</h4>
        <p>${currentCustomer.email}</p>
    `;

    // Show policy dashboard
    renderPolicyDashboard();

    // Reset chat messages with welcome
    const chatMessages = document.getElementById('insuranceChatMessages');
    chatMessages.innerHTML = `
        <div class="ai-message">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
                <p>Hello ${currentCustomer.name.split(' ')[0]}! I'm your Bedrock Insurance Advisor. I can help you with:</p>
                <ul>
                    <li>Understanding your coverage details</li>
                    <li>Filing or checking claims</li>
                    <li>Policy questions and renewals</li>
                    <li>Getting quotes for additional coverage</li>
                </ul>
                <p>What can I help you with today?</p>
            </div>
        </div>
    `;
}

// Render policy dashboard
function renderPolicyDashboard() {
    const dashboardDiv = document.getElementById('policyDashboard');

    let policiesHTML = '<div class="policy-grid">';

    currentCustomer.policies.forEach(policy => {
        const icon = policy.type === 'home' ? '🏠' : '🚗';
        policiesHTML += `
            <div class="policy-card" onclick="showPolicyDetails('${policy.number}')">
                <div class="policy-type">${icon} ${policy.type} Insurance</div>
                <div class="policy-number">${policy.number}</div>
                <div class="policy-coverage">${policy.coverage}</div>
                <span class="policy-status ${policy.status}">${policy.status.toUpperCase()}</span>
            </div>
        `;
    });

    policiesHTML += '</div>';

    // Add quick actions
    policiesHTML += `
        <div style="margin-top: 15px; display: flex; gap: 10px; flex-wrap: wrap;">
            <button class="cta-button secondary-cta" style="flex: 1; min-width: 140px;" onclick="askAboutCoverage()">
                📋 View Coverage
            </button>
            <button class="cta-button secondary-cta" style="flex: 1; min-width: 140px;" onclick="startClaim()">
                📝 File Claim
            </button>
        </div>
    `;

    dashboardDiv.innerHTML = policiesHTML;
}

// Show policy details
function showPolicyDetails(policyNumber) {
    const policy = currentCustomer.policies.find(p => p.number === policyNumber);
    if (!policy) return;

    addInsuranceMessage(`Tell me about policy ${policyNumber}`, 'user');

    // Trigger AI response with policy details
    setTimeout(() => {
        let details = `Here are the details for your ${policy.type} insurance policy **${policy.number}**:\n\n`;
        details += `**Coverage:** ${policy.coverage}\n`;
        details += `**Premium:** ${policy.premium}\n`;
        details += `**Deductible:** ${policy.deductible}\n`;

        if (policy.address) details += `**Property:** ${policy.address}\n`;
        if (policy.vehicle) details += `**Vehicle:** ${policy.vehicle}\n`;

        details += `\n**Features:**\n`;
        policy.features.forEach(f => {
            details += `• ${f}\n`;
        });

        details += `\n**Renewal Date:** ${new Date(policy.renewal_date).toLocaleDateString()}\n\n`;
        details += `Is there anything specific you'd like to know about this policy?`;

        addInsuranceMessage(details, 'ai');
    }, 500);
}

// Quick action: Ask about coverage
function askAboutCoverage() {
    addInsuranceMessage("What coverage do I have?", 'user');
    sendInsuranceAIRequest("What coverage do I have?");
}

// Quick action: Start claim
function startClaim() {
    addInsuranceMessage("I want to file a claim", 'user');

    setTimeout(() => {
        let message = "I can help you file a claim. Which type of claim do you need to file?\n\n";
        currentCustomer.policies.forEach(p => {
            message += `• ${p.type === 'home' ? '🏠' : '🚗'} ${p.type.toUpperCase()} - Policy ${p.number}\n`;
        });
        message += "\nPlease let me know which policy this claim is for.";

        addInsuranceMessage(message, 'ai');
    }, 500);
}

// Send message
function sendInsuranceMessage(event) {
    event.preventDefault();

    const input = document.getElementById('insuranceChatInput');
    const message = input.value.trim();

    if (!message) return;

    addInsuranceMessage(message, 'user');
    input.value = '';

    // Send to AI
    sendInsuranceAIRequest(message);
}

// Add user message to chat
        </div >
    `;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Add AI message to chat
function addAIMessage(text) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'ai-message';

    // Convert markdown-style formatting to HTML
    const formatted = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');

    messageDiv.innerHTML = `
    < div class="message-avatar" >🤖</div >
        <div class="message-content">
            ${formatted}
        </div>
`;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Send request to AI
async function sendInsuranceAIRequest(message) {
    const typingIndicator = document.getElementById('typingIndicator');
    typingIndicator.style.display = 'flex';

    try {
        const response = await fetch('/api/insurance/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                customer_id: currentCustomer.id
            })
        });

        const data = await response.json();

        typingIndicator.style.display = 'none';

        if (data.response) {
            addAIMessage(data.response);
        }
    } catch (error) {
        typingIndicator.style.display = 'none';
        addAIMessage("I apologize, but I'm having trouble connecting. Please try again.");
    }
}

// Utility: Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    const modal = document.getElementById('chatModal');
    if (e.target === modal) {
        closeChat();
    }
});
