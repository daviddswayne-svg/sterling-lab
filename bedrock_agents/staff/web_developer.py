from .. import llm
import json
import os
from ..config import MODELS, PROMPTS_PATH
from ..config import DATA_DIR # Keep if used elsewhere, but prompts uses specific path now

class WebDeveloper:
    def __init__(self):
        self.model = MODELS["writer"]
        
        # Load external prompts
        with open(PROMPTS_PATH, "r") as f:
            self.prompts = json.load(f)["web_developer"]

    RISK_WORDS = {"LOW", "MODERATE", "ELEVATED", "SEVERE"}
    OUTLOOK_WORDS = {"STABLE", "CAUTIOUS", "POSITIVE", "NEGATIVE"}

    def _finalize(self, updates, brief, image_path):
        """Overlay computed market tiles, constrain the model's two labels, attach the hero image."""
        from ..market_stats import compute_market_stats, MISSING
        updates.update(compute_market_stats(brief.get("raw_market_data"), brief.get("macro")))
        risk = updates.get("market_risk", "").strip().upper()
        outlook = updates.get("market_outlook", "").strip().upper()
        updates["market_risk"] = risk if risk in self.RISK_WORDS else MISSING
        updates["market_outlook"] = outlook if outlook in self.OUTLOOK_WORDS else MISSING
        if image_path:
            updates["hero_image"] = image_path
        return updates

    def build_page(self, brief, image_path=None):
        """Generates HTML content based on the creative brief."""
        print(f"👨‍💻 Web Developer ({self.model}) is building the page '{brief.get('headline', 'Update')}'...")
        
        # Build CSS rules list
        css_list = "\n        - ".join(self.prompts["css_rules"])
        
        # Image is now embedded in the strict template below
        pass

        # Market tiles (S&P, VIX, yield, CPI, sector) are computed from real data in market_stats.py,
        # never written by the model.

        prompt = f"""
        {self.prompts['system_prompt']}
        
        Brief:
        {brief}
        
        Output a JSON object mapping element IDs to their new text content.
        
        Output format must be STRICT DELIMITER BLOCKS.
        Do NOT use JSON. Do NOT use Markdown.
        
        Format:
        ===SECTION: key_name===
        Content goes here...
        ===END===

        Keys required:
        - strategy_title
        - strategy_desc
        - risk_title
        - risk_desc
        - opp_title
        - opp_desc
        - insight_title
        - insight_desc
        - market_risk (exactly one word: LOW, MODERATE, ELEVATED or SEVERE)
        - market_outlook (exactly one word: STABLE, CAUTIOUS, POSITIVE or NEGATIVE)

        Example Output:
        ===SECTION: strategy_title===
        Coastal Resilience Strategy
        ===END===
        ===SECTION: market_risk===
        SEVERE
        ===END===
        ===SECTION: strategy_desc===
        Focus on flood mitigation and green infrastructure.
        ===END===
        """
        
        response = llm.chat(model=self.model, messages=[
            {'role': 'user', 'content': prompt}
        ])
        
        content = response['message']['content']
        

        # Parse Delimiter Blocks
        import re
        updates = {}
        
        # Regex to capture content between ===SECTION: key=== and ===END===
        # Flags: DOTALL (dot matches newline)
        pattern = r"===SECTION:\s*(\w+)===(.*?)===END==="
        matches = re.findall(pattern, content, re.DOTALL)
        
        if matches:
            for key, val in matches:
                updates[key.strip()] = val.strip()
            return self._finalize(updates, brief, image_path)
        else:
            print("❌ Web Developer failed to produce valid blocks. Raw content:")
            print(content[:200])
             # Fallback
            return self._finalize({
                "strategy_title": brief.get('headline', 'Update Failed'),
                "strategy_desc": "Unable to generate content structure. System Maintenance.",
            }, brief, image_path)

if __name__ == "__main__":
    dev = WebDeveloper()
    # Mock brief
    print(dev.build_page({"title": "Test", "key_points": ["A", "B"]}))
