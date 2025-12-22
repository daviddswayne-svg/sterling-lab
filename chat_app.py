import streamlit as st
# pysqlite3 fix for Docker deployment
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import sqlite3
import time
import requests
import json
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.caches import BaseCache
from langchain_core.callbacks import BaseCallbackHandler, Callbacks
try:
    ChatOllama.model_rebuild()
except Exception as e:
    pass
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from ollama import Client  # New import for Worker
import base64
from io import BytesIO
from PIL import Image

# Configuration
import os

# Configuration - Production Ready
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(SCRIPT_DIR, "chroma_db_synthetic")
EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_LLM = "qwen2.5-coder:32b"
DB_PATH = os.path.join(SCRIPT_DIR, "chat_history_frontier.db")

# Remote Worker Config (Mac Studio M3 via SSH Tunnel)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
WORKER_MODEL = "llama3.3"

# M1 Muscle Config (Direct SSH Tunnel for Oracle)
# Uses separate tunnel on port 12434 for deep reasoning
M1_OLLAMA = os.getenv("M1_OLLAMA", "http://host.docker.internal:12434")
FRONTIER_MODEL = "deepseek-r1:70b"
VISION_MODEL = "llama3.2-vision:latest"
AUTO_INGEST_DIR = os.getenv("AUTO_INGEST_DIR", os.path.join(SCRIPT_DIR, "auto_ingest"))

# --- Helper: Lab Stability ---
def get_lab_status():
    """Check connectivity to the M1 Muscle over Thunderbolt."""
    try:
        response = requests.get(f"{M1_OLLAMA}/api/tags", timeout=1)
        return response.status_code == 200
    except:
        return False

# --- Helper: Get Models ---
def get_ollama_models():
    """Fetch available models from local Ollama instance."""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags")
        if response.status_code == 200:
            models = [model['name'] for model in response.json()['models']]
            return models
    except Exception as e:
        pass
    return [DEFAULT_LLM, "llama3.1:latest", "gemma2:27b"] # Fallback

