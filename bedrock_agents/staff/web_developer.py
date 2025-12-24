import ollama
import json
import os
from ..config import OLLAMA_HOST, MODELS, PROMPTS_PATH
from ..config import DATA_DIR # Keep if used elsewhere, but prompts uses specific path now

class WebDeveloper:
    def __init__(self):
        self.client = ollama.Client(host=OLLAMA_HOST)
        self.model = MODELS["writer"]
        
        # Load external prompts
        with open(PROMPTS_PATH, "r") as f:
            self.prompts = json.load(f)["web_developer"]

    def build_page(self, brief, image_path=None):
        """Generates HTML content based on the creative brief."""
        print(f"👨‍💻 Web Developer ({self.model}) is building the page '{brief.get('headline', 'Update')}'...")
        
        # Build CSS rules list
        css_list = "\n        - ".join(self.prompts["css_rules"])
        
        # Image is now embedded in the strict template below
        pass

        # Extract Raw Market Data if available works
        market_stats = ""
        if "raw_market_data" in brief:
             raw = brief["raw_market_data"]
             # Format specific keys we care about
             spy = raw.get("SPY", {"price": "N/A", "change_pct": "0.0"})
             vix = raw.get("^VIX", {"price": "N/A", "change_pct": "0.0"})
             market_stats = f"""
             REAL-TIME DATA (Use these EXACT stats):
             - S&P 500 (SPY): ${spy['price']} ({spy['change_pct']}%)
             - Volatility (VIX): {vix['price']} (Change: {vix['change_pct']}%)
             """

        prompt = f"""
        {self.prompts['system_prompt']}
        
        {market_stats}

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
        - market_inflation (e.g. "+3.2% ▲")
        - market_risk (e.g. "ELEVATED")
        - market_yield (e.g. "4.12%")
        - market_sector (e.g. "POSITIVE")
        - market_sp500 (e.g. "+1.2% $500.12")
        - market_volatility (e.g. "15.4 (LOW)")
        - market_outlook (e.g. "STABLE")

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
        
        response = self.client.chat(model=self.model, messages=[
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
            return updates
        else:
            print("❌ Web Developer failed to produce valid blocks. Raw content:")
            print(content[:200])
             # Fallback
            return {
                "strategy_title": brief.get('headline', 'Update Failed'),
                "strategy_desc": "Unable to generate content structure. System Maintenance.",
            }

if __name__ == "__main__":
    dev = WebDeveloper()
    # Mock brief
    print(dev.build_page({"title": "Test", "key_points": ["A", "B"]}))
