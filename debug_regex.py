
import os
import re

# Mock DASHBOARD_DIR
DASHBOARD_DIR = "/Users/daviddswayne/.gemini/antigravity/scratch/sterling_lab/dashboard"

def debug_update():
    target_file = os.path.join(DASHBOARD_DIR, "bedrock", "index.html")
    
    with open(target_file, "r") as f:
        full_html = f.read()
    
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
    
    content_updates = {
        "strategy_title": "TEST STRATEGY",
        "risk_title": "TEST RISK",
        "risk_desc": "This is a test description inserted by the debugger."
    }
    
    print(f"Read HTML of size: {len(full_html)}")
    
    for key, new_text in content_updates.items():
        if key in id_map:
            html_id = id_map[key]
            pattern = f'(id="{html_id}"[^>]*>)(.*?)(</)'
            
            print(f"Testing ID: {html_id}")
            match = re.search(pattern, full_html, re.DOTALL)
            if match:
                print(f"✅ Match found: {match.group(0)}")
                full_html = re.sub(pattern, f'\\1{new_text}\\3', full_html, flags=re.DOTALL)
                print("✅ Replacement executed")
            else:
                print(f"❌ Match NOT found for {html_id}")

    print("Debug run complete.")

if __name__ == "__main__":
    debug_update()