# --- Callbacks ---
class TokenCallbackHandler(BaseCallbackHandler):
    """Callback Handler that tracks token usage and speed for Ollama."""
    def __init__(self, container):
        self.tokens = {"input": 0, "output": 0, "total": 0}
        self.container = container
        self.output_counter = 0
        self.start_time = None
        self.end_time = None

    def on_llm_start(self, serialized, prompts, **kwargs):
        """Run when LLM starts running."""
        self.start_time = time.time()

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Run on new LLM token. Only available when streaming=True."""
        if self.start_time is None:
            self.start_time = time.time() # Fallback

        self.output_counter += 1
        # Update UI in real-time
        self.container.markdown(f"🪙 **Generating...** | Output Tokens: **{self.output_counter}**")

    def on_llm_end(self, response, **kwargs):
        self.end_time = time.time()
        duration = self.end_time - self.start_time if self.start_time else 0
        
        try:
            # Check for Ollama specific metadata in generations to get final precise counts
            if response.generations:
                for generations_list in response.generations:
                    for gen in generations_list:
                         if isinstance(gen.message.response_metadata, dict):
                            metadata = gen.message.response_metadata
                            # Ollama keys: prompt_eval_count, eval_count
                            self.tokens["input"] += metadata.get('prompt_eval_count', 0)
                            self.tokens["output"] = metadata.get('eval_count', self.output_counter)
                
                self.tokens["total"] = self.tokens["input"] + self.tokens["output"]
                
                # Calculate TPS
                tps = self.tokens["output"] / duration if duration > 0 else 0
                
                # Final Update with full stats
                token_str = f"Input: {self.tokens['input']} | Output: {self.tokens['output']} | Total: {self.tokens['total']} | Speed: **{tps:.2f} t/s**"
                self.container.markdown(f"🪙 **Finished** | {token_str}")
                
        except Exception as e:
            pass # Fail silently on stats

# --- PrivateGPT Integration ---
def query_private_gpt(prompt):
    """Query the running PrivateGPT server."""
    # Note: PrivateGPT might also need env var configuration eventually
    url = "http://localhost:8001/v1/completions"
    payload = {
        "prompt": prompt,
        "use_context": True,
        "include_sources": True,
        "stream": False
    }
    try:
        response = requests.post(url, json=payload, timeout=120)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Status {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": f"Connection Failed: {e}"}


# --- Database Functions ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_message(role, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO messages (role, content) VALUES (?, ?)', (role, content))
    conn.commit()
    conn.close()

def get_messages():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT role, content FROM messages ORDER BY id ASC')
    data = c.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in data]

def is_greeting(text):
    greetings = ["hello", "hi", "hey", "howdy", "morning", "afternoon", "evening", "how are you", "what's up", "yo"]
    clean_text = text.lower().strip().strip('?!.')
    return clean_text in greetings or len(clean_text) < 4

# --- Ingestion Helpers ---
def ingest_text_to_frontier(text, source_name="vision_upload.txt"):
    """Manually add a piece of text to the synthetic knowledge store."""
    try:
        from synthetic_ingest_2026 import generate_synthetic_qa
        from langchain_core.documents import Document
        
        st.info(f"🧬 Distilling 2026 insights for: {source_name}...")
        qa = generate_synthetic_qa(text)
        
        if not qa:
            st.error("❌ Failed to generate synthetic Q&A for this document.")
            return False
            
        synth_doc = Document(
            page_content=f"Question: {qa['question']}\nAnswer: {qa['answer']}",
            metadata={
                "source": source_name,
                "original_context": text,
                "is_synthetic": True,
                "auto_ingested": True
            }
        )
        
        embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_HOST)
        db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
        db.add_documents([synth_doc])
        
        st.success(f"✅ Ingested into 2026 Reasoning Grid.")
        return True
    except Exception as e:
        st.error(f"Ingestion Error: {e}")
        return False

# --- RAG Pipeline ---
@st.cache_resource
def get_chain(model_name):
    """Initialize the Conversational RAG pipeline."""
    try:
        # Initialize embeddings with detailed error handling
        try:
            embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_HOST)
        except Exception as emb_error:
            st.error(f"❌ Failed to initialize embeddings model '{EMBEDDING_MODEL}': {emb_error}")
            st.warning(f"💡 Ensure '{EMBEDDING_MODEL}' is available on {OLLAMA_HOST}")
            st.code(f"ollama pull {EMBEDDING_MODEL}", language="bash")
            return None
        
        # Load ChromaDB
        try:
            db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
        except Exception as db_error:
            st.error(f"❌ Failed to load ChromaDB from {CHROMA_PATH}: {db_error}")
            st.warning("💡 Try re-running ingestion: python ingest_sterling.py")
            return None
        
        # Use selected model
        llm = ChatOllama(model=model_name, temperature=0, streaming=True, base_url=OLLAMA_HOST)
        
        memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True,
            output_key='answer' 
        )
        
        retriever = db.as_retriever(search_kwargs={"k": 10})
        
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=retriever,
            memory=memory,
            return_source_documents=True,
            get_chat_history=lambda h: h
        )
        return qa_chain
    except Exception as e:
        st.error(f"❌ Failed to initialize RAG pipeline: {e}")
        import traceback
        st.code(traceback.format_exc(), language="python")
        return None


import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

# ... (Previous imports) ...

# --- Authentication ---
def load_auth():
    config_path = os.path.join(SCRIPT_DIR, 'config.yaml')
    with open(config_path) as file:
        config = yaml.load(file, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
    return authenticator

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="2026 Frontier Lab - Sterling Estate",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (Keeping existing styles but adding auth specific tweaks if needed)
st.markdown("""
<style>
    /* Match dashboard styling */
    .stApp {
        background: radial-gradient(circle at top right, #111827, #030712);
        color: #f1f5f9 !important;
    }
    
    /* Global Text Brightness (EXCLUDING Selectboxes, Inputs, and ICONS) */
    p:not([data-baseweb] *):not(.st-emotion-cache-* svg *), 
    span:not([data-baseweb] *):not(.st-emotion-cache-* svg *), 
    li, h1, h2, h3 {
        color: #f1f5f9 !important;
    }
    
    /* SURGICAL Selectbox Fix: Ensure Selected Value is WHITE */
    div[data-baseweb="select"] div[role="button"],
    div[data-baseweb="select"] div[role="button"] > div,
    div[data-baseweb="select"] div[role="button"] span {
        color: #ffffff !important;
    }

    /* Keep dropdown menu items readable (White on Dark background) */
    div[data-baseweb="popover"] div[data-baseweb="menu"] div,
    div[role="listbox"] div,
    div[role="listbox"] span,
    div[role="option"] span {
        color: #f1f5f9 !important;
    }
    
    /* Let icons use their default colors */
    
    /* Glassmorphism Sidebar */
    [data-testid="stSidebar"] {
        background: rgba(15, 20, 25, 0.7) !important;
        backdrop-filter: blur(12px);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Simplified Headers - NO overflow/cutoff */
    h1, h2, h3 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        color: #818cf8 !important;
        max-width: 100% !important;
        overflow: visible !important;
        white-space: normal !important;
        padding-top: 1rem !important;
        margin-top: 1rem !important;
    }
    
    /* Main title specifically - extra padding */
    .block-container h1:first-of-type {
        padding-top: 2rem !important;
        margin-top: 0 !important;
    }
    
    /* FORCE checkbox and toggle labels WHITE */
    .stCheckbox label,
    .stCheckbox label span,
    .stCheckbox label div,
    .stCheckbox label p,
    [data-testid="stCheckbox"] label,
    [data-testid="stCheckbox"] label *,
    /* Toggle labels */
    label[data-baseweb="checkbox"],
    label[data-baseweb="checkbox"] *,
    /* All label elements in sidebar */
    [data-testid="stSidebar"] label span,
    [data-testid="stSidebar"] label div,
    [data-testid="stSidebar"] label p {
        color: #ffffff !important;
    }
    
    /* Make "Active Model" label WHITE */
    .stSelectbox label,
    .stSelectbox label span,
    [data-testid="stSelectbox"] label,
    [data-testid="stSelectbox"] > label {
        color: #f1f5f9 !important;
    }
    
    /* Make ALL sidebar labels/widget text WHITE */
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }
    
    /* SPECIFIC FIX: File uploader label */
    [data-testid="stFileUploader"] label p,
    [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] p {
        color: #ffffff !important;
    }
    
    /* Custom Chat Container */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        margin-bottom: 1rem !important;
        box-shadow: 0 4px 24px -1px rgba(0, 0, 0, 0.2);
    }
    
    /* FORCE all chat message text to WHITE */
    .stChatMessage,
    .stChatMessage div,
    .stChatMessage p,
    .stChatMessage span,
    .stChatMessage li,
    .stChatMessage strong,
    .stChatMessage em {
        color: #ffffff !important;
    }
    
    /* Thinking Trace Glow */
    .stExpander {
        background: rgba(99, 102, 241, 0.05) !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        border-radius: 12px !important;
    }
    
    /* FORCE all expander content to WHITE */
    .stExpander div,
    .stExpander p,
    .stExpander span,
    .stExpander pre,
    .stExpander code {
        color: #ffffff !important;
    }
    
    /* Pulse Animation for Generating */
    @keyframes pulse {
        0% { opacity: 0.6; }
        50% { opacity: 1; }
        100% { opacity: 0.6; }
    }
    .generating-text {
        animation: pulse 1.5s infinite;
        color: #818cf8;
        font-weight: 500;
    }
    
    /* Buttons (Enforced) */
    /* Dashboard Button Styles */
    .dash-link-button {
        display: block !important;
        width: 100% !important;
        text-align: center !important;
        background: rgba(129, 138, 248, 0.1) !important;
        border: 1px solid rgba(129, 138, 248, 0.4) !important;
        border-radius: 12px !important;
        padding: 12px !important;
        color: #f1f5f9 !important;
        text-decoration: none !important;
        font-weight: 600 !important;
        margin-top: 2rem !important;
        transition: all 0.3s ease !important;
    }
    
    .dash-link-button:hover {
        background: rgba(129, 138, 248, 0.2) !important;
        border-color: #818cf8 !important;
        transform: translateY(-1px) !important;
    }

    .stButton > button {
        width: 100% !important;
        background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        padding: 0.6rem 1rem !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5) !important;
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    }
    
    /* Premium Image Upload UI Refinement */
    [data-testid="stFileUploader"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 2px dashed rgba(129, 138, 248, 0.3) !important;
        border-radius: 16px !important;
        padding: 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: rgba(129, 138, 248, 0.6) !important;
        background: rgba(255, 255, 255, 0.05) !important;
    }

    [data-testid="stFileUploaderDropzone"] {
        color: #f1f5f9 !important;
    }
    
    [data-testid="stFileUploaderDropzone"] p {
        color: #f1f5f9 !important;
    }
    
    [data-testid="stFileUploader"] label p {
        color: #f1f5f9 !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stFileUploader"] div[data-testid="stMarkdownContainer"] p {
        color: #1e293b !important; /* DARK TEXT on the light dropzone */
        font-weight: 500 !important;
    }

    [data-testid="stFileUploaderDropzone"] span {
        color: #1e293b !important; /* DARK TEXT on the light dropzone */
    }
    
    [data-testid="stFileUploader"] small {
        color: #475569 !important;
    }
    
    /* Force inner dropzone text to DARK for readability */
    [data-testid="stFileUploaderDropzone"] div[data-testid="stMarkdownContainer"] p,
    [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stFileUploaderDropzone"] small {
        color: #0f172a !important;
    }
    
    /* High-Contrast Uploader Overhaul */
    [data-testid="stFileUploader"] {
        background: rgba(15, 23, 42, 0.4) !important;
        border: 2px dashed rgba(129, 138, 248, 0.5) !important;
        border-radius: 12px !important;
        padding: 0.5rem !important;
    }
    
    [data-testid="stFileUploaderDropzone"] {
        background: transparent !important;
        color: #f1f5f9 !important;
    }

    [data-testid="stFileUploaderDropzone"] div[data-testid="stMarkdownContainer"] p {
        color: #f1f5f9 !important;
        font-weight: 500 !important;
    }

    [data-testid="stFileUploaderDropzone"] span {
        color: #f1f5f9 !important;
    }
    
    [data-testid="stFileUploader"] small {
        color: rgba(241, 245, 249, 0.7) !important;
    }
    
    /* Fix Upload Button Text */
    [data-testid="stFileUploader"] button {
        background: rgba(129, 138, 248, 0.2) !important;
        border: 1px solid rgba(129, 138, 248, 0.5) !important;
        color: #f1f5f9 !important;
    }
    
    /* Dashboard Button Styles (Unified) */
    .dash-link-button {
        display: block !important;
        width: 100% !important;
        text-align: center !important;
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(139, 92, 246, 0.15)) !important;
        border: 1px solid rgba(129, 138, 248, 0.4) !important;
        border-radius: 10px !important;
        padding: 10px !important;
        color: #f1f5f9 !important;
        text-decoration: none !important;
        font-weight: 600 !important;
        margin-top: 1rem !important;
        transition: all 0.3s ease !important;
    }
    
    .dash-link-button:hover {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.25), rgba(139, 92, 246, 0.25)) !important;
        border-color: #818cf8 !important;
    }

    /* Remove Streamlit Header & Spacing */
    header {visibility: hidden;}
    .stAppHeader {display: none;}
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 2rem !important;
        margin-top: -20px !important;
    }
    
    /* Remove redundant spacing in sidebar */
    [data-testid="stSidebarNav"] {display: none;}
    [data-testid="stSidebarUserContent"] {padding-top: 1rem;}
    
    /* Ensure markdown text in messages is bright */
    .stChatMessage div[data-testid="stMarkdownContainer"] p {
        color: #f1f5f9 !important;
        font-size: 1.05rem !important;
        line-height: 1.6 !important;
    }

