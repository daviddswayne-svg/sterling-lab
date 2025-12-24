
import re

full_html = """
                    <!-- 3. Strategy Zone (Bottom) -->
                    <div class="bento-strategy card-glow">
                        <h2 class="hero-title" id="strategy-title">Safe Haven</h2>
                        <div class="hero-description" id="strategy-desc">
                            Discover advanced home protection strategies tailored for suburban homeowners.
                            Implement smart security, understand flood insurance, and enhance safety through landscape
                            design.
                        </div>
                        <div class="cta-row">
"""

id_map = {
    "strategy_title": "strategy-title",
    "strategy_desc": "strategy-desc"
}

content_updates = {
    "strategy_title": "TEST STRATEGY TITLE",
    "strategy_desc": "Test Description Update."
}

print("--- START DEBUG ---")

for key, new_text in content_updates.items():
    if key in id_map:
        html_id = id_map[key]
        print(f"Testing ID: {html_id}")
        
        # Original Pattern from PublishingManager
        pattern = f'(id="{html_id}"[^>]*>)(.*?)(</)'
        
        match = re.search(pattern, full_html, re.DOTALL)
        if match:
             print(f"✅ Match Found for {html_id}")
             print(f"   Group 1 (Tag): {match.group(1)}")
             print(f"   Group 2 (Old Content): {match.group(2)}")
             print(f"   Group 3 (Close): {match.group(3)}")
             
             updated = re.sub(pattern, f'\\1{new_text}\\3', full_html, flags=re.DOTALL)
             # print(updated)
        else:
             print(f"❌ No Match for {html_id}")
             
print("--- END DEBUG ---")
