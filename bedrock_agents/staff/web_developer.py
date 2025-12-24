import ollama
import json
import os
from ..config import OLLAMA_HOST, MODELS, DATA_DIR

class WebDeveloper:
    def __init__(self):
        self.client = ollama.Client(host=OLLAMA_HOST)
        self.model = MODELS["writer"]
        
        # Load external prompts
        prompts_path = os.path.join(DATA_DIR, "prompts.json")
        with open(prompts_path, "r") as f:
            self.prompts = json.load(f)["web_developer"]

    def build_page(self, brief, image_path=None):
        """Generates HTML content based on the creative brief."""
        print(f"👨‍💻 Web Developer ({self.model}) is building the page '{brief.get('headline', 'Update')}'...")
        
        # Build CSS rules list
        css_list = "\n        - ".join(self.prompts["css_rules"])
        
        # Image is now embedded in the strict template below
        pass

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

        Example Output:
        ===SECTION: strategy_title===
        Coastal Resilience Strategy
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
