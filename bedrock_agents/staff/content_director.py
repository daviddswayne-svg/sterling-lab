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
        
        Examples of the vibe (Ensure Variety!):
        - Climate-Adaptive Architecture
        - Quantum-Encryption Liability
        - Space-Debris Property Rights
        - AI-Workforce Displacement Insurance
        - Sovereign-Individual Data HAVENs
        - Micro-Grid Energy Trading
        
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
        """Generates a professional market briefing using Real-Time Intelligence with Daily Caching."""
        
        # 1. Check for Cached Briefing (Speed Optimization)
        # The briefing only updates once per day. Caching removes the 30s RAG/LLM wait.
        cache_path = os.path.join(DATA_DIR, "daily_briefing.json")
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    cached = json.load(f)
                # Check for 'date' field or assume validity if file exists (refresh happens on failed read)
                if cached.get('date') == today_str:
                    print(f"🚀 Serving Cached Briefing from {cache_path}")
                    return cached
            except Exception as e:
                print(f"⚠️ Cache read failed: {e}")

        # 2. Generate Fresh Briefing (The Slow Part)
        print("🧠 Content Director initializing fresh generation...")
        
        try:
            # Lazy import to avoid circular dependency
            from ..market_intel import MarketIntelligence
            
            intel = MarketIntelligence()
            print(f"🧠 Content Director ({self.model}) is gathering market intelligence...")
            
            # Gather all data
            context_data = intel.get_full_briefing_context()
            
            market_str = "\n".join([f"- {t}: ${d['price']} ({d['change_pct']}%) [Vol: {d['volatility_30d']}%]" for t, d in context_data['market_data'].items()])
            news_str = "\n".join([f"- {h}" for h in context_data['news_headlines']])
            
            prompt = f"""
            {self.prompts['system_prompt']}
            DATE: {datetime.now().strftime("%Y-%m-%d %H:%M")}
            
            === MARKET INTELLIGENCE STREAM ===
            HARD DATA (Live Tickers):
            {market_str}
            
            LATEST NEWS WIRES:
            {news_str}
            
            DEEP INSIGHT (Swiss Re Sigma Report 2025 Outlook):
            "{context_data['sigma_report_context']}"
            
            === INSTRUCTION ===
            You are the Chief Market Analyst for Bedrock Insurance.
            Write a "Morning Briefing" for our high-net-worth protection agents.
            
            GUIDELINES:
            1. Synthesize the Hard Data and News into a cohesive narrative.
            2. CRITICAL: Explicitly cite the "Swiss Re Sigma Report" for the long-term outlook.
            3. Tone: Bloomberg Terminal meets Architectural Digest. Sophisticated, urgent, yet reassuring.
            4. Focus on "Risk Landscape" and "Asset Resilience".
            
            Output a JSON object with this EXACT structure:
            {{
                "headline": "Punchy, 5-7 word title",
                "market_sentiment": "One word (e.g., Volatile, Cautious, Bullish)",
                "briefing_body": "The main paragraph (approx 100-150 words). Use HTML <b> tags for emphasis on key numbers.",
                "date": "{today_str}"
            }}
            """
            
            print(f"   💡 Synthesizing brief with Real-Time Data...")
            
            response = self.client.chat(model=self.model, format='json', messages=[
                {'role': 'user', 'content': prompt}
            ])
            
            content = response['message']['content']
            briefing = json.loads(content)
            
            # Ensure date is set
            briefing['date'] = today_str
            
            # 3. Save to Cache
            try:
                with open(cache_path, 'w') as f:
                    json.dump(briefing, f, indent=4)
                print(f"💾 Saved fresh briefing to {cache_path}")
            except Exception as e:
                print(f"⚠️ Failed to write cache: {e}")
                
            return briefing

        except Exception as e:
            print(f"❌ Content Director Error: {e}")
            # Reraise so the API fallback handles it, 
            # OR return the fallback detailed here. 
            # Given we have API fallback, raising is fine.
            raise e

if __name__ == "__main__":
    director = ContentDirector()
    brief = director.create_daily_brief()
    print(json.dumps(brief, indent=2))
