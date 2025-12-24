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
        
        CRITICAL LAYOUT INSTRUCTION: "Split Command Center"
        You MUST generate a single <section> with a 2-column grid layout.
        
        HTML Structure:
        <section class="hero-card card-glow" style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; align-items: start;">
            
            <!-- LEFT COLUMN: VISUAL -->
            <div class="visual-col">
                 <img src='{image_path}' class='hero-image' style="width: 100%; height: auto; border-radius: 8px; object-fit: cover; aspect-ratio: 1/1;">
            </div>
            
            <!-- RIGHT COLUMN: INTELLIGENCE -->
            <div class="content-col" style="display: flex; flex-direction: column; gap: 1rem;">
                <h2 class="hero-title">{brief.get('headline', 'Market Update')}</h2>
                <div class="hero-description">
                   [Write 2 short, punchy paragraphs based on the Brief. Focus on risk and opportunity.]
                </div>
                
                <!-- DATA GRID (Compact) -->
                <div class="data-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem;">
                    <div class="data-card" style="background: rgba(255,255,255,0.05); padding: 0.5rem; border-radius: 6px; border: 1px solid rgba(74, 144, 226, 0.2);">
                        <h4 style="color: #4a90e2; margin: 0 0 0.5rem 0; font-size: 0.7rem;">INFLATION VECTOR</h4>
                        <img src="/assets/inflation_chart.png" style="width: 100%; border-radius: 4px;">
                    </div>
                    <div class="data-card" style="background: rgba(255,255,255,0.05); padding: 0.5rem; border-radius: 6px; border: 1px solid rgba(0, 230, 118, 0.2);">
                        <h4 style="color: #00e676; margin: 0 0 0.5rem 0; font-size: 0.7rem;">CLIMATE RISK</h4>
                        <img src="/assets/storm_chart.png" style="width: 100%; border-radius: 4px;">
                    </div>
                </div>
                
                <div class="cta-row" style="margin-top: 1rem;">
                    <button class="cta-button" onclick="openInsuranceChat()">Get a Quote</button>
                    <button class="cta-button secondary-cta">Contact Advisor</button>
                </div>
            </div>
            
        </section>

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