</style>
""", unsafe_allow_html=True)

def main():
    # DIRECTLY RUN APPLICATION - NO AUTHENTICATION
    run_app()

def run_app():
    # Initialize DB
    init_db()

    # Load Full History from DB
    if "db_history" not in st.session_state:
        st.session_state.db_history = get_messages()
        
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0
    if "trigger_ingest" not in st.session_state:
        st.session_state.trigger_ingest = False

    # --- Sidebar ---
    logo_path = os.path.join(SCRIPT_DIR, "assets", "swaynesystems_logo.png")
    if os.path.exists(logo_path):
        st.sidebar.image(logo_path, use_container_width=True)
    
    st.sidebar.title("⚜️ Sterling Estate Office")
    st.sidebar.caption("Multi-Family Intelligence & Advisory")
    
    # Selection Console
    available_models = get_ollama_models()
    if DEFAULT_LLM not in available_models:
        default_index = 0 if available_models else 0
        if not available_models: available_models = [DEFAULT_LLM]
    else:
        default_index = available_models.index(DEFAULT_LLM)

    if "selected_model_name" not in st.session_state:
        st.session_state["selected_model_name"] = available_models[default_index]

    selected_model = st.sidebar.selectbox(
        "Active Model", 
        available_models, 
        index=default_index,
        key="temp_model_selector",
        on_change=lambda: st.session_state.update({"selected_model_name": st.session_state.temp_model_selector})
    )
    selected_model = st.session_state.get("selected_model_name", selected_model)
    st.sidebar.caption(f"⚡ {selected_model} Engine Online")
    
    # Intelligence Options
    col_a, col_b = st.sidebar.columns(2)
    with col_a:
        use_oracle = st.toggle("Oracle", value=False)
        if use_oracle:
            st.caption("DeepSeek Logic Active")
    with col_b:
        use_distributed = st.checkbox("Council", value=False)
    
    if st.sidebar.button("System Health Check", use_container_width=True):
        try:
            r1_status = requests.get(f"{M1_OLLAMA}/api/ps").json()
            st.sidebar.success("✅ M1 Weights Ready")
        except:
            st.sidebar.warning("M1 Hub Offline")

    # Main Chat Interface
    st.title("🧬 2026 Frontier Lab")
    sub_title = "Proprietary RAG Interface"
    if use_distributed:
        sub_title = f"Distributed Grid Active (Manager: {selected_model} + Worker: {WORKER_MODEL})"
    st.caption(sub_title)
    
    if "current_session_messages" not in st.session_state:
        st.session_state.current_session_messages = []
        
        # Show welcome greeting from receptionist on first load
        welcome_message = """### 💁 Welcome to the 2026 Frontier Lab
        
