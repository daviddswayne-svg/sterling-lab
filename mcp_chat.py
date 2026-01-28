"""
MCP-Powered Chat Interface for swaynesystems.ai
Replaces RAG with grounded tool execution via Model Context Protocol

Tools:
- Exa: Semantic web search (no hallucinations - real results)
- GitHub: Repository operations
- Filesystem: Local file access
- DeepSeek R1: Deep reasoning (M1 Ultra)
"""

import streamlit as st
import time
import requests
import json
import os
from datetime import datetime
from ollama import Client

# === CONFIGURATION ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# LLM Hosts (via SSH tunnels when deployed)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
M1_OLLAMA = os.getenv("M1_OLLAMA", "http://host.docker.internal:12434")

# Models
TOOL_MODEL = "llama3.3"  # Smart model for tool-calling decisions
SYNTH_MODEL = "gemma2:27b"  # Fast model for synthesizing responses

# API Keys (loaded from environment)
EXA_API_KEY = os.getenv("EXA_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")

# === MCP TOOL DEFINITIONS ===
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for current information using Exa semantic search. Use this for any factual questions, recent events, documentation, or when you need real-world data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "num_results": {"type": "integer", "description": "Number of results (1-10, default 5)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_repos",
            "description": "List GitHub repositories for a user or organization",
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "GitHub username or org name"}
                },
                "required": ["username"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "github_commits",
            "description": "Get recent commits from a GitHub repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "description": "Repository in format owner/repo"},
                    "limit": {"type": "integer", "description": "Number of commits (default 5)"}
                },
                "required": ["repo"]
            }
        }
    }
]

# === TOOL EXECUTION ===
def execute_tool(name: str, args: dict, status_callback=None) -> dict:
    """Execute an MCP tool and return structured result"""

    result = {"success": False, "data": None, "error": None}

    try:
        if name == "search_web":
            if not EXA_API_KEY:
                result["error"] = "Exa API key not configured"
                return result

            from exa_py import Exa
            exa = Exa(api_key=EXA_API_KEY)

            search_results = exa.search(
                args.get("query", ""),
                num_results=min(args.get("num_results", 5), 10),
                type="auto"
            )

            formatted = []
            for r in search_results.results:
                formatted.append({
                    "title": r.title or "No title",
                    "url": r.url,
                    "snippet": getattr(r, 'text', '')[:200] if hasattr(r, 'text') else ''
                })

            result["success"] = True
            result["data"] = formatted

        elif name == "github_repos":
            if not GITHUB_TOKEN:
                result["error"] = "GitHub token not configured"
                return result

            headers = {"Authorization": f"token {GITHUB_TOKEN}"}
            response = requests.get(
                f"https://api.github.com/users/{args['username']}/repos",
                headers=headers,
                params={"sort": "updated", "per_page": 10}
            )

            if response.status_code == 200:
                repos = response.json()
                result["success"] = True
                result["data"] = [{
                    "name": r["name"],
                    "description": r.get("description") or "No description",
                    "stars": r.get("stargazers_count", 0),
                    "updated": r.get("updated_at", "")[:10]
                } for r in repos]
            else:
                result["error"] = f"GitHub API error: {response.status_code}"

        elif name == "github_commits":
            if not GITHUB_TOKEN:
                result["error"] = "GitHub token not configured"
                return result

            headers = {"Authorization": f"token {GITHUB_TOKEN}"}
            response = requests.get(
                f"https://api.github.com/repos/{args['repo']}/commits",
                headers=headers,
                params={"per_page": args.get("limit", 5)}
            )

            if response.status_code == 200:
                commits = response.json()
                result["success"] = True
                result["data"] = [{
                    "sha": c["sha"][:7],
                    "message": c["commit"]["message"].split("\n")[0][:60],
                    "author": c["commit"]["author"]["name"],
                    "date": c["commit"]["author"]["date"][:10]
                } for c in commits]
            else:
                result["error"] = f"GitHub API error: {response.status_code}"

    except Exception as e:
        result["error"] = str(e)

    return result

