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
        
        The Layout is FIXED. You are only updating the text.
        
        Keys required:
        - "strategy_title": Headline for the main strategy card.
        - "strategy_desc": 2 short paragraphs for the strategy description.
        
        - "risk_title": Title for Risk Analysis card.
        - "risk_desc": 1-sentence insight on risk.
        
        - "opp_title": Title for Market Opportunity card.
        - "opp_desc": 1-sentence insight on opportunity.
        
        - "insight_title": Title for Agent Insight card.
        - "insight_desc": 1-sentence insight for agents.

        Output JSON ONLY. No markdown formatted blocks.
        {
            "strategy_title": "...",
            "strategy_desc": "...",
            "risk_title": "...",
            "risk_desc": "...",
            "opp_title": "...",
            "opp_desc": "...",
            "insight_title": "...",
            "insight_desc": "..."
        }
        """
        
        response = self.client.chat(model=self.model, messages=[
            {'role': 'user', 'content': prompt}
        ])
        
        content = response['message']['content']
        
        content = response['message']['content']
        
        # 1. Extract from Markdown block if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        # 2. Parse JSON
        try:
            updates = json.loads(content)
            return updates
        except json.JSONDecodeError:
            print(f"❌ Web Developer failed to produce valid JSON: {content[:100]}...")
            # Fallback
            return {
                "strategy_title": brief.get('headline', 'Update Failed'),
                "strategy_desc": "Unable to generate content structure. System Maintenance.",
                "risk_desc": "Data stream interrupted.",
                "opp_desc": "Data stream interrupted.",
                "insight_desc": "Data stream interrupted."
            }

if __name__ == "__main__":
    dev = WebDeveloper()
    # Mock brief
    print(dev.build_page({"title": "Test", "key_points": ["A", "B"]}))
