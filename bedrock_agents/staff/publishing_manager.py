import subprocess
import os
import re
import json
from ..config import DASHBOARD_DIR, GIT_REMOTE, GIT_BRANCH

# Element IDs on dashboard/bedrock/index.html that the staff meeting rewrites.
ID_MAP = {
    "strategy_title": "strategy-title",
    "strategy_desc": "strategy-desc",
    "risk_title": "risk-title",
    "risk_desc": "risk-desc",
    "opp_title": "opp-title",
    "opp_desc": "opp-desc",
    "insight_title": "insight-title",
    "insight_desc": "insight-desc",
    "market_inflation": "market-inflation-val",
    "market_risk": "market-risk-val",
    "market_yield": "market-yield-val",
    "market_sector": "market-sector-val",
    "market_sp500": "market-sp500-val",
    "market_volatility": "market-volatility-val",
    "market_outlook": "market-outlook-val",
}


class PublishingManager:
    """Two steps: apply_updates() edits the page on disk; publish() commits, pushes and hot-swaps."""

    def apply_updates(self, content_updates, theme):
        """Surgically rewrites text nodes and the hero image in bedrock/index.html. Returns number of changes."""
        print(f"🚀 Publishing Manager is applying update: {theme}...")
        target_file = os.path.join(DASHBOARD_DIR, "bedrock", "index.html")

        if not isinstance(content_updates, dict):
            print("⚠️ Received non-dict updates. Aborting.")
            return 0

        with open(target_file, "r") as f:
            full_html = f.read()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(full_html, "html.parser")
        changes = 0

        for key, new_text in content_updates.items():
            if key == "hero_image":
                element = soup.find(id="hero-image")
                if element:
                    element["src"] = new_text
                    element["style"] = "display: block;"
                    print(f"   🎬 Hero image -> {new_text}")
                    changes += 1
                else:
                    print("   ⚠️ #hero-image not found in HTML.")
                continue

            target_id = ID_MAP.get(key)
            if not target_id:
                print(f"   ⚠️ Key '{key}' ignored (no ID mapping).")
                continue
            element = soup.find(id=target_id)
            if element is None:
                print(f"   ⚠️ ID #{target_id} not found in HTML.")
                continue
            element.string = new_text
            print(f"   ✅ Updated #{target_id}")
            changes += 1

        if changes:
            with open(target_file, "w") as f:
                f.write(str(soup))
            print(f"✅ HTML updated ({changes} changes).")
        else:
            print("⚠️ No changes made to HTML structure.")
        return changes

    def publish(self, theme):
        """Commit only the Bedrock files, push to live + origin, then hot-swap into the running container.

        Runs on the M3 from a dedicated clone (never David's working tree). Returns True on success.
        Never runs inside the site container (its filesystem is ephemeral and has no git remote).
        """
        if os.path.exists("/.dockerenv"):
            print("🐳 Running in a container: not publishing (changes would vanish on redeploy).")
            return False

        repo_dir = os.path.dirname(DASHBOARD_DIR)

        def git(*args, check=True):
            return subprocess.run(["git", *args], cwd=repo_dir, check=check, capture_output=True, text=True)

        try:
            git("add", "dashboard/bedrock/index.html", "dashboard/bedrock/meeting_latest.json")
            git("add", "-A", "--", "dashboard/assets/bedrock_*.png")
            if git("diff", "--cached", "--quiet", check=False).returncode == 0:
                print("ℹ️ Nothing to commit.")
                return True
            git("commit", "-m", f"Bedrock Insurance Auto-Update: {theme}")
            print("📝 Committed.")

            # Someone else may have pushed while the meeting ran; rebase our one commit on top.
            # `live` (the deploy source) is the source of truth, not `origin` (GitHub backup).
            pull = git("pull", "--rebase", GIT_REMOTE, GIT_BRANCH, check=False)
            if pull.returncode != 0:
                git("rebase", "--abort", check=False)
                print(f"❌ Rebase failed, leaving the commit local for a human to resolve:\n{pull.stderr[-400:]}")
                return False

            print(f"📡 Pushing to {GIT_REMOTE} (deploy source)...")
            git("push", GIT_REMOTE, GIT_BRANCH)
            print("💾 Backing up to origin...")
            git("push", "origin", GIT_BRANCH, check=False)

            print("🔥 Hot-swapping into the running site container...")
            swap = subprocess.run(["./hot_swap.sh", "--bedrock"], cwd=repo_dir, capture_output=True, text=True)
            print(swap.stdout[-600:])
            if swap.returncode != 0:
                print(f"⚠️ Hot-swap failed (the site updates on the next Coolify redeploy): {swap.stderr[-300:]}")
                return False
            print("🎉 Published.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Git error: {e}\n{(e.stderr or '')[-400:]}")
            return False