Good day! I'm **Vivienne**, your receptionist at the Sterling Estate's Frontier Intelligence Office. 

Please, make yourself comfortable. Our advanced AI systems are at your service, ready to assist with any inquiries about the Sterling Estate, our operations, or general analysis.

**Available Services:**
- **Standard Mode**: Direct RAG-powered analysis with your selected model
- **🔮 Oracle Mode**: Deep deductive reasoning via our M1 Muscle (DeepSeek-R1:70b) for complex forensic analysis
- **👥 Council Mode**: Multi-agent collaborative intelligence featuring our specialized team of personas

Feel free to ask anything! The Council and Oracle are standing by whenever you need them. Simply toggle their modes in the sidebar and I'll connect you immediately.

How may I assist you today?"""
        
        st.session_state.current_session_messages.append({
            "role": "assistant",
            "content": welcome_message
        })

    # Display Active Session
    for message in st.session_state.current_session_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "tokens" in message:
                st.caption(f"🪙 {message['tokens']}")

    # --- Side Bar Features ---
    # Moved up to ensure visibility
    
    # Initialize Chain (Reloads if model changes)
    # We do this inside a try-block to prevent the whole UI from dying on startup
    qa_chain = None
    try:
        qa_chain = get_chain(selected_model)
    except Exception as e:
        st.sidebar.error(f"RAG Engine Status: Error ({e})")
        
    if not qa_chain:
        st.sidebar.warning("⚠️ RAG Engine offline. Check Local Ollama.")
        
    # Pre-populate memory from DB if fresh session
    if qa_chain and len(qa_chain.memory.chat_memory.messages) == 0 and len(st.session_state.db_history) > 0:
        recent = st.session_state.db_history[-10:]
        for msg in recent:
            if msg['role'] == 'user':
                qa_chain.memory.chat_memory.add_user_message(msg['content'])
            else:
                qa_chain.memory.chat_memory.add_ai_message(msg['content'])

    # --- VISION AGENT ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("👁️ Vision Agent")
    st.sidebar.markdown('<p style="color: white; margin: 0; padding: 0.5rem 0;">Upload Image to Lab</p>', unsafe_allow_html=True)
    uploaded_image = st.sidebar.file_uploader(
        "",  # Empty label since we're using markdown above
        type=["png", "jpg", "jpeg"],
        key=f"uploader_{st.session_state.uploader_key}",
        label_visibility="collapsed"
    )
    if uploaded_image:
        st.sidebar.image(uploaded_image, caption="Cache Active", use_container_width=True)
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("🗑️ Discard", use_container_width=True, key="vision_discard_btn"):
                st.session_state.vision_analysis = None
                st.session_state.uploader_key += 1
                st.rerun()
        with col2:
            if st.session_state.get("vision_analysis"):
                if st.button("💾 Archive", use_container_width=True, key="vision_archive_btn"):
                    st.session_state.trigger_ingest = True
                    st.rerun()
            else:
                st.button("💾 Archive", use_container_width=True, disabled=True, key="vision_archive_disabled_btn")
        
        # Store analysis in session state to allow ingestion after viewing
        if "vision_analysis" not in st.session_state:
            st.session_state.vision_analysis = None
    
    # Check for triggered ingestion from sidebar
    if st.session_state.get("trigger_ingest"):
        with st.sidebar.status("Processing Ingestion..."):
            # Step A: Draft a formal text document
            drafter_client = Client(host=OLLAMA_HOST)
            draft_prompt = f"Convert this vision analysis into a formal Sterling Estate archival document. Maintain all IDs, dates, and forensic details.\n\nANALYSIS:\n{st.session_state.vision_analysis}"
            draft_resp = drafter_client.chat(model="dolphin-llama3", messages=[{'role': 'user', 'content': draft_prompt}])
            formal_draft = draft_resp['message']['content']
            
            # Step B: Save to auto_ingest
            timestamp = int(time.time())
            filename = f"auto_vision_{timestamp}.txt"
            file_path = os.path.join(AUTO_INGEST_DIR, filename)
            with open(file_path, "w") as f:
                f.write(formal_draft)
            
            # Step C: Ingest to Synthetic Store
            success = ingest_text_to_frontier(formal_draft, source_name=filename)
            if success:
                st.sidebar.success(f"Archived: {filename}")
                st.session_state.vision_analysis = None
                st.session_state.uploader_key += 1
                st.session_state.trigger_ingest = False
                time.sleep(1)
                st.rerun()
            else:
                st.sidebar.error("Ingestion failed.")
                st.session_state.trigger_ingest = False

    # --- Dashboard Navigation (Bottom) ---
    st.sidebar.markdown('<a href="/" target="_self" class="dash-link-button">← Dashboard</a>', unsafe_allow_html=True)

    # User Input
    if prompt := st.chat_input("Ask a question..."):
        # UI Update
        st.session_state.current_session_messages.append({"role": "user", "content": prompt})
        st.session_state.db_history.append({"role": "user", "content": prompt})
        save_message("user", prompt)
        
        with st.chat_message("user"):
            st.markdown(prompt)

            # Generate RESPONSE
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            token_placeholder = st.empty()
            
            # --- DISTRIBUTED LOGIC ---
            if False: # PrivateGPT Mode Disabled
                pass
                # === PrivateGPT Mode ===
                with st.spinner("🤖 asking PrivateGPT..."):
                    resp = query_private_gpt(prompt)
                    
                    if "error" in resp:
                        st.error(resp["error"])
                        save_message("assistant", f"Error: {resp['error']}")
                    else:
                        # Parse PrivateGPT Response
                        # Note: The response format depends on the PrivateGPT version.
                        # Using specific /v1/completions logic
                        try:
                            # Standard format for text completion with sources
                            answer = resp['choices'][0]['message']['content']
                            sources = resp['choices'][0]['sources']
                            
                            st.markdown(answer)
                            
                            # Display Sources
                            if sources:
                                with st.expander("View PrivateGPT Sources"):
                                    for src in sources:
                                        doc = src.get("document", {})
                                        meta = doc.get("doc_metadata", {})
                                        filename = meta.get("file_name", "Unknown File")
                                        text = src.get("text", "")
                                        score = src.get("score", 0.0)
                                        st.markdown(f"**{filename}** (Relevance: {score:.2f})")
                                        st.text(text[:300] + "...")
                                        
                            # Save
                            st.session_state.current_session_messages.append({"role": "assistant", "content": answer})
                            st.session_state.db_history.append({"role": "assistant", "content": answer})
                            save_message("assistant", answer)
                            
                        except Exception as e:
                             st.error(f"Failed to parse response: {e}. Raw: {resp}")

            elif uploaded_image:
                # --- VISION AGENT MODE (Priority if image is present) ---
                if not get_lab_status():
                    st.error("❌ M1 Muscle is Offline. Vision requires the Thunderbolt bridge.")
                    st.stop()
                
                with st.spinner("👁️ Frontier Vision Agent is analyzing..."):
                    try:
                        # Convert image to base64
                        img = Image.open(uploaded_image)
                        # Fix for RGBA/PNG images
                        if img.mode in ('RGBA', 'P'):
                            img = img.convert('RGB')
                        buffered = BytesIO()
                        img.save(buffered, format="JPEG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        
                        client = Client(host=M1_OLLAMA)
                        response = client.generate(
                            model="llama3.2-vision", 
                            prompt=prompt if prompt else "Analyze this image in the context of the Sterling Estate.",
                            images=[img_str],
                            stream=True
                        )
                        
                        final_answer = ""
                        answer_placeholder = st.empty()
                        
                        for chunk in response:
                            if 'response' in chunk:
                                final_answer += chunk['response']
                                answer_placeholder.markdown(final_answer + "▌")
                        
                        answer_placeholder.markdown(final_answer)
                        st.session_state.vision_analysis = final_answer
                        
                        # Save
                        st.session_state.current_session_messages.append({"role": "assistant", "content": final_answer})
                        st.session_state.db_history.append({"role": "assistant", "content": final_answer})
                        save_message("assistant", final_answer)
                        
                        # Rerun to update sidebar "Archive" button state
                        st.rerun()

                    except Exception as e:
                        st.error(f"Vision Connection Error: {e}")

                # --- New Ingestion Button in Sidebar for Vision Analysis ---
                if st.session_state.get("vision_analysis"):
                    st.sidebar.markdown("---")
                    st.sidebar.subheader("💾 Ingestion Factory")
                    if st.sidebar.button("Archive to 2026 Archive & Dismiss"):
                        st.session_state.trigger_ingest = True
                        st.rerun()

            elif use_distributed:
                # --- COUNCIL MODE with RECEPTIONIST ---
                
                # Step 1: RECEPTIONIST provides immediate feedback
                receptionist_placeholder = st.empty()
                with receptionist_placeholder.container():
                    st.markdown("### 💁 Sterling Estate Receptionist")
                    receptionist_msg = st.empty()
                    
                    # Adapt receptionist message for Council mode
                    if use_oracle:
                        service_desc = "our Frontier Council with Oracle oversight"
                    else:
                        service_desc = "our Frontier Council"
                    
                    receptionist_prompt = f'''You are Vivienne, the warm and professional receptionist at the Sterling Estate's Frontier service.
                    
A client just asked: "{prompt}"

Your task:
1. Acknowledge their question with warmth and professionalism
2. Tell them you're connecting them to {service_desc} for collaborative analysis
3. Provide 2-3 sentences of general context about how the Council works together to give them something to read while they wait
4. Keep it witty, sophisticated, and concise (3-4 sentences total)
5. End by saying the Council is now convening

Be friendly but professional - like a high-end concierge service.'''
                    
                    try:
                        recept_client = Client(host=OLLAMA_HOST)
                        recept_response = recept_client.chat(
                            model=selected_model,
                            messages=[{'role': 'user', 'content': receptionist_prompt}]
                        )
                        receptionist_text = recept_response['message']['content']
                        receptionist_msg.markdown(receptionist_text)
                    except:
                        receptionist_msg.markdown("☎️ **Connecting you to the Council for collaborative analysis...**")
                
                # Step 2: Council Processing
                worker_output_container = st.empty()
                with worker_output_container.status("⚡️ Orchestrating Distributed Task...", expanded=True) as status:
                    final_answer = ""
                    token_msg = ""
                    source_docs = []
                    
                    try:
                        # Step 1: Manager Planning (COUNCIL MODE)
                        status.write(f"🧠 Manager ({selected_model}) is convening the Council...")
                        manager_client = Client(host=OLLAMA_HOST)
                        
                        # Modify Council prompt to include Oracle when both modes are on
                        if use_oracle:
                            council_prompt = """You are the Council Chairman selecting team members based on the question type.

