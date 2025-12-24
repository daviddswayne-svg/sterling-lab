import subprocess
import os
import re
import json
from ..config import DASHBOARD_DIR, GIT_REMOTE, GIT_BRANCH

class PublishingManager:
    def __init__(self):
        pass

    def update_website(self, content_updates, theme):
        """Updates bedrock.html text content and pushes to git."""
        print(f"🚀 Publishing Manager is deploying update: {theme}...")
        
        target_file = os.path.join(DASHBOARD_DIR, "bedrock", "index.html")
        
        try:
            with open(target_file, "r") as f:
                full_html = f.read()

            # Prepare ID map
            id_map = {
                "strategy_title": "strategy-title",
                "strategy_desc": "strategy-desc",
                "risk_title": "risk-title",
                "risk_desc": "risk-desc",
                "opp_title": "opp-title",
                "opp_desc": "opp-desc",
                "insight_title": "insight-title",
                "insight_desc": "insight-desc"
            }

            if isinstance(content_updates, dict):
                print("🎯 Performing Surgical Text Updates (BS4 Layout-Agnostic)...")
                
                # Use BeautifulSoup for robust HTML parsing
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(full_html, 'html.parser')
                    
                    changes_count = 0
                    
                    for key, new_text in content_updates.items():
                        target_id = id_map.get(key)
                        if target_id:
                            element = soup.find(id=target_id)
                            if element:
                                # Update text content while preserving any potential nested tags if we wanted,
                                # but here we are replacing content.
                                element.string = new_text
                                print(f"   ✅ Updated #{target_id}")
                                changes_count += 1
                            else:
                                print(f"   ⚠️ ID #{target_id} not found in HTML.")
                        else:
                             print(f"   ⚠️ Key '{key}' ignored (No ID mapping).")
                    
                    if changes_count > 0:
                        # Convert back to string (formatter=None prevents escaping like &lt;)
                        full_html = str(soup)
                    else:
                        print("⚠️ No changes made to HTML structure.")
                        
                except ImportError:
                    print("❌ BeautifulSoup4 not installed. Falling back to Regex (Risky).")
                    # Fallback Regex Logic (Legacy)
                    for key, new_text in content_updates.items():
                        if key in id_map:
                             html_id = id_map[key]
                             pattern = f'(id="{html_id}"[^>]*>)(.*?)(</)'
                             if re.search(pattern, full_html, re.DOTALL):
                                 full_html = re.sub(pattern, f'\\1{new_text}\\3', full_html, flags=re.DOTALL)
            else:
                print("⚠️ Received raw string instead of updates dict. Aborting.")
                return

            with open(target_file, "w") as f:
                f.write(full_html)
                
            print("✅ HTML file updated.")
            
            # Check if running in Docker container
            is_container = os.path.exists('/.dockerenv')
            
            if is_container:
                print("🐳 Running in container. Skipping Git Push/Hot-Swap (Changes applied locally).")
                return

            # 2. Git Operations
            try:
                repo_dir = os.path.dirname(DASHBOARD_DIR)
                
                # Pull first
                subprocess.run(["git", "pull", "origin", GIT_BRANCH], cwd=repo_dir, check=False)
                
                # Add
                subprocess.run(["git", "add", "dashboard/bedrock/index.html"], cwd=repo_dir, check=True)
                
                # Commit
                subprocess.run(["git", "commit", "-m", f"Bedrock Insurance Auto-Update: {theme}"], cwd=repo_dir, check=True)
                
                # Push to LIVE (Deploy)
                print(f"📡 Pushing to {GIT_REMOTE}...")
                subprocess.run(["git", "push", GIT_REMOTE, GIT_BRANCH], cwd=repo_dir, check=True)
                
                # Push to Origin (Backup)
                print("💾 Backing up to origin...")
                subprocess.run(["git", "push", "origin", GIT_BRANCH], cwd=repo_dir, check=False)
                
                print("🎉 Deployment Triggered Successfully!")
                
                # 3. Hot-Swap (Instant Update)
                print("🔥 Executing Hot-Swap for instant validation...")
                subprocess.run(["./hot_swap.sh"], cwd=repo_dir, check=False)
                
            except subprocess.CalledProcessError as e:
                print(f"❌ Git Error: {e}")

        except Exception as e:
            print(f"❌ Publishing Error: {e}")

if __name__ == "__main__":
    pm = PublishingManager()
    # Mock update
    # pm.update_website({"risk_title": "New Risk"}, "Test Theme")
