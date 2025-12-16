import streamlit as st
import sqlite3
import time
import requests
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_core.callbacks import BaseCallbackHandler
from ollama import Client  # New import for Worker

# Configuration
import os

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(SCRIPT_DIR, "chroma_db")
EMBEDDING_MODEL = "nomic-embed-text"
DEFAULT_LLM = "qwen2.5-coder:32b"
DB_PATH = "chat_history.db"

# Remote Worker Config
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
WORKER_IP = "127.0.0.1" # Still used for fallback logic if needed, but primary is OLLAMA_HOST
WORKER_PORT = "11434"
WORKER_MODEL = "llama3.3"

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

# --- RAG Pipeline ---
@st.cache_resource
def get_chain(model_name):
    """Initialize the Conversational RAG pipeline."""
    try:
        embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_HOST)
        db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
        
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
        st.error(f"Failed to initialize RAG pipeline: {e}")
        return None

# --- Main App ---
def main():
    st.set_page_config(page_title="Swayne Intelligence", layout="wide", page_icon="📡")
    
    # Initialize DB
    init_db()

    # Load Full History from DB
    if "db_history" not in st.session_state:
        st.session_state.db_history = get_messages()

    # Sidebar: App Controls
    logo_path = os.path.join(SCRIPT_DIR, "assets", "logo.png")
    if os.path.exists(logo_path):
        st.sidebar.image(logo_path, use_container_width=True)
    
    st.sidebar.title("Swayne Intelligence")
    st.sidebar.caption("Central Command Node")
    
    # Model Selector
    available_models = get_ollama_models()
    try:
        default_idx = available_models.index(DEFAULT_LLM)
    except ValueError:
        try:
            default_idx = 0
            # If our default isn't there but others are, just pick the first one
        except:
             default_idx = 0
        
    selected_model = st.sidebar.selectbox("Active Model", available_models, index=default_idx)
    st.sidebar.caption(f"Status: Online ({selected_model})")
    
    # History Toggle
    st.sidebar.markdown("---")
    show_history = st.sidebar.checkbox("Show Operation Logs", value=False)
    
    # --- KNOWLEDGE SOURCE TOGGLE ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("🧠 Intelligence Source")
    knowledge_source = st.sidebar.radio(
        "Select Dataset:",
        ["Internal Database (Sterling)", "PrivateGPT Server"],
        captions=["ChromaDB + Ollama", "Mistral/Llama @ Port 8001"]
    )

    
    # --- DISTRIBUTED MODE TOGGLE ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚡️ Compute Cluster")
    use_distributed = st.sidebar.checkbox("Enable Council Mode", value=True)
    if use_distributed:
        st.sidebar.success(f"Connected: {WORKER_MODEL} via Mac Studio")
    
    if show_history:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Archived Logs")
        for msg in st.session_state.db_history:
             st.sidebar.text(f"{msg['role'].upper()}: {msg['content']}")
        st.sidebar.markdown("---")

    # Main Chat Interface
    st.title("📡 Swayne Intelligence")
    sub_title = "Proprietary RAG Interface"
    if use_distributed:
        sub_title = f"Distributed Grid Active (Manager: {selected_model} + Worker: {WORKER_MODEL})"
    st.caption(sub_title)
    
    if "current_session_messages" not in st.session_state:
        st.session_state.current_session_messages = []

    # Display Active Session
    for message in st.session_state.current_session_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "tokens" in message:
                st.caption(f"🪙 {message['tokens']}")

    # Initialize Chain (Reloads if model changes)
    qa_chain = get_chain(selected_model)
    if not qa_chain:
        st.stop()
        
    # Pre-populate memory from DB if fresh session
    if len(qa_chain.memory.chat_memory.messages) == 0 and len(st.session_state.db_history) > 0:
        recent = st.session_state.db_history[-10:]
        for msg in recent:
            if msg['role'] == 'user':
                qa_chain.memory.chat_memory.add_user_message(msg['content'])
            else:
                qa_chain.memory.chat_memory.add_ai_message(msg['content'])

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
            if knowledge_source == "PrivateGPT Server":
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

            elif use_distributed:
                worker_output_container = st.empty()
                with worker_output_container.status("⚡️ Orchestrating Distributed Task...", expanded=True) as status:
                    final_answer = ""
                    token_msg = ""
                    source_docs = []
                    
                    try:
                        # Step 1: Manager Planning (COUNCIL MODE)
                        status.write(f"🧠 Manager ({selected_model}) is convening the Council...")
                        manager_client = Client(host=OLLAMA_HOST)
                        
                        council_prompt = """You are the Council Chairman. Select the best team of 1-3 Personas to answer the user:
1. "Consultant" (Balanced): Best for advice, explanations, and nuance.
2. "Analyst" (Strict): Best for data, lists, math, and JSON/CSV.
3. "Maverick" (Cynic): Best for bold opinions, critiques, or "cut to the chase" answers.

Return JSON ONLY:
{
  "reasoning": "Why this team?",
  "team": ["Consultant", "Maverick"], 
  "instruction": "Clear instruction for the council"
}"""

                        manager_response = manager_client.chat(model=selected_model, format='json', messages=[
                            {'role': 'system', 'content': council_prompt},
                            {'role': 'user', 'content': f"User Question: {prompt}"}
                        ])
                        
                        import json
                        try:
                            decision = json.loads(manager_response['message']['content'])
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
                            if "Analyst" in persona:
                                model = "qwen2.5-coder:32b"
                                icon = "📊"
                                sys = "You are The Analyst. Be strict, dry, and data-driven. Output ONLY stats, lists, or code."
                            elif "Maverick" in persona:
                                model = "dolphin-llama3"
                                icon = "🦅"
                                sys = "You are The Maverick. Be cynical, bold, and unfiltered. Don't sugarcoat anything."
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

            else:
                # --- STANDARD LOCAL MODE ---
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
                    with st.expander("View Source Documents"):
                        for i, doc in enumerate(source_docs):
                            st.markdown(f"**Source {i+1}:** {doc.metadata.get('source', 'Unknown')}")
                            st.text(doc.page_content[:500] + "...")
                                    
                except Exception as e:
                    st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