Available Personas:
1. **Analyst** - Technical expert. SELECT for: data analysis, calculations, code, structured outputs (JSON/CSV/lists), technical troubleshooting, metrics
2. **Consultant** - Professional advisor. SELECT for: strategic advice, explanations, balanced perspectives, general guidance
3. **Maverick** - Contrarian thinker. SELECT for: debates, critiques, alternative viewpoints, devil's advocate, provocative insights
4. **Oracle** - Deep reasoner (M1). SELECT for: complex mysteries, forensic analysis, connecting hidden patterns, deductive reasoning

RULES:
- Match personas to question type (technical = Analyst, strategic = Consultant, critical = Maverick, forensic = Oracle)
- Use 2-4 personas. Mix different viewpoints for complex questions
- Don't always pick the same team. Vary based on the question's nature

Return JSON ONLY (No Markdown, No Code Blocks):
{
  "reasoning": "Why this specific team for THIS question?",
  "team": ["persona1", "persona2"],
  "instruction": "What the team should focus on"
}"""
                        else:
                            council_prompt = """You are the Council Chairman selecting team members based on the question type.

Available Personas:
1. **Analyst** - Technical expert. SELECT for: data analysis, calculations, code, structured outputs (JSON/CSV/lists), technical troubleshooting, metrics
2. **Consultant** - Professional advisor. SELECT for: strategic advice, explanations, balanced perspectives, general guidance
3. **Maverick** - Contrarian thinker. SELECT for: debates, critiques, alternative viewpoints, devil's advocate, provocative insights

