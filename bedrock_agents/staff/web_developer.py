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
        
        {image_html}
        
        You must use the following CSS classes from our design system:
        - {css_list}
        
        Output ONLY the HTML content to be injected into the dynamic update zone.
        
        Output ONLY the HTML content.
        
        CRITICAL LAYOUT INSTRUCTION: "Bento Grid Content Filling"
        You are NOT building the layout. The CSS Grid is already set.
        You must output the content for the 3 slots:
        
        <div class="bento-grid">
            <!-- SLOT 1: VISUAL (Top Left) -->
            <div class="bento-visual card-glow">
                 <img src='{image_path}' alt='Visual Analysis'>
            </div>
            
            <!-- SLOT 2: DATA (Top Right) -->
            <div class="bento-data">
                <div class="data-card">
                    <h4>Inflation Vector</h4>
                    <img src="/assets/inflation_chart.png">
                </div>
                <div class="data-card">
                    <h4>Climate Risk</h4>
                    <img src="/assets/storm_chart.png">
                </div>
            </div>
            
            <!-- SLOT 3: STRATEGY (Bottom Full) -->
            <div class="bento-strategy card-glow">
                <h2 class="hero-title">{brief.get('headline', 'Market Update')}</h2>
                <div class="hero-description">
                   [Write 2 short, punchy paragraphs based on the Brief. Focus on risk and opportunity.]
                </div>
                <div class="cta-row">
                    <button class="cta-button" onclick="openInsuranceChat()">Get a Quote</button>
                    <button class="cta-button secondary-cta">Contact Advisor</button>
                </div>
            </div>
        </div>

        Do NOT output <html>, <head>, <body>, or <main> tags.
        Do NOT wrap in markdown code blocks.
        """
        
        response = self.client.chat(model=self.model, messages=[
            {'role': 'user', 'content': prompt}
        ])
        
        content = response['message']['content']
        
        # 1. Extract from Markdown block if present
        if "```html" in content:
            content = content.split("```html")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        # 2. Heuristic Cleanup (Remove conversational filler if no markdown)
        # Find first < and last >
        start_idx = content.find("<")
        end_idx = content.rfind(">")
        
        if start_idx != -1 and end_idx != -1:
            content = content[start_idx:end_idx+1]
            
        # 3. Security: Remove <html>, <head>, <body> tags if included despite prompt
        content = content.replace("<!DOCTYPE html>", "").replace("<html>", "").replace("</html>", "")
        content = content.replace("<head>", "").replace("</head>", "")
        content = content.replace("<body>", "").replace("</body>", "")
            
        return content

if __name__ == "__main__":
    dev = WebDeveloper()
    # Mock brief
    print(dev.build_page({"title": "Test", "key_points": ["A", "B"]}))
