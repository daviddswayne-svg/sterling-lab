"""
ESC Family History Chat — Streamlit frontend for natural language database queries
Connects to ESC API running on Mac Studio M3 via SSH tunnel
"""

import streamlit as st
import requests
import json
import os
from io import BytesIO

# === CONFIGURATION ===
ESC_API_URL = os.getenv("ESC_API_URL", "http://localhost:8002")
REQUEST_TIMEOUT = 600  # seconds — Qwen queries typically take 60-200s; 600s safety net

# === STREAMLIT UI ===
st.set_page_config(
    page_title="Family History Explorer - Swayne Systems",
    page_icon="📷",
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

    /* SQL trace cards */
    .sql-trace {
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
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

    /* Expander for SQL trace */
    .stExpander {
        background: rgba(99, 102, 241, 0.05) !important;
        border: 1px solid rgba(99, 102, 241, 0.2) !important;
        border-radius: 12px !important;
    }

    .stExpander div, .stExpander p, .stExpander span {
        color: #ffffff !important;
    }

    /* Image grid */
    .image-grid-label {
        color: rgba(255,255,255,0.45);
        font-size: 0.75rem;
        margin-top: 0.75rem;
        margin-bottom: 0.4rem;
    }
    .image-caption {
        color: rgba(255,255,255,0.55);
        font-size: 0.72rem;
        text-align: center;
        margin-top: 0.2rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_thumbnail(image_id: int) -> bytes | None:
    """Fetch a thumbnail (400px). Cached so reruns on Load More don't re-fetch."""
    try:
        r = requests.get(f"{ESC_API_URL}/image/{image_id}", params={"size": "thumb"}, timeout=10)
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_large_image(image_id: int) -> bytes | None:
    """Fetch a large (1200px) version. Cached for fast repeat opens."""
    try:
        r = requests.get(f"{ESC_API_URL}/image/{image_id}", params={"size": "large"}, timeout=20)
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
    return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_image_meta(image_id: int) -> dict | None:
    """Fetch image metadata (filename, date, people, location). Cached so Load More is instant."""
    try:
        r = requests.get(f"{ESC_API_URL}/image/{image_id}/meta", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def render_image_grid(image_ids: list[int]):
    """Display a thumbnail grid for a list of image IDs."""
    if not image_ids:
        return

    st.markdown('<div class="image-grid-label">📷 Photos from this query</div>', unsafe_allow_html=True)

    # Fetch thumbnails + metadata (cap at 12)
    items = []
    for img_id in image_ids[:12]:
        thumb = fetch_thumbnail(img_id)
        if thumb:
            meta = fetch_image_meta(img_id)
            items.append((img_id, thumb, meta))

    if not items:
        return

    # 3-column grid
    cols = st.columns(3)
    mac_paths = []
    for i, (img_id, thumb_bytes, meta) in enumerate(items):
        with cols[i % 3]:
            # Build caption: filename + year
            if meta:
                name = meta.get("filename", f"ID {img_id}")
                date = meta.get("date", "")
                year = f"  {date[6:8]}" if len(date) >= 8 else ""
                if year:
                    yr = int(year)
                    year = f"  {'20' if yr <= 26 else '19'}{yr:02d}"
                people = meta.get("people", [])
                loc = meta.get("locations", [])
                caption_parts = [name + year]
                if people:
                    caption_parts.append(", ".join(people[:2]))
                if loc:
                    caption_parts.append(loc[0])
                caption = "  ·  ".join(caption_parts)
                if meta.get("mac_path"):
                    mac_paths.append((img_id, name, meta["mac_path"], thumb_bytes))
            else:
                caption = f"Image {img_id}"

            # Click to view larger image
            with st.popover("🔍", use_container_width=True):
                large = fetch_large_image(img_id)
                if large:
                    st.image(large, caption=caption, use_container_width=True)

            st.image(thumb_bytes, caption=caption[:60], use_container_width=True)

    st.caption(f"Showing {len(items)} of {len(image_ids)} photo{'s' if len(image_ids) != 1 else ''} found")

    # Mac path expander — thumbnail + 🔍 popover + copyable path
    if mac_paths:
        with st.expander(f"📁 File paths ({len(mac_paths)})", expanded=False):
            for img_id, name, path, thumb_bytes in mac_paths:
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.image(thumb_bytes, width=70)
                    with st.popover("🔍"):
                        large = fetch_large_image(img_id)
                        if large:
                            st.image(large, caption=name, use_container_width=True)
                with col2:
                    st.code(path, language=None)


def _photo_caption(meta: dict | None, img_id: int) -> str:
    """Build a short 1-line caption: filename + year."""
    if not meta:
        return f"ID {img_id}"
    name = meta.get("filename") or f"ID {img_id}"
    date = meta.get("date") or ""
    year = ""
    if len(date) >= 8:
        yr = int(date[6:8])
        year = f"  {'20' if yr <= 26 else '19'}{yr:02d}"
    return f"{name}{year}"


def _photo_popover_content(large_bytes: bytes | None, meta: dict | None):
    """Render large image + metadata inside a popover."""
    if large_bytes:
        st.image(large_bytes, use_container_width=True)
    if meta:
        parts = []
        if meta.get("trip"):
            parts.append(f"**Trip:** {meta['trip']}")
        people = meta.get("people", [])
        if people:
            parts.append(f"**People:** {', '.join(people)}")
        locs = meta.get("locations", [])
        if locs:
            parts.append(f"**Location:** {', '.join(locs[:2])}")
        if meta.get("quality"):
            parts.append(f"**Quality:** {meta['quality']}")
        if parts:
            st.markdown("  \n".join(parts))


def render_photo_browser(image_data: list[dict], msg_idx: int):
    """Lazy-loading photo gallery: 4-column thumbnail grid, 25 at a time. Skips off-disk images."""
    if not image_data:
        return

    count_key = f"shown_{msg_idx}"
    if count_key not in st.session_state:
        st.session_state[count_key] = 25

    total = len(image_data)
    shown = min(st.session_state[count_key], total)

    COLS = 4
    with st.expander(f"📷 Photos — {total} found", expanded=True):
        rendered = 0
        grid_cols = None
        for item in image_data[:shown]:
            img_id = item["id"]
            thumb = fetch_thumbnail(img_id)
            if thumb is None:
                continue  # skip images not on disk
            meta = fetch_image_meta(img_id)
            if rendered % COLS == 0:
                grid_cols = st.columns(COLS)
            with grid_cols[rendered % COLS]:
                st.image(thumb, use_container_width=True)
                caption = _photo_caption(meta, img_id)
                with st.popover("🔍", use_container_width=True):
                    large = fetch_large_image(img_id)
                    _photo_popover_content(large, meta)
                st.caption(caption)
            rendered += 1

        if rendered == 0:
            st.caption("No images found on disk for this query.")
        else:
            st.caption(f"Showing {rendered} of {total}")

        if shown < total:
            remaining = total - shown
            if st.button(f"Load 25 more ({remaining} remaining)", key=f"load_more_{msg_idx}"):
                st.session_state[count_key] = shown + 25
                st.rerun()


def fetch_stats():
    """Fetch database stats from ESC API."""
    try:
        r = requests.get(f"{ESC_API_URL}/stats", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def check_health():
    """Check ESC API health."""
    try:
        r = requests.get(f"{ESC_API_URL}/health", timeout=5)
        if r.status_code == 200:
            data = r.json()
            return data.get("database") == "ok" and data.get("ollama", "").startswith("ok")
    except Exception:
        pass
    return False


def fetch_model_status() -> dict:
    """Check if qwen3:32b is loaded and ready."""
    try:
        r = requests.get(f"{ESC_API_URL}/model_status", timeout=4)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {"status": "unknown", "label": "Unknown"}


def send_chat(message: str, history: list, mode: str = "photos") -> dict | None:
    """Send chat message to ESC API."""
    try:
        r = requests.post(
            f"{ESC_API_URL}/chat",
            json={"message": message, "history": history, "mode": mode},
            timeout=REQUEST_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json()
    except requests.exceptions.Timeout:
        return {"response": "The query timed out. Try a simpler question or be more specific about which tables to search.", "sql_trace": []}
    except Exception as e:
        return {"response": f"Connection error: {e}", "sql_trace": []}
    return None


def main():
    # === SIDEBAR ===
    st.sidebar.title("📷 Family History DB")
    st.sidebar.caption("Natural Language SQL Explorer")

    # Mode selector
    st.sidebar.markdown("---")
    mode_choice = st.sidebar.radio(
        "Mode",
        options=["📷 Photos", "📖 Journals"],
        index=0,
        help="Photos: search and display images\nJournals: read trip narrative entries"
    )
    mode = "journals" if mode_choice == "📖 Journals" else "photos"

    # Clear chat when mode changes
    if "active_mode" not in st.session_state:
        st.session_state.active_mode = mode
    if st.session_state.active_mode != mode:
        st.session_state.active_mode = mode
        st.session_state.messages = []
        st.session_state.thinking = False
        st.session_state.pop("pending_prompt", None)
        st.rerun()

    # Connection status
    st.sidebar.markdown("---")
    st.sidebar.subheader("Connection")
    healthy = check_health()
    if healthy:
        st.sidebar.success("Mac Studio M3 Connected")
    else:
        st.sidebar.error("Mac Studio M3 Offline")

    # Model status — use session flag while blocked so sidebar updates immediately
    if st.session_state.get("thinking", False):
        st.sidebar.info("qwen3:32b Thinking...")
    else:
        model_info = fetch_model_status()
        model_state = model_info.get("status", "unknown")
        if model_state == "ready":
            st.sidebar.success("qwen3:32b Ready")
        elif model_state == "idle":
            st.sidebar.warning("qwen3:32b Not Loaded")
            st.sidebar.caption("First query will take ~60s to load")
        else:
            st.sidebar.caption("qwen3 status unknown")

    # Database stats
    stats = fetch_stats()
    if stats:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Database")
        st.sidebar.metric("Photos", f"{stats.get('photos', 0):,}")
        col1, col2 = st.sidebar.columns(2)
        col1.metric("People", f"{stats.get('people', 0):,}")
        col2.metric("Trips", f"{stats.get('trips', 0):,}")
        col1, col2 = st.sidebar.columns(2)
        col1.metric("Geo Features", f"{stats.get('geo_features', 0):,}")
        col2.metric("Species", f"{stats.get('species', 0):,}")

    # Stop / Clear buttons
    st.sidebar.markdown("---")
    col1, col2 = st.sidebar.columns(2)
    if col1.button("⏹ Stop", help="Cancel any in-flight query"):
        try:
            requests.post(f"{ESC_API_URL}/cancel", timeout=3)
        except Exception:
            pass
        st.sidebar.caption("Query stopped.")
    if col2.button("Clear Chat"):
        try:
            requests.post(f"{ESC_API_URL}/cancel", timeout=3)
        except Exception:
            pass
        st.session_state.messages = []
        st.rerun()

    # Dashboard link
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        '<a href="/" target="_self" style="display:block;text-align:center;'
        'background:rgba(99,102,241,0.2);border:1px solid rgba(99,102,241,0.4);'
        'border-radius:10px;padding:10px;color:#f1f5f9;text-decoration:none;'
        'font-weight:600;">Dashboard</a>',
        unsafe_allow_html=True,
    )

    # === MAIN CONTENT ===
    if mode == "journals":
        st.title("📖 Family History Journals")
        st.caption("1,805 trip journals spanning the 1930s–2020s — mountaineering, fishing, family travels, and wildlife surveys")
    else:
        st.title("Family History Explorer")
        st.caption("144K photos · 3K people · 6.9K trips · 140+ years of Swayne family history")

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if not st.session_state.messages:
        if mode == "journals":
            welcome = """### Welcome to the Journal Explorer

Browse narrative trip journals written by Mike Swayne — 1,805 entries from the 1930s through 2020s. Journals are returned in full with the actual day-by-day narrative text.

**How to ask:**

📅 **Browse by topic or place** — returns a list of matching journals with excerpts:
> "Find fishing trip journals from the 1960s" · "Show me journals from Mount Rainier trips"

📖 **Read a specific trip** — returns the full journal:
> "Tell me about the 1971 Alaska road trip" · "What happened on the 1996 Aconcagua climb?"

🔍 **Search by keyword** — searches both trip names and journal text:
> "Find any journal mentioning the Sockeye run" · "Find journals that mention bears"

**Name tip:** If you say "Michael" or "Elizabeth" I'll ask which one — Dad and brother share a name, as do Mom and sister."""
        else:
            welcome = """### Welcome to the Family History Explorer

Ask questions about the Swayne family database in plain English — I'll query 121 tables covering people, photos, trips, geographic features, species, and more.

**How results are returned:**

📊 **By default, results come back as a table** — all rows, no summarizing. If you'd like a written summary instead, just say *"summarize"* or *"give me an overview."*

📷 **Photos are only shown when you ask for them** — include *"show photos"* or *"show images"* in your question to get the image grid alongside the results.

🏔️ **"Climbing trips" vs "trips"** — saying *"climbing trips"* filters to officially tagged climbing expeditions (more accurate for elevation queries). *"Trips"* is broader and includes everything.

👤 **Shared names** — "Michael" could be Dad (Mike) or brother, and "Elizabeth" could be Mom or sister. Use *"Dad," "Mom," "my brother,"* or *"my sister"* to be specific, or I'll ask you to clarify.

📅 **Decades work naturally** — "trips in the 1970s," "photos from the 1990s," "species photographed in the 1960s" all work as expected."""
        st.session_state.messages.append({"role": "assistant", "content": welcome})

    # Display chat history
    for msg_idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Photo browser (all images, lazy-loaded)
            if message.get("image_data"):
                render_photo_browser(message["image_data"], msg_idx)

            # Show SQL trace if present
            if message.get("sql_trace"):
                with st.expander("SQL Queries", expanded=False):
                    for i, trace in enumerate(message["sql_trace"]):
                        st.code(trace.get("sql", ""), language="sql")
                        if trace.get("result_preview"):
                            st.markdown(trace["result_preview"][:300])

    # Handle pending prompt — runs after history renders so user msg is visible first
    spinner_text = "Retrieving journal..." if mode == "journals" else "Querying the database..."
    if st.session_state.get("pending_prompt"):
        prompt = st.session_state.pop("pending_prompt")
        with st.chat_message("assistant"):
            with st.spinner(spinner_text):
                history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages[:-1]
                    if m["role"] in ("user", "assistant")
                ]
                result = send_chat(prompt, history, mode=mode)

                if result:
                    st.markdown(result["response"])

                    image_data = result.get("image_data", []) if mode == "photos" else []
                    new_msg_idx = len(st.session_state.messages)
                    if image_data:
                        render_photo_browser(image_data, new_msg_idx)

                    sql_trace = result.get("sql_trace", [])
                    trace_label = "Journal Queries" if mode == "journals" else "SQL Queries"
                    if sql_trace:
                        with st.expander(trace_label, expanded=False):
                            for trace in sql_trace:
                                sql_text = trace.get("sql", "")
                                if sql_text.startswith("get_journal("):
                                    st.code(sql_text, language="text")
                                else:
                                    st.code(sql_text, language="sql")
                                if trace.get("result_preview"):
                                    st.markdown(trace["result_preview"][:300])

                    timing = result.get("timing_ms", 0)
                    if timing:
                        st.caption(f"Completed in {timing / 1000:.1f}s using {result.get('model', 'unknown')}")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result["response"],
                        "sql_trace": sql_trace,
                        "image_ids": result.get("image_ids", []),
                        "image_data": image_data,
                    })
                else:
                    error_msg = "Failed to get a response from the ESC API. Is the Mac Studio connected?"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

        st.session_state.thinking = False

    # Chat input — set pending state and rerun so sidebar shows "Thinking..." immediately
    input_placeholder = "Ask about a journal or trip..." if mode == "journals" else "Ask about the family history..."
    if prompt := st.chat_input(input_placeholder):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.thinking = True
        st.session_state.pending_prompt = prompt
        st.rerun()


if __name__ == "__main__":
    main()
