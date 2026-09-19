"""Entry point for the Bedrock staff meeting. Runs on the M3, everything local.

    python -m bedrock_agents.run_meeting              # real run: edit page, commit, push, hot-swap
    python -m bedrock_agents.run_meeting --dry-run    # edit the working copy only; nothing pushed, no cooldown used
    python -m bedrock_agents.run_meeting --fresh      # ignore today's cached brief

Started three ways, all of which share one lock so only a single meeting runs at a time:
  * launchd, daily 06:00       (com.swaynesystems.bedrock-meeting)
  * the site's ⚡ button        (via the trigger service, bedrock_agents/trigger_server.py, max one per hour)
  * by hand from a terminal

Runs from a dedicated clone (~/bedrock-publisher/sterling-lab) so it never touches David's working tree.
State (lock, cooldown, live progress) lives in ~/bedrock-publisher/state (override: BEDROCK_STATE_DIR).
"""
import argparse
import fcntl
import json
import os
import signal
import subprocess
import sys
import time

# Local services on the M3. Must be set before bedrock_agents.config is imported.
os.environ.setdefault("OLLAMA_HOST", "http://localhost:11434")
os.environ.setdefault("COMFYUI_HOST", "http://localhost:8188")

STATE_DIR = os.environ.get("BEDROCK_STATE_DIR", os.path.expanduser("~/bedrock-publisher/state"))
MAX_RUNTIME_S = 15 * 60


def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)  # atomic: readers never see a half-written file


def sync_clone(repo_dir):
    """Reset the dedicated clone to the deploy source of truth (`live`) so a previous failed run can't leak in."""
    if os.environ.get("BEDROCK_SYNC", "1") == "0":
        return True
    remotes = subprocess.run(["git", "remote"], cwd=repo_dir, capture_output=True, text=True).stdout.split()
    if "live" not in remotes:
        print("ℹ️ No `live` remote in this clone: skipping sync.")
        return True
    for cmd in (["git", "fetch", "live"], ["git", "checkout", "-f", "main"], ["git", "reset", "--hard", "live/main"]):
        r = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True, timeout=90)
        if r.returncode != 0:
            print(f"❌ {' '.join(cmd)} failed: {r.stderr[-300:]}")
            return False
    print("🔄 Clone synced to live/main.")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="do not commit, push or hot-swap; leaves the cooldown alone")
    parser.add_argument("--fresh", action="store_true", help="delete today's cached daily briefing first")
    args = parser.parse_args()

    if args.dry_run:
        os.environ["BEDROCK_PUBLISH"] = "0"

    os.makedirs(STATE_DIR, exist_ok=True)

    # One meeting at a time, across scheduled / button / manual starts.
    lock = open(os.path.join(STATE_DIR, "run.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("⏳ A meeting is already running. Exiting.")
        return 3

    status_path = os.path.join(STATE_DIR, "run_status.json")
    cooldown_path = os.path.join(STATE_DIR, "cooldown.json")
    started = time.time()
    events = []
    state = {"running": True, "started": started, "finished": None, "status": "running",
             "dry_run": args.dry_run, "events": events}
    write_json(status_path, state)
    if not args.dry_run:
        write_json(cooldown_path, {"last_start": started, "last_status": "running"})

    def finish(status):
        state.update(running=False, finished=time.time(), status=status)
        write_json(status_path, state)
        if not args.dry_run:
            write_json(cooldown_path, {"last_start": started, "last_status": status})

    def on_timeout(signum, frame):
        raise TimeoutError(f"meeting exceeded {MAX_RUNTIME_S}s")

    signal.signal(signal.SIGALRM, on_timeout)
    signal.alarm(MAX_RUNTIME_S)

    status = "failed"
    try:
        from bedrock_agents.config import DATA_DIR, PROJECT_ROOT
        from bedrock_agents.orchestrator import run_meeting_generator

        if not args.dry_run and not sync_clone(PROJECT_ROOT):
            events.append({"agent": "error", "message": "Could not sync the repository; meeting cancelled.", "t": 0})
            return 1

        if args.fresh:
            cache = os.path.join(DATA_DIR, "daily_briefing.json")
            if os.path.exists(cache):
                os.remove(cache)
                print("🧹 Removed cached briefing.")

        print("========================================")
        print("🏢 Bedrock Insurance - Staff Meeting")
        print("========================================")
        problem = False
        for agent, message in run_meeting_generator():
            t = round(time.time() - started, 1)
            print(f"[{t:6.1f}s] [{agent.upper()}] {message}", flush=True)
            events.append({"agent": agent, "message": message, "t": t})
            write_json(status_path, state)
            if agent == "error" or "Publish FAILED" in message:
                problem = True
        status = "failed" if problem else "ok"
        return 1 if problem else 0
    except BaseException as e:  # includes the SIGALRM timeout
        print(f"❌ Meeting aborted: {e}")
        events.append({"agent": "error", "message": f"Meeting aborted: {e}", "t": round(time.time() - started, 1)})
        return 1
    finally:
        signal.alarm(0)
        finish(status)


if __name__ == "__main__":
    sys.exit(main())
