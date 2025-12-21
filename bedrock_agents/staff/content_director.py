import json
import os
import ollama
from datetime import datetime
from ..config import OLLAMA_HOST, MODELS, DATA_DIR

class ContentDirector:
    def __init__(self):
        self.client = ollama.Client(host=OLLAMA_HOST)
        self.model = MODELS["director"]
        
        # Load external prompts
        prompts_path = os.path.join(DATA_DIR, "prompts.json")
        with open(prompts_path, "r") as f:
            self.prompts = json.load(f)["content_director"]

    def create_daily_brief(self):
        """Generates a creative brief for the day's insurance content."""
        import random
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%H:%M:%S")
        
        # Randomly select a theme to force variety
        selected_theme = random.choice(self.prompts["themes"])
        
        # Build list of all themes for context
        themes_list = "\n        - ".join(self.prompts["themes"])
        
        prompt = f"""
        {self.prompts['system_prompt']}
        Today's date is {date_str} at {time_str}.
        
        ASSIGNED THEME (you MUST use this): {selected_theme}
        
        All available themes (for context):
        - {themes_list}
        
        CRITICAL: Generate completely UNIQUE content. Do not reuse phrases, headlines, or descriptions from previous outputs. Think of fresh angles and new vocabulary.
        
        Return a JSON object with this EXACT structure:
        {json.dumps(self.prompts['output_format'], indent=4)}
        """
        
        print(f"🧠 Content Director ({self.model}) is planning content for {date_str}...")
        print(f"   📌 Assigned Theme: {selected_theme}")
        
        response = self.client.chat(model=self.model, format='json', messages=[
            {'role': 'user', 'content': prompt}
        ])
        
        content = response['message']['content']
        return json.loads(content)

if __name__ == "__main__":
    director = ContentDirector()
    brief = director.create_daily_brief()
    print(json.dumps(brief, indent=2))