RULES:
- Match personas to question type (technical = Analyst, strategic = Consultant, critical = Maverick)
- Use 1-3 personas. Mix different viewpoints for complex questions
- Don't always pick the same team. Vary based on the question's nature

Return JSON ONLY (No Markdown, No Code Blocks):
{
  "reasoning": "Why this specific team for THIS question?",
  "team": ["persona1", "persona2"],
  "instruction": "What the team should focus on"
}"""

                        manager_response = manager_client.chat(model=selected_model, format='json', messages=[
                            {'role': 'system', 'content': council_prompt},
                            {'role': 'user', 'content': f"User Question: {prompt}"}
                        ])
                        
                        try:
                            # FIX: Strip markdown code blocks if present
                            clean_json = manager_response['message']['content']
                            if "```" in clean_json:
                                clean_json = clean_json.split("```")[1]
                                if clean_json.startswith("json"):
                                    clean_json = clean_json[4:]
                            
                            decision = json.loads(clean_json)
                            team = decision.get("team", ["Consultant"])
                            instruction = decision.get("instruction", "")
                            reason = decision.get("reasoning", "")
                        except:
                            team = ["Consultant"]
                            instruction = manager_response['message']['content']
                            reason = "Parse failed."

                        # Manager Stats
                        m_tokens = manager_response.get('eval_count', 0)
                        m_dur_sec = manager_response.get('eval_duration', 0) / 1e9
                        m_tps = m_tokens / m_dur_sec if m_dur_sec > 0 else 0
                        status.markdown(f"> **Council Team:** {', '.join(team)}\n> **Goal:** {reason}")

                        # Step 2: RAG Retrieval
                        if is_greeting(prompt):
                            status.write("👋 Detected greeting. Skipping context retrieval.")
                            context_text = "No additional context required for this greeting."
                            relevant_docs = []
                        else:
                            status.write("📚 Manager is retrieving documents...")
                            retriever = qa_chain.retriever
                            relevant_docs = retriever.invoke(prompt)
                            context_text = "\n\n".join([f"Source: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content}" for doc in relevant_docs])
                        
                        source_docs = relevant_docs # Assign relevant_docs to source_docs for later display
                        
                        # Step 3: Council Execution (Sequential)
                        council_replies = []
                        total_worker_tokens = 0
                        
                        for persona in team:
                            # Map Persona to Real Model & Prompt
                            if "Oracle" in persona:
                                # Special handling for Oracle on M1
                                if not get_lab_status():
                                    council_replies.append("### 🔮 Oracle Failed:\nM1 Muscle is offline. Oracle requires Thunderbolt bridge.")
                                    continue
                                    
                                model = FRONTIER_MODEL
                                icon = "🔮"
                                sys = "You are The Oracle. Provide deep deductive analysis with forensic precision. Connect hidden patterns and examine contradictions."
                                
                                status.write(f"{icon} {persona} ({model}) is performing deep analysis via M1...")
                                
                                oracle_payload = f"""[INSTRUCTION]
{instruction}

[CONTEXT - Forensic Archive]
{context_text}

[QUESTION]
{prompt}

Provide a deep forensic analysis. Identify patterns, contradictions, and hidden connections."""
                                
                                try:
                                    # Call M1 Oracle directly
                                    payload = {
                                        "model": FRONTIER_MODEL,
                                        "prompt": oracle_payload,
                                        "stream": False
                                    }
                                    oracle_resp = requests.post(f"{M1_OLLAMA}/api/generate", json=payload)
                                    oracle_data = oracle_resp.json()
                                    content = oracle_data.get('response', 'Oracle response failed')
                                    # Filter out thinking tags
                                    content = content.replace('<think>', '').replace('</think>', '')
                                    council_replies.append(f"### {icon} {persona}'s Deep Analysis:\n{content}")
                                    total_worker_tokens += oracle_data.get('eval_count', 0)
                                except Exception as e:
                                    council_replies.append(f"### {icon} {persona} Failed:\n{e}")
                                    
                            elif "Analyst" in persona:
                                model = "qwen2.5-coder:32b"
                                icon = "📊"
                                sys = "You are The Analyst. Be strict, dry, and data-driven. Output ONLY stats, lists, or code."
                                status.write(f"{icon} {persona} ({model}) is thinking...")
                                
                                worker_payload = f"""[INSTRUCTION]
{instruction}

[CONTEXT]
{context_text}

[QUESTION]
{prompt}"""
                                
                                try:
                                    worker_client = Client(host=OLLAMA_HOST)
                                    w_resp = worker_client.chat(model=model, messages=[
                                        {'role': 'system', 'content': sys},
                                        {'role': 'user', 'content': worker_payload}
                                    ])
                                    content = w_resp['message']['content']
                                    council_replies.append(f"### {icon} {persona}'s Verification:\n{content}")
                                    total_worker_tokens += w_resp.get('eval_count', 0)
                                except Exception as e:
                                    council_replies.append(f"### {icon} {persona} Failed:\n{e}")
                                    
                            elif "Maverick" in persona:
                                model = "dolphin-llama3"
                                icon = "🦅"
                                sys = "You are The Maverick. Be cynical, bold, and unfiltered. Don't sugarcoat anything."
                                status.write(f"{icon} {persona} ({model}) is thinking...")
                                
                                worker_payload = f"""[INSTRUCTION]
{instruction}

[CONTEXT]
{context_text}

