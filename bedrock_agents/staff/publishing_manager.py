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
            
        # VERY Simple Template Injection (Replace <main... with new content)
        # Note: This assumes the structure created in bedrock.html initially
        # A more robust way would be to keep a separate template file.
        
        # For this MVP, let's just reconstruct the file with the new content
        # We need to preserve the header/footer
        
        header_part = full_html.split('<main class="main-content">')[0]
        footer_part = full_html.split('</main>')[1]
        
        new_full_html = f"{header_part}<main class=\"main-content\">\n{html_content}\n</main>{footer_part}"
        
        with open(target_file, "w") as f:
            f.write(new_full_html)
            
        print("✅ HTML file updated.")
        
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
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git Error: {e}")

if __name__ == "__main__":
    pm = PublishingManager()
    # pm.update_website("<div>Test</div>", "Test Theme")
