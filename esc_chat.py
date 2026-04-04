"""
ESC Family History Chat — Streamlit frontend for natural language database queries
Connects to ESC API running on Mac Studio M3 via SSH tunnel
"""

import streamlit as st
import requests
import json
import os
import re
from io import BytesIO
from pathlib import Path

# === CONFIGURATION ===
ESC_API_URL = os.getenv("ESC_API_URL", "http://localhost:8002")
# ESC_MAP_URL: browser-accessible base URL for the map endpoint.
# Locally this equals ESC_API_URL. When deployed, set this env var to the
# public-facing URL where /map/{id} is reachable from the user's browser.
ESC_MAP_URL = os.getenv("ESC_MAP_URL", ESC_API_URL)
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


def render_photo_browser(image_data: list[dict], msg_idx: int,
                         label: str = None, expanded: bool = True):
    """Lazy-loading photo gallery: 4-column thumbnail grid, 25 at a time. Skips off-disk images."""
    if not image_data:
        return

    count_key = f"shown_{msg_idx}"
    if count_key not in st.session_state:
        st.session_state[count_key] = 25

    total = len(image_data)
    shown = min(st.session_state[count_key], total)
    expander_label = label or f"📷 Photos — {total} found"

    COLS = 4
    with st.expander(expander_label, expanded=expanded):
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


# ── Mike's Journal Magazine ──────────────────────────────────────────────────

_MONTHS_CLIENT = {
    'january': '01', 'february': '02', 'march': '03', 'april': '04',
    'may': '05', 'june': '06', 'july': '07', 'august': '08',
    'september': '09', 'october': '10', 'november': '11', 'december': '12',
}

_DAY_HDR = re.compile(
    r'^(?:'
    # Format A: weekday prefix — "Monday, March 4, 2012 Location"
    r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)'
    r'(?:/(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday))?'
    r'[,\s]+'
    r'|'
    # Format B: month-first with dash — "July 15 – Location" or "July 15 - Location"
    r'(?=(?:January|February|March|April|May|June|July|August|'
    r'September|October|November|December)\s+\d{1,2}\s*[\u2013\u2014\-])'
    r')'
    r'(January|February|March|April|May|June|July|August|September|October|November|December)'
    r'\s+(\d{1,2})(?:/\d{1,2})?'
    r'(?:[,\s]+(\d{4}))?',
    re.IGNORECASE,
)


def _render_inline_photos(ids: list[int]):
    """Render 1-3 photos centered inline between journal paragraphs."""
    available = []
    for img_id in ids:
        thumb = fetch_thumbnail(img_id)
        if thumb:
            available.append((img_id, thumb))
        if len(available) == 3:
            break
    if not available:
        return
    n = len(available)
    if n == 1:
        cols = st.columns([2, 3, 2])
        photo_cols = [cols[1]]
    elif n == 2:
        cols = st.columns([1, 3, 3, 1])
        photo_cols = [cols[1], cols[2]]
    else:
        cols = st.columns([1, 2, 2, 2, 1])
        photo_cols = [cols[1], cols[2], cols[3]]
    for (img_id, thumb), col in zip(available, photo_cols):
        with col:
            meta = fetch_image_meta(img_id)
            st.image(thumb, use_container_width=True)
            with st.popover("🔍", use_container_width=True):
                large = fetch_large_image(img_id)
                _photo_popover_content(large, meta)
            st.caption(_photo_caption(meta, img_id))