[QUESTION]
{prompt}"""
                                
                                try:
                                    worker_client = Client(host=OLLAMA_HOST)
                                    w_resp = worker_client.chat(model=model, messages=[
                                        {'role': 'system', 'content': sys},
                                        {'role': 'user', 'content': worker_payload}
                                    ])
                                    content = w_resp['message']['content']
                                    council_replies.append(f"### {icon} {persona}'s Verification:\n{content}")
                                    total_worker_tokens += w_resp.get('eval_count', 0)
                                except Exception as e:
                                    council_replies.append(f"### {icon} {persona} Failed:\n{e}")
                                    
                            else: # Consultant
                                model = "llama3.3"
                                icon = "👔"
                                sys = "You are The Consultant. Be helpful, professional, and explain things clearly."
                                status.write(f"{icon} {persona} ({model}) is thinking...")
                                
                                worker_payload = f"""[INSTRUCTION]
{instruction}

[CONTEXT]
{context_text}

[QUESTION]
{prompt}"""
                                
                                try:
                                    worker_client = Client(host=OLLAMA_HOST)
                                    w_resp = worker_client.chat(model=model, messages=[
                                        {'role': 'system', 'content': sys},
                                        {'role': 'user', 'content': worker_payload}
                                    ])
                                    content = w_resp['message']['content']
                                    council_replies.append(f"### {icon} {persona}'s Verification:\n{content}")
                                    total_worker_tokens += w_resp.get('eval_count', 0)
                                except Exception as e:
                                    # Fallback to Localhost if remote fails
                                    try:
                                        status.write(f"⚠️ Primary connection attempt failed. Using local fallback...")
                                        worker_client = Client(host='http://localhost:11434')
                                        w_resp = worker_client.chat(model=model, messages=[
                                            {'role': 'system', 'content': sys},
                                            {'role': 'user', 'content': worker_payload}
                                        ])
                                        content = w_resp['message']['content']
                                        council_replies.append(f"### {icon} {persona}'s Verification (Local Backup):\n{content}")
                                        total_worker_tokens += w_resp.get('eval_count', 0)
                                    except Exception as e2:
                                        council_replies.append(f"### {icon} {persona} Failed:\n{e} | Backup: {e2}")

                        # Step 4: Chairman Synthesis
                        status.write("🧠 Chairman is synthesizing the Council's advice...")
                        final_payload = f"""The User asked: "{prompt}"
                        
Here is what your Council reported:
{chr(10).join(council_replies)}

Synthesize these into a single Final Answer. Use the structure:
1. **The Council's View**: Detailed synthesis of the different perspectives.
2. **Final Recommendation**: Concrete advice.
"""
                        chairman_resp = manager_client.chat(model=selected_model, messages=[
                            {'role': 'system', 'content': "You are the Chairman. Synthesize the Council's reports into a cohesive final answer."},
                            {'role': 'user', 'content': final_payload}
                        ])
                        
                        final_answer = chairman_resp['message']['content']
                        
                        # Stats
                        c_tokens = chairman_resp.get('eval_count', 0)
                        
                        status.update(label=f"✅ Council Adjourned (Team: {', '.join(team)})", state="complete", expanded=False)
                        
                        token_msg = f"**Usage**: Manager ({m_tokens+c_tokens}) + Council ({total_worker_tokens}) tokens."

                    except Exception as e:
                        status.update(label="❌ Council Failed", state="error")
                        st.error(f"Connection to AI backend failed: {e}")
                        final_answer = "I attempted to contact the AI backend but the connection failed. Please verify the SSH tunnel to Mac Studio is active."
                
                # Display Final Logic
                message_placeholder.markdown(final_answer)
                st.caption(token_msg)
                
                # Save to history
                st.session_state.current_session_messages.append({
                    "role": "assistant", 
                    "content": final_answer,
                    "tokens": token_msg if token_msg else "Error"
                })
                st.session_state.db_history.append({"role": "assistant", "content": final_answer})
                save_message("assistant", final_answer)
                
                # Sources (Same as Local Mode)
                if source_docs:
                    with st.expander("View Source Documents (Retrieved by Manager)"):
                        for i, doc in enumerate(source_docs):
                            st.markdown(f"**Source {i+1}:** {doc.metadata.get('source', 'Unknown')}")
                            st.text(doc.page_content[:500] + "...")

            elif use_oracle:
                # --- ORACLE REASONING MODE (M1) with RECEPTIONIST ---
                if not get_lab_status():
                    st.error("❌ M1 Muscle is Offline. Oracle Mode requires the Thunderbolt bridge.")
                    st.stop()
                
                # Step 1: RECEPTIONIST provides immediate feedback
                receptionist_placeholder = st.empty()
                with receptionist_placeholder.container():
                    st.markdown("### 💁 Sterling Estate Receptionist")
                    receptionist_msg = st.empty()
                    
                    # Generate warm receptionist message
                    receptionist_prompt = f'''You are Vivienne, the warm and professional receptionist at the Sterling Estate's Frontier Oracle service. 
                    
A client just asked: "{prompt}"

Your task:
1. Acknowledge their question with warmth and professionalism
2. Tell them you're connecting them to the Oracle for deep analysis
3. Provide 2-3 sentences of general context or advice related to their question to give them something interesting to read while they wait
4. Keep it witty, sophisticated, and concise (3-4 sentences total)
5. End by saying the Oracle is now reviewing their case

Be friendly but professional - like a high-end concierge service.'''
                    
                    try:
                        # Use fast local model for receptionist
                        recept_client = Client(host=OLLAMA_HOST)
                        recept_response = recept_client.chat(
                            model=selected_model,  # Use the currently selected fast model
                            messages=[{'role': 'user', 'content': receptionist_prompt}]
                        )
                        receptionist_text = recept_response['message']['content']
                        receptionist_msg.markdown(receptionist_text)
                    except:
                        receptionist_msg.markdown("☎️ **Connecting you to the Oracle for deep analysis...**")
                
                # Step 2: Oracle Processing
                with st.spinner("🔮 Oracle is analyzing..."):
                    try:
                        # Context Retrieval
                        if is_greeting(prompt):
                            context_text = "The user is greeting you. Respond with a welcoming, forensic Frontier Oracle persona."
                            relevant_docs = []
                        else:
                            retriever = qa_chain.retriever
                            relevant_docs = retriever.invoke(prompt)
                            context_text = "\n\n".join([f"Source: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content}" for doc in relevant_docs])
                        
                        # Build Oracle Prompt with explicit thinking instructions
                        oracle_prompt = f"""You are the 2026 Frontier Oracle with deep reasoning capabilities.

