"""Tiny local service that lets the site's ⚡ button start a REAL Bedrock staff meeting, safely.

    python -m bedrock_agents.trigger_server            # 127.0.0.1:9101 (launchd: com.swaynesystems.bedrock-trigger)

The site container only proxies to this service (through the existing SSH reverse tunnel), so every rule
lives here on the M3 and cannot be bypassed from the website:

  * one meeting per hour (10 minutes after a failed one, so it can retry); a run that already started counts
  * one meeting at a time (the same flock run_meeting.py takes, so the 06:00 scheduled run is covered too)
  * kill switch: `touch ~/bedrock-publisher/state/DISABLED`  (remove the file to re-enable)
  * binds 127.0.0.1 only; stdlib only

Endpoints
  POST /run     -> {"status": "started" | "running" | "cooldown" | "disabled" | "error", ...}
  GET  /status  -> live progress of the current/last meeting (events so far) + cooldown info
  GET  /health  -> {"ok": true}
"""
import fcntl
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = int(os.environ.get("BEDROCK_TRIGGER_PORT", "9101"))
STATE_DIR = os.environ.get("BEDROCK_STATE_DIR", os.path.expanduser("~/bedrock-publisher/state"))
CLONE_DIR = os.environ.get("BEDROCK_CLONE_DIR", os.path.expanduser("~/bedrock-publisher/sterling-lab"))
PYTHON = os.environ.get("BEDROCK_PYTHON", sys.executable)
COOLDOWN_OK_S = int(os.environ.get("BEDROCK_COOLDOWN_S", "3600"))
COOLDOWN_FAILED_S = int(os.environ.get("BEDROCK_COOLDOWN_FAILED_S", "600"))

_start_lock = threading.Lock()  # serialises concurrent POSTs inside this process


def _path(name):
    return os.path.join(STATE_DIR, name)


def read_json(name, default):
    try:
        with open(_path(name)) as f:
            return json.load(f)
    except Exception:
        return default


def write_json(name, data):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = _path(name) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, _path(name))


def is_running():
    """True if a meeting holds the run lock (whoever started it)."""
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(_path("run.lock"), "a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(f, fcntl.LOCK_UN)
            return False
        except BlockingIOError:
            return True


def cooldown_info(now=None):
    now = now or time.time()
    cd = read_json("cooldown.json", {})
    last_start = cd.get("last_start")
    if not last_start:
        return {"last_started": None, "next_allowed_at": 0, "retry_after_s": 0}
    window = COOLDOWN_FAILED_S if cd.get("last_status") == "failed" else COOLDOWN_OK_S
    nxt = last_start + window
    return {"last_started": last_start, "next_allowed_at": nxt, "retry_after_s": max(0, int(nxt - now))}


def disabled():
    return os.path.exists(_path("DISABLED"))


def start_meeting():
    with _start_lock:
        if disabled():
            return {"status": "disabled", **cooldown_info()}
        if is_running():
            return {"status": "running", **cooldown_info()}
        cd = cooldown_info()
        if cd["retry_after_s"] > 0:
            return {"status": "cooldown", **cd}
        if not os.path.isdir(os.path.join(CLONE_DIR, "bedrock_agents")):
            print(f"❌ Bot clone not found at {CLONE_DIR}", flush=True)
            return {"status": "error", "message": "publisher clone missing"}

        now = time.time()
        # Claim the slot BEFORE spawning so a second request a millisecond later is refused.
        write_json("cooldown.json", {"last_start": now, "last_status": "running"})
        write_json("run_status.json", {"running": True, "started": now, "finished": None,
                                       "status": "running", "dry_run": False, "events": []})
        log = open(os.path.join(os.path.dirname(STATE_DIR), "meeting.log"), "a")
        log.write(f"\n===== button-triggered meeting {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
        log.flush()
        subprocess.Popen([PYTHON, "-m", "bedrock_agents.run_meeting"], cwd=CLONE_DIR, stdout=log,
                         stderr=subprocess.STDOUT, start_new_session=True)
        print(f"🚀 meeting started at {time.strftime('%H:%M:%S')}", flush=True)
        return {"status": "started", **cooldown_info()}


def current_status():
    st = read_json("run_status.json", {"running": False, "events": [], "status": "none"})
    running = is_running()
    if st.get("running") and not running:
        # The process died without writing its final state (crash / killed): report it honestly.
        st.update(running=False, status="failed", finished=st.get("finished") or time.time())
    st["running"] = running
    st["disabled"] = disabled()
    st.update(cooldown_info())
    return st


class Handler(BaseHTTPRequestHandler):
    server_version = "BedrockTrigger/1"

    def _send(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.rstrip("/") == "/run":
            try:
                return self._send(200, start_meeting())
            except Exception as e:
                print(f"❌ start_meeting error: {e}", flush=True)
                return self._send(500, {"status": "error", "message": "internal error"})
        self._send(404, {"error": "not found"})

    def do_GET(self):
        p = self.path.split("?")[0].rstrip("/")
        if p == "/status":
            return self._send(200, current_status())
        if p == "/health":
            return self._send(200, {"ok": True})
        self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        pass  # keep launchd logs to our own lines


if __name__ == "__main__":
    os.makedirs(STATE_DIR, exist_ok=True)
    print(f"Bedrock trigger listening on http://{HOST}:{PORT} (state: {STATE_DIR}, clone: {CLONE_DIR})", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