def render_journal_magazine(response: str, day_photos: list[dict],
                             all_image_data: list[dict], msg_idx: int):
    """Render a journal as Mike's Journal Magazine — day sections with inline photos."""
    photos_by_date = {d["date"]: d["ids"] for d in day_photos}

    # Split header block (# title + metadata) from journal body at the --- divider
    if "\n---\n\n" in response:
        header_part, body = response.split("\n---\n\n", 1)
        st.markdown(header_part + "\n\n---")
    else:
        body = response

    # Split body into per-day sections
    lines = body.split('\n')
    sections: list[tuple] = []  # (header_line | None, date_key | None, body_text)
    cur_header: str | None = None
    cur_date: str | None = None
    cur_lines: list[str] = []

    for line in lines:
        m = _DAY_HDR.match(line.strip())
        if m and line.strip():
            # Save previous section
            sections.append((cur_header, cur_date, '\n'.join(cur_lines).strip()))
            cur_header = line.strip()
            month_name, day_str, year_str = m.group(1), m.group(2), m.group(3)
            month = _MONTHS_CLIENT[month_name.lower()]
            day = int(day_str)
            if year_str:
                yr = int(year_str) % 100
                cur_date = f"{month}/{day:02d}/{yr:02d}"
            else:
                # No year in header — find matching key from backend day_photos by MM/DD
                md_prefix = f"{month}/{day:02d}/"
                cur_date = next((k for k in photos_by_date if k.startswith(md_prefix)), None)
            cur_lines = []
        else:
            cur_lines.append(line)
    sections.append((cur_header, cur_date, '\n'.join(cur_lines).strip()))

    # Render each day section
    has_sections = any(hdr for hdr, _, _ in sections)
    if not has_sections:
        # No parseable day headers — just show body text
        st.markdown(body)
    else:
        rendered_dates: set[str] = set()
        for header, date_key, text in sections:
            # Skip location-log entries: header with no body text.
            # Some journals have per-location lines (e.g. "Sunday, March 4 Wanganella Cove")
            # with no prose — these would otherwise create 100+ duplicate photo blocks.
            if header and not text:
                continue
            if header:
                st.markdown(f"**{header}**")
            if text:
                st.markdown(text)
            # Only show photos once per date (backend may have multiple headers/same date)
            if date_key and date_key in photos_by_date and date_key not in rendered_dates:
                _render_inline_photos(photos_by_date[date_key])
                rendered_dates.add(date_key)
            if header:
                st.markdown("---")

    # All trip photos expander at bottom (collapsed — journal text is primary)
    if all_image_data:
        total = len(all_image_data)
        render_photo_browser(
            all_image_data, msg_idx,
            label=f"📷 All Trip Photos — {total} on record",
            expanded=False,
        )


def _render_map_link(trip_id: int):
    """Render map buttons: 2D Leaflet map + 3D terrain viewer."""
    map_url   = f"{ESC_MAP_URL}/map/{trip_id}"
    map3d_url = f"{ESC_MAP_URL}/map3d/{trip_id}"
    st.markdown(
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;">'
        f'<a href="{map_url}" target="_blank" rel="noopener" style="'
        'display:inline-block;padding:10px 22px;'
        'background:rgba(59,130,246,0.15);border:1px solid rgba(59,130,246,0.5);'
        'border-radius:8px;color:#93c5fd;text-decoration:none;font-weight:600;font-size:15px;'
        '">🗺️ Open Trip Map</a>'
        f'<a href="{map3d_url}" target="_blank" rel="noopener" style="'
        'display:inline-block;padding:10px 22px;'
        'background:rgba(139,92,246,0.15);border:1px solid rgba(139,92,246,0.5);'
        'border-radius:8px;color:#c4b5fd;text-decoration:none;font-weight:600;font-size:15px;'
        '">🏔️ 3D Terrain</a>'
        '</div>',
        unsafe_allow_html=True,
    )


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