IMPORTANT: Wrap ALL your reasoning steps in <think> tags. Show your complete thought process.

Use the following context from the Sterling Family Office archive to provide a DEEP DEDUCTIVE ANALYSIS.

CONTEXT:
---
{context_text}
---

QUESTION:
{prompt}

Format your response EXACTLY like this:

<think>
Step 1: Let me analyze the available documents...
[Your detailed reasoning process here - be thorough and show all steps]
Step 2: Cross-referencing the information...
[Continue showing your work]
Step 3: Identifying patterns and contradictions...
[Keep showing reasoning]
Conclusion: Based on this analysis...
</think>

[Your final, distilled answer here - clear and concise]

Analysis Focus:
1. Identify specific transactions or forensic details in the context
2. Examine medical, financial, and legal overlaps  
3. Locate active statuses of family members or aliases
4. Conclude with deductive reasoning on the user's query

Remember: Show ALL reasoning in <think> tags, then provide your final answer outside the tags.
"""

                        # Call M1 Oracle
                        payload = {
                            "model": FRONTIER_MODEL,
                            "prompt": oracle_prompt,
                            "stream": True
                        }
                        
                        response = requests.post(f"{M1_OLLAMA}/api/generate", json=payload, stream=True)
                        
                        # Split-screen theater mode: Thinking on left, Answer on right
                        st.markdown("### 🔮 Oracle Analysis Theater")
                        
                        col_think, col_answer = st.columns(2)
                        
                        with col_think:
                            st.markdown("#### 💭 Thinking Process")
                            st.caption("*Watch the Oracle reason in real-time*")
                            thinking_placeholder = st.empty()
                        
                        with col_answer:
                            st.markdown("#### ✨ Final Answer")
                            st.caption("*Distilled analysis*")
                            answer_placeholder = st.empty()
                        
                        # State tracking
                        thinking_content = ""
                        final_answer = ""
                        in_think_block = False
                        
                        for line in response.iter_lines():
                            if line:
                                chunk = json.loads(line)
                                if 'response' in chunk:
                                    content = chunk['response']
                                    
                                    # Handle tag detection and state changes
                                    if "<think>" in content:
                                        in_think_block = True
                                        content = content.replace("<think>", "")
                                    
                                    # Route content BEFORE changing state for closing tag
                                    if in_think_block:
                                        # Check if this chunk ends the thinking block
                                        if "</think>" in content:
                                            # Remove closing tag and add content to thinking
                                            content = content.replace("</think>", "")
                                            if content.strip():
                                                thinking_content += content
                                                thinking_placeholder.markdown(thinking_content + " ✓")
                                            # NOW end the thinking block
                                            in_think_block = False
                                        else:
                                            # Normal thinking content
                                            thinking_content += content
                                            thinking_placeholder.markdown(thinking_content + " 🤔")
                                    else:
                                        # This is answer content
                                        clean_content = content.replace("<think>", "").replace("</think>", "")
                                        if clean_content.strip():
                                            final_answer += clean_content
                                            answer_placeholder.markdown(final_answer + "▌")
                        
                        # Final Polish
                        answer_placeholder.markdown(final_answer)
                        
                        # Save to history
                        st.session_state.current_session_messages.append({"role": "assistant", "content": final_answer})
                        st.session_state.db_history.append({"role": "assistant", "content": final_answer})
                        save_message("assistant", final_answer)
                        
                        # Sources
                        if relevant_docs:
                            with st.expander("View Forensic Sources (Retrieved for Oracle)"):
                                for i, doc in enumerate(relevant_docs):
                                    st.markdown(f"**Source {i+1}:** {doc.metadata.get('source', 'Unknown')}")
                                    st.text(doc.page_content[:500] + "...")

                    except Exception as e:
                        st.error(f"Oracle Connection Error: {e}")

            else:
                # --- STANDARD LOCAL MODE ---
                if not qa_chain:
                    st.error("❌ RAG Engine is not initialized. Please verify Local Ollama status.")
                    st.stop()
                try:
                    # Setup Callback for this run
                    class StreamHandler(TokenCallbackHandler):
                         def __init__(self, token_container, text_container):
                             super().__init__(token_container)
                             self.text_container = text_container
                             self.text = ""
                             
                         def on_llm_new_token(self, token: str, **kwargs) -> None:
                             super().on_llm_new_token(token, **kwargs)
                             self.text += token
                             self.text_container.markdown(self.text + "▌")
                    
                    stream_handler = StreamHandler(token_placeholder, message_placeholder)
                    
                    # Invoke Chain
                    response = qa_chain.invoke(
                        {"question": prompt},
                        config={'callbacks': [stream_handler]}
                    )
                    
                    answer = response.get("answer")
                    source_docs = response.get("source_documents", [])
                    
                    # Final Polish
                    message_placeholder.markdown(answer)
                    
                    # Token Stats
                    tps = stream_handler.tokens["output"] / (stream_handler.end_time - stream_handler.start_time) if (stream_handler.end_time and stream_handler.start_time) else 0
                    token_str = f"Input: {stream_handler.tokens['input']} | Output: {stream_handler.tokens['output']} | Total: {stream_handler.tokens['total']} | Speed: **{tps:.2f} t/s**"
                    
                    # Save
                    st.session_state.current_session_messages.append({
                        "role": "assistant", 
                        "content": answer,
                        "tokens": token_str
                    })
                    st.session_state.db_history.append({"role": "assistant", "content": answer})
                    save_message("assistant", answer)
                    
                    # Sources
                    if source_docs:
                        with st.expander("View Source Documents"):
                            for i, doc in enumerate(source_docs):
                                st.markdown(f"**Source {i+1}:** {doc.metadata.get('source', 'Unknown')}")
                                st.text(doc.page_content[:500] + "...")
                                    
                except Exception as e:
                    st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