def format_tool_result(name: str, result: dict) -> str:
    """Format tool result for display and LLM consumption"""

    if not result["success"]:
        return f"Tool error: {result['error']}"

    data = result["data"]

    if name == "search_web":
        lines = ["Web search results:"]
        for i, r in enumerate(data, 1):
            lines.append(f"{i}. **{r['title']}**")
            lines.append(f"   {r['url']}")
        return "\n".join(lines)

    elif name == "github_repos":
        lines = ["GitHub repositories:"]
        for r in data:
            lines.append(f"- **{r['name']}**: {r['description']} (⭐ {r['stars']}, updated {r['updated']})")
        return "\n".join(lines)

    elif name == "github_commits":
        lines = ["Recent commits:"]
        for c in data:
            lines.append(f"- `{c['sha']}` {c['message']} ({c['author']}, {c['date']})")
        return "\n".join(lines)

    return json.dumps(data, indent=2)

# === STREAMLIT UI ===
st.set_page_config(
    page_title="MCP Agent Lab - Swayne Systems",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (matching existing theme)
st.markdown("""
<style>
    /* Dark theme base */
    .stApp {
        background: linear-gradient(180deg, #0f1419 0%, #1a1f2e 100%);
    }

    /* Chat messages */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        margin-bottom: 1rem !important;
    }

    .stChatMessage, .stChatMessage div, .stChatMessage p, .stChatMessage span {
        color: #ffffff !important;
    }

    /* Tool action cards */
    .tool-card {
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
    }

    .tool-card.success {
        border-color: rgba(34, 197, 94, 0.5);
        background: rgba(34, 197, 94, 0.1);
    }

    .tool-card.pending {
        border-color: rgba(234, 179, 8, 0.5);
        background: rgba(234, 179, 8, 0.1);
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #1a1f2e !important;
    }

    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 1rem !important;
        font-weight: 600 !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.5);
    }

    /* Expander for tool trace */
    .stExpander {
        background: rgba(99, 102, 241, 0.05) !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        border-radius: 12px !important;
    }

    .stExpander div, .stExpander p, .stExpander span {
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

def main():
    # === SIDEBAR ===
    # Logo loading disabled to avoid numpy conflicts in some environments
    # logo_path = os.path.join(SCRIPT_DIR, "assets", "swaynesystems_logo.png")
    # if os.path.exists(logo_path):
    #     st.sidebar.image(logo_path, use_container_width=True)

    st.sidebar.title("🤖 MCP Agent Lab")
    st.sidebar.caption("Grounded AI • No Hallucinations")

    # Status indicators
    st.sidebar.markdown("---")
    st.sidebar.subheader("System Status")

    # Check M3 (tool model)
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=2)
        if r.status_code == 200:
            st.sidebar.success("🟢 M3 Ultra (Tool Agent)")
        else:
            st.sidebar.error("🔴 M3 Offline")
    except:
        st.sidebar.error("🔴 M3 Offline")

    # Tool status
    st.sidebar.markdown("---")
    st.sidebar.subheader("Available Tools")

    if EXA_API_KEY:
        st.sidebar.markdown("✅ **Exa Search** - Semantic web search")
    else:
        st.sidebar.markdown("❌ **Exa Search** - Key missing")

    if GITHUB_TOKEN:
        st.sidebar.markdown("✅ **GitHub** - Repo & commit access")
    else:
        st.sidebar.markdown("❌ **GitHub** - Token missing")

    st.sidebar.markdown("---")
    st.sidebar.caption(f"🧠 Decisions: {TOOL_MODEL}")
    st.sidebar.caption(f"⚡ Synthesis: {SYNTH_MODEL}")

    # Dashboard link
    st.sidebar.markdown("---")
    st.sidebar.markdown('<a href="/" target="_self" style="display:block;text-align:center;background:rgba(99,102,241,0.2);border:1px solid rgba(99,102,241,0.4);border-radius:10px;padding:10px;color:#f1f5f9;text-decoration:none;font-weight:600;">← Dashboard</a>', unsafe_allow_html=True)

    # === MAIN CONTENT ===
    st.title("🧪 MCP Agent Lab")
    st.caption(f"Powered by {TOOL_MODEL} (decisions) + {SYNTH_MODEL} (fast synthesis) • Grounded responses via MCP")

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Welcome message
        welcome = """### Welcome to the MCP Agent Lab

I'm your AI assistant with access to **real-time tools**:

| Tool | What it does |
|------|--------------|
| 🔍 **Exa Search** | Semantic web search for current information |
| 🐙 **GitHub** | Access your repositories and commits |

Unlike RAG systems, I don't hallucinate - I fetch **real data** from verified sources.

**Try asking:**
- "Search for the latest MCP protocol documentation"
- "Show me my GitHub repositories"
- "What are the recent commits in daviddswayne-svg/sterling-lab?"

How can I help you today?"""
        st.session_state.messages.append({"role": "assistant", "content": welcome})

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Show tool trace if present
            if "tool_trace" in message:
                with st.expander("🔧 Agent Actions", expanded=False):
                    for action in message["tool_trace"]:
                        status_icon = "✅" if action["success"] else "❌"
                        st.markdown(f"**{status_icon} {action['tool']}**")
                        st.code(json.dumps(action["args"], indent=2), language="json")
                        if action["success"]:
                            st.markdown(action["result_preview"])

    # Chat input
    if prompt := st.chat_input("Ask anything..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            tool_trace = []

            with st.status("🤖 Agent thinking...", expanded=True) as status:
                try:
                    # Call Llama 3.3 with tools
                    status.write("📤 Sending to Llama 3.3...")

                    client = Client(host=OLLAMA_HOST)
                    response = client.chat(
                        model=TOOL_MODEL,
                        messages=[{"role": "user", "content": prompt}],
                        tools=TOOLS
                    )

                    msg = response.get("message", {})
                    tool_calls = msg.get("tool_calls") or (msg.tool_calls if hasattr(msg, 'tool_calls') else None)

                    if tool_calls:
                        status.write(f"🔧 Agent requested {len(tool_calls)} tool(s)")

                        tool_results = []
                        for tc in tool_calls:
                            func = tc.function if hasattr(tc, 'function') else tc.get("function", {})
                            name = func.name if hasattr(func, 'name') else func.get('name')
                            args = func.arguments if hasattr(func, 'arguments') else func.get('arguments', {})

                            status.write(f"⚡ Executing: **{name}**")

                            # Execute tool
                            result = execute_tool(name, args, lambda s: status.write(s))
                            formatted = format_tool_result(name, result)

                            tool_trace.append({
                                "tool": name,
                                "args": args,
                                "success": result["success"],
                                "result_preview": formatted[:300] + "..." if len(formatted) > 300 else formatted
                            })

                            tool_results.append({
                                "tool": name,
                                "result": formatted
                            })

                            if result["success"]:
                                status.write(f"✅ {name} completed")
                            else:
                                status.write(f"❌ {name} failed: {result['error']}")

                        # Get final synthesis with STREAMING from fast model
                        status.write(f"⚡ {SYNTH_MODEL} synthesizing (streaming)...")
                        status.update(label="⚡ Streaming response...", state="running")

                        synthesis_prompt = f"""Based on the user's question and the tool results below, provide a helpful response.

User Question: {prompt}

Tool Results:
{chr(10).join([f"[{r['tool']}]: {r['result']}" for r in tool_results])}

Provide a clear, well-formatted response that directly answers the user's question using the tool results. Include relevant links and details."""

                        # Stream the response token by token
                        final_content = ""
                        stream = client.chat(
                            model=SYNTH_MODEL,
                            messages=[{"role": "user", "content": synthesis_prompt}],
                            stream=True
                        )

                        for chunk in stream:
                            token = chunk.get("message", {}).get("content", "")
                            if not token and hasattr(chunk.get("message", {}), "content"):
                                token = chunk["message"].content
                            final_content += token
                            response_placeholder.markdown(final_content + "▌")

                        # Final update without cursor
                        response_placeholder.markdown(final_content)
                        status.update(label="✅ Complete", state="complete")

                    else:
                        # No tools needed - direct response
                        final_content = msg.content if hasattr(msg, 'content') else msg.get("content", "")
                        status.update(label="✅ Complete", state="complete")

                    # Display response
                    response_placeholder.markdown(final_content)

                    # Show tool trace
                    if tool_trace:
                        with st.expander("🔧 Agent Actions", expanded=True):
                            for action in tool_trace:
                                status_icon = "✅" if action["success"] else "❌"
                                st.markdown(f"**{status_icon} {action['tool']}**")
                                st.code(json.dumps(action["args"], indent=2), language="json")
                                st.markdown(action["result_preview"])

                    # Save to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": final_content,
                        "tool_trace": tool_trace if tool_trace else None
                    })

                except Exception as e:
                    status.update(label="❌ Error", state="error")
                    error_msg = f"Error: {str(e)}"
                    response_placeholder.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

if __name__ == "__main__":
    main()