def show_auth_page():
    """Login / Register page shown to unauthenticated users."""
    st.title("Family History Explorer")
    st.caption("Swayne Systems · Private access for Swayne family members")

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", key="login_btn", use_container_width=True):
            if not username or not password:
                st.warning("Please enter your username and password.")
            else:
                try:
                    r = requests.post(
                        f"{ESC_API_URL}/auth/login",
                        json={"username": username, "password": password},
                        timeout=10,
                    )
                    if r.status_code == 200:
                        user = r.json()
                        st.session_state.user = user
                        st.session_state.session_id = user["session_id"]
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Login failed."))
                except Exception as e:
                    st.error(f"Connection error: {e}")

    with tab_register:
        st.caption("Register using your RDX ID from the family database. Ask David if you don't know yours.")
        rdx_id = st.number_input("Your RDX ID", min_value=1, step=1, key="reg_rdx")
        first_name = st.text_input("Your first name (as it appears in the database)", key="reg_fname")
        new_username = st.text_input("Choose a username", key="reg_username")
        new_password = st.text_input("Choose a password (6+ characters)", type="password", key="reg_password")
        confirm_password = st.text_input("Confirm password", type="password", key="reg_confirm")
        if st.button("Register", key="register_btn", use_container_width=True):
            if not all([rdx_id, first_name, new_username, new_password, confirm_password]):
                st.warning("Please fill in all fields.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                try:
                    r = requests.post(
                        f"{ESC_API_URL}/auth/register",
                        json={
                            "rdx_id": int(rdx_id),
                            "first_name": first_name,
                            "username": new_username,
                            "password": new_password,
                        },
                        timeout=10,
                    )
                    if r.status_code == 200:
                        user = r.json()
                        st.session_state.user = user
                        st.session_state.session_id = user["session_id"]
                        st.rerun()
                    else:
                        st.error(r.json().get("detail", "Registration failed."))
                except Exception as e:
                    st.error(f"Connection error: {e}")


def main():
    # Auth gate — show login/register if not authenticated
    if not st.session_state.get("user"):
        show_auth_page()
        return

    # === SIDEBAR ===
    st.sidebar.title("📷 Family History DB")
    st.sidebar.caption("Natural Language SQL Explorer")

    # Logged-in user + logout
    user = st.session_state.get("user", {})
    st.sidebar.markdown(f"**{user.get('display_name', 'User')}**")
    if st.sidebar.button("Logout", key="logout_btn"):
        try:
            requests.post(
                f"{ESC_API_URL}/auth/logout",
                params={"session_id": st.session_state.get("session_id")},
                timeout=5,
            )
        except Exception:
            pass
        for key in ["user", "session_id", "messages", "thinking", "active_mode", "pending_prompt"]:
            st.session_state.pop(key, None)
        st.rerun()

    # Change password
    with st.sidebar.expander("🔑 Change Password"):
        cp_current = st.text_input("Current password", type="password", key="cp_current")
        cp_new = st.text_input("New password (6+ chars)", type="password", key="cp_new")
        cp_confirm = st.text_input("Confirm new password", type="password", key="cp_confirm")
        if st.button("Update Password", key="cp_btn"):
            if not all([cp_current, cp_new, cp_confirm]):
                st.error("Please fill in all fields.")
            elif cp_new != cp_confirm:
                st.error("New passwords do not match.")
            elif len(cp_new) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                try:
                    r = requests.post(
                        f"{ESC_API_URL}/auth/change_password",
                        json={"user_id": user["id"], "current_password": cp_current, "new_password": cp_new},
                        timeout=10,
                    )
                    if r.status_code == 200:
                        st.success("Password updated.")
                    else:
                        st.error(r.json().get("detail", "Failed to update password."))
                except Exception as e:
                    st.error(f"Connection error: {e}")

    # Activity log
    with st.sidebar.expander("📊 My Activity"):
        if st.button("Load Activity", key="activity_load_btn"):
            try:
                r = requests.get(f"{ESC_API_URL}/auth/activity", params={"user_id": user["id"]}, timeout=10)
                if r.status_code == 200:
                    st.session_state.activity_data = r.json()
            except Exception as e:
                st.error(f"Connection error: {e}")

        activity = st.session_state.get("activity_data")
        if activity:
            sessions = activity.get("sessions", [])
            queries = activity.get("queries", [])

            st.markdown("**Login History**")
            if sessions:
                for s in sessions[:10]:
                    login = s["login_at"][:16].replace("T", " ")
                    logout = s["logout_at"][:16].replace("T", " ") if s["logout_at"] else "active"
                    st.caption(f"In: {login} · Out: {logout}")
            else:
                st.caption("No sessions recorded.")

            st.markdown("**Query History**")
            if queries:
                for q in queries[:20]:
                    when = q["at"][:16].replace("T", " ")
                    st.caption(f"{when} — {q['query'][:60]}")
            else:
                st.caption("No queries recorded.")

            if queries and st.button("Clear Query History", key="clear_queries_btn"):
                try:
                    r = requests.delete(f"{ESC_API_URL}/auth/activity", params={"user_id": user["id"]}, timeout=10)
                    if r.status_code == 200:
                        st.session_state.activity_data["queries"] = []
                        st.success("Query history cleared.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Connection error: {e}")

    # Mode selector
    st.sidebar.markdown("---")
    mode_choice = st.sidebar.radio(
        "Mode",
        options=["📷 Photos", "📖 Journals", "🗺️ Trip Map"],
        index=0,
        help="Photos: search and display images\nJournals: read trip narrative entries\nTrip Map: view an interactive route map for any trip"
    )
    if mode_choice == "📖 Journals":
        mode = "journals"
    elif mode_choice == "🗺️ Trip Map":
        mode = "map"
    else:
        mode = "photos"

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


    # Database schema diagram
    schema_path = Path(__file__).parent / "ESC-Swayne-Database.png"
    if schema_path.exists():
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Database Schema**")
        with open(schema_path, "rb") as f:
            schema_bytes = f.read()
        st.sidebar.image(schema_bytes, use_container_width=True)
        with st.sidebar.popover("🔍 Full size", use_container_width=True):
            st.image(schema_bytes, caption="ESC Swayne Database Schema", use_container_width=True)

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
        st.title("📖 Mike's Journal Magazine")
        st.caption("1,805 trip journals spanning the 1930s–2020s · Each journal opens as a photo magazine with day-by-day narrative and inline photos")
    elif mode == "map":
        st.title("🗺️ Trip Map")
        st.caption("Interactive route maps with GPS tracks, waypoints, and clickable photo locations")
    else:
        st.title("Family History Explorer")
        st.caption("144K photos · 3K people · 6.9K trips · 140+ years of Swayne family history")

    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if not st.session_state.messages:
        if mode == "map":
            welcome = """### Welcome to Trip Map

View interactive route maps for any trip in the database. Maps show GPS route segments (when available), ordered waypoints with elevation, and clickable 📷 camera icons that open photos from that location.

**How to use it:**

🗺️ **Name a specific trip:**
> "Show me the map for the 1959 Big Snow Mountain trip"
> "Map the 2011 Cascade Pass to Stehekin backpack"

🔍 **If multiple trips match**, I'll list them so you can pick the right one:
> "Show a map for a Nepal trip" → lists matching trips → "Map trip 5969"

🆔 **Use a trip ID directly:**
> "Map trip 640" · "Show map for trip 5859"

**Map features:**
- 🔴 GPS route line (CalTopo) when available, or dashed line connecting waypoints
- 🔵 DB waypoints with name and elevation
- 📷 Camera icons — click any to see a photo from that location"""
        elif mode == "journals":
            welcome = """### Welcome to Mike's Journal Magazine

Mike Swayne kept detailed trip journals from the 1930s through the 2020s — mountaineering, fishing, road trips, wildlife surveys, and family travels. When you open a specific journal, it renders as a **photo magazine**: day-by-day narrative with photos matched to each day inline, and a full trip photo gallery at the bottom.

**How to use it:**

📅 **Browse by topic or place** — returns a list of matching journals with excerpts:
> "Find fishing trip journals from the 1960s" · "Show me journals from Mount Rainier trips"

📖 **Open a specific journal** — renders the full photo magazine:
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

👤 **Names & nicknames** — *"Mike"* = Michael Dennis Swayne · *"Michael"* = Michael Thomas Swayne · *"Dave"* = David · *"Don"* = Donald · *"Lillie"* = Elizabeth Brown Swayne · *"Liz"* = Elizabeth Ann Swayne. Say *"Elizabeth"* alone and I'll ask which one.

📅 **Decades work naturally** — "trips in the 1970s," "photos from the 1990s," "species photographed in the 1960s" all work as expected."""
        st.session_state.messages.append({"role": "assistant", "content": welcome})

    # Display chat history
    for msg_idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            if message.get("is_magazine"):
                render_journal_magazine(
                    message["content"],
                    message.get("day_photos", []),
                    message.get("image_data", []),
                    msg_idx,
                )
            else:
                st.markdown(message["content"])
                if message.get("image_data"):
                    render_photo_browser(message["image_data"], msg_idx)
                if message.get("map_trip_id"):
                    _render_map_link(message["map_trip_id"])
                if mode == "journals" and not message.get("is_magazine") and "(TripID:" in message.get("content", ""):
                    st.info("💡 To open a journal as a photo magazine, ask about a specific trip — e.g. *\"Tell me about the [trip name]\"*")

            # Show SQL trace if present
            if message.get("sql_trace"):
                with st.expander("SQL Queries", expanded=False):
                    for i, trace in enumerate(message["sql_trace"]):
                        st.code(trace.get("sql", ""), language="sql")
                        if trace.get("result_preview"):
                            st.markdown(trace["result_preview"][:300])

    # Handle pending prompt — runs after history renders so user msg is visible first
    if mode == "journals":
        spinner_text = "Retrieving journal..."
    elif mode == "map":
        spinner_text = "Searching trips..."
    else:
        spinner_text = "Querying the database..."
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
                    image_data = result.get("image_data", [])
                    day_photos = result.get("day_photos", []) if mode == "journals" else []
                    new_msg_idx = len(st.session_state.messages)
                    is_magazine = mode == "journals" and bool(image_data or day_photos)

                    map_trip_id = result.get("map_trip_id")

                    if is_magazine:
                        render_journal_magazine(
                            result["response"], day_photos, image_data, new_msg_idx
                        )
                    else:
                        st.markdown(result["response"])
                        if image_data:
                            render_photo_browser(image_data, new_msg_idx)
                        if map_trip_id:
                            _render_map_link(map_trip_id)
                        # In journals mode, if the response is a search list (not a full journal),
                        # prompt the user to ask about a specific trip to open the photo magazine
                        if mode == "journals" and not is_magazine and "(TripID:" in result.get("response", ""):
                            st.info("💡 To open a journal as a photo magazine, ask about a specific trip — e.g. *\"Tell me about the [trip name]\"*")

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
                        "day_photos": day_photos,
                        "is_magazine": is_magazine,
                        "map_trip_id": map_trip_id,
                    })
                else:
                    error_msg = "Failed to get a response from the ESC API. Is the Mac Studio connected?"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

        st.session_state.thinking = False

    # Chat input — set pending state and rerun so sidebar shows "Thinking..." immediately
    if mode == "map":
        input_placeholder = "Name a trip to map, or say 'map trip 640'..."
    elif mode == "journals":
        input_placeholder = "Ask about a journal or trip..."
    else:
        input_placeholder = "Ask about the family history..."
    if prompt := st.chat_input(input_placeholder):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.thinking = True
        st.session_state.pending_prompt = prompt
        # Log the query (fire-and-forget, never block the UI)
        _user = st.session_state.get("user", {})
        if _user:
            try:
                requests.post(
                    f"{ESC_API_URL}/auth/log_query",
                    params={
                        "user_id": _user["id"],
                        "session_id": st.session_state.get("session_id"),
                        "query": prompt,
                    },
                    timeout=3,
                )
            except Exception:
                pass
        st.rerun()


if __name__ == "__main__":
    main()
