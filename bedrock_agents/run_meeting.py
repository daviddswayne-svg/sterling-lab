"""Entry point for the daily Bedrock staff meeting. Runs on the M3, everything local.

    python -m bedrock_agents.run_meeting              # full run: edit page, commit, push, hot-swap
    python -m bedrock_agents.run_meeting --dry-run    # edit the working copy only; nothing pushed
    python -m bedrock_agents.run_meeting --fresh      # ignore today's cached brief

Scheduled by ~/Library/LaunchAgents/com.swaynesystems.bedrock-meeting.plist from a dedicated clone
(~/bedrock-publisher/sterling-lab) so it never touches David's working tree.
"""
import argparse
import os
import sys

# Local services on the M3. Must be set before bedrock_agents.config is imported.
os.environ.setdefault("OLLAMA_HOST", "http://localhost:11434")
os.environ.setdefault("COMFYUI_HOST", "http://localhost:8188")

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--dry-run", action="store_true", help="do not commit, push or hot-swap")
parser.add_argument("--fresh", action="store_true", help="delete today's cached daily briefing first")
args = parser.parse_args()

if args.dry_run:
    os.environ["BEDROCK_PUBLISH"] = "0"

from bedrock_agents.config import DATA_DIR  # noqa: E402
from bedrock_agents.orchestrator import main  # noqa: E402

if args.fresh:
    cache = os.path.join(DATA_DIR, "daily_briefing.json")
    if os.path.exists(cache):
        os.remove(cache)
        print("🧹 Removed cached briefing.")

if __name__ == "__main__":
    main()
    sys.exit(0)
