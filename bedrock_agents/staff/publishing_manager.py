import subprocess
import os
from ..config import DASHBOARD_DIR, GIT_REMOTE, GIT_BRANCH

class PublishingManager:
    def __init__(self):
        pass

    def update_website(self, html_content, theme):
        """Updates bedrock.html and pushes to git."""
        print(f"🚀 Publishing Manager is deploying update: {theme}...")
        
        # 1. Read the Template (We'll use the existing file as a base template)
        # In a real scenario, we'd use Jinja2, but for now we'll do a simple injection
        target_file = os.path.join(DASHBOARD_DIR, "bedrock", "index.html")
        
        with open(target_file, "r") as f:
            full_html = f.read()
            
        # TARGETED INJECTION: Update only the dynamic 'agent-updates' container
        # This preserves the Market Briefing widget and other layout elements
        start_marker = '<div id="agent-updates">'
        end_marker = '<!-- END DYNAMIC ZONE -->'
        
        if start_marker in full_html and end_marker in full_html:
            print("🎯 Targeting specific container: #agent-updates")
            header_part = full_html.split(start_marker)[0]
            # We want to preserve the footer (which starts at the comment)
            # split(end_marker) gives [content_before, content_after_start_of_marker] ... wait logic check
            
            # Correct logic:
            # part1 = 0 to start_marker
            # part2 = end_marker to EOF
            
            p1 = full_html.find(start_marker)
            p2 = full_html.find(end_marker)
            
            header_part = full_html[:p1]
            footer_part = full_html[p2:]
            
            # Construct new HTML: Header + Wrapper + Content + Footer
            # Note: We re-add the wrapper div because we are replacing the *entire block* between markers logic?
            # actually if split at start_marker, header doesn't include it. 
            # So we must add it back.
            
            new_full_html = f"{header_part}{start_marker}\n{html_content}\n</div>\n            {footer_part}"
        else:
            print("⚠️ Target container not found. Falling back to Main replacement.")
            header_part = full_html.split('<main class="main-content">')[0]
            footer_part = full_html.split('</main>')[1]
            html_content = html_content.replace('<main class="main-content">', '').replace("</main>", "").strip()
            new_full_html = f"{header_part}<main class=\"main-content\">\n{html_content}\n</main>{footer_part}"

        with open(target_file, "w") as f:
            f.write(new_full_html)
            
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
            subprocess.run(["git", "add", "dashboard/assets/"], cwd=repo_dir, check=False) # Add generated images
            
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

if __name__ == "__main__":
    pm = PublishingManager()
    # pm.update_website("<div>Test</div>", "Test Theme")
