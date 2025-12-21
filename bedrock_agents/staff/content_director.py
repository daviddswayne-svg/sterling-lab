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

    def _consult_trend_scout(self):
        """Uses a different, more 'wild' model to generate lateral thinking concepts."""
        scout_model = "dolphin-llama3" # Using Dolphin for its creativity/unfiltered nature
        
        prompt = """
        Generate ONE provocative, futuristic, or unexpected concept that relates to 'Protection', 'Assets', or 'Lifestyle'.
        
        Examples of the vibe:
        - Digital Afterlife Management
        - Drone-Defense Skies
        - Nomad-Capitalism
        - Bio-metric Fortresses
        
        Return ONLY the concept name, nothing else. No explanation.
        """
        
        try:
            print(f"📡 Pinging Trend Scout ({scout_model}) for a wild idea...")
            response = self.client.chat(model=scout_model, messages=[
                {'role': 'user', 'content': prompt}
            ])
            concept = response['message']['content'].strip()
            return concept
        except Exception as e:
            print(f"⚠️ Trend Scout failed: {e}. Falling back to random spark.")
            import random
            return random.choice(["Cyber-Physical Security", "Climate-Resilient Living", "Asset-Tokenization"])

    def create_daily_brief(self):
        """Generates a creative brief using multi-agent brainstorming."""
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        time_str = datetime.now().strftime("%H:%M:%S")
        
        # Step 1: Get a wild idea from the Trend Scout
        wild_concept = self._consult_trend_scout()
        
        prompt = f"""
        {self.prompts['system_prompt']}
        Today's date is {date_str} at {time_str}.
        
        INPUT FROM TREND SCOUT: "{wild_concept}"
        
        INSTRUCTION: 
        1. We are brainstorming with a futurist consultant (the Trend Scout).
        2. Take their wild concept: "{wild_concept}"
        3. GROUND IT into a sophisticated, high-end insurance marketing theme for Bedrock.
        4. Example: If input is "Digital Afterlife", theme could be "Legacy Conservation for the Digital Age".
        
        Your goal is to show we are ahead of the curve.
        
        Return a JSON object with this EXACT structure:
        {json.dumps(self.prompts['output_format'], indent=4)}
        """
        
        print(f"🧠 Content Director ({self.model}) is digesting the scout's idea...")
        print(f"   💡 Converting '{wild_concept}' into a campaign strategy...")
        
        response = self.client.chat(model=self.model, format='json', messages=[
            {'role': 'user', 'content': prompt}
        ])
        
        content = response['message']['content']
        return json.loads(content)

if __name__ == "__main__":
    director = ContentDirector()
    brief = director.create_daily_brief()
    print(json.dumps(brief, indent=2))
