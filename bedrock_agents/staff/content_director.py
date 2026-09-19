import json
import os
from .. import llm
from datetime import datetime
from ..config import MODELS, DATA_DIR, PROMPTS_PATH

class ContentDirector:
    def __init__(self):
        self.model = MODELS["director"]
        
        # Load external prompts
        with open(PROMPTS_PATH, "r") as f:
            self.prompts = json.load(f)["content_director"]

    def _consult_trend_scout(self):
        """Uses a different, more 'wild' model to generate lateral thinking concepts."""
        scout_model = MODELS["director"]  # same warm model as every other stage; creativity comes from temperature
        
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
            response = llm.chat(model=scout_model, options={'temperature': 1.1}, messages=[
                {'role': 'user', 'content': prompt}
            ])
            concept = response['message']['content'].strip()
            return concept
        except Exception as e:
            print(f"⚠️ Trend Scout failed: {e}. Falling back to random spark.")
            import random
            return random.choice(["Cyber-Physical Security", "Climate-Resilient Living", "Asset-Tokenization"])

    def create_daily_brief(self, use_cache=True):
        """Generates a professional market briefing using Real-Time Intelligence with Daily Caching."""
        
        # 1. Check for Cached Briefing (Speed Optimization)
        # The briefing only updates once per day. Caching removes the 30s RAG/LLM wait.
        cache_path = os.path.join(DATA_DIR, "daily_briefing.json")
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        if use_cache and os.path.exists(cache_path):
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
            
            from ..market_stats import _vix_label
            from ..sigma_report import cite_names, format_for_prompt
            sigma = context_data.get('sigma') or {}
            sigma_block = format_for_prompt(sigma)
            names = cite_names(sigma)
            cite_rule = (f'Explicitly cite at least one of these by name for the outlook: {"; ".join(names)}. Use only the quoted findings listed above.'
                         if names else 'Do NOT cite Swiss Re or any report; none could be read this run.')
            market_str = "\n".join([
                f"- {t}: {d['price']} ({d['change_pct']:+}% today, {d['return_1m_pct']:+}% over 1 month)"
                + (f" -> market volatility is {_vix_label(d['price'])}" if t == "^VIX" else "")
                for t, d in context_data['market_data'].items()]) or "- (market data unavailable this run)"
            macro = context_data.get('macro') or {}
            if macro.get('cpi_yoy') is not None:
                market_str += f"\n- US CPI inflation (year over year): {macro['cpi_yoy']}% (previous month: {macro.get('cpi_yoy_prev')}%)"
            news_str = "\n".join([f"- {h}" for h in context_data['news_headlines']]) or "- (no news feed available this run)"
            
            prompt = f"""
            {self.prompts['system_prompt']}
            DATE: {datetime.now().strftime("%Y-%m-%d %H:%M")}
            
            === MARKET INTELLIGENCE STREAM ===
            HARD DATA (Live Tickers):
            {market_str}
            
            LATEST NEWS WIRES:
            {news_str}
            
            DEEP INSIGHT (current Swiss Re Institute publications, read by this system):
            {sigma_block}
            
            === INSTRUCTION ===
            You are the Chief Market Analyst for Bedrock Insurance.
            Write a "Morning Briefing" for our high-net-worth protection agents.
            
            GUIDELINES:
            1. Synthesize the Hard Data and News into a cohesive narrative.
            2. CRITICAL: {cite_rule}
            3. Tone: Bloomberg Terminal meets Architectural Digest. Sophisticated, urgent, yet reassuring.
            4. Focus on "Risk Landscape" and "Asset Resilience".
            5. Use ONLY the numbers listed above. Never invent a figure, price or statistic; if a number is not listed, describe the trend in words instead.
            6. Name instruments in plain words (S&P 500, VIX, 10-year Treasury yield); never write ticker symbols such as ^VIX or ^TNX.
            
            Output a JSON object with this EXACT structure:
            {{
                "headline": "Punchy, 5-7 word title",
                "market_sentiment": "One word (e.g., Volatile, Cautious, Bullish)",
                "briefing_body": "The main paragraph (approx 100-150 words). Use HTML <b> tags for emphasis on key numbers.",
                "date": "{today_str}"
            }}
            """
            
            print(f"   💡 Synthesizing brief with Real-Time Data...")
            
            response = llm.chat(model=self.model, format='json', messages=[
                {'role': 'user', 'content': prompt}
            ])
            
            content = response['message']['content']
            briefing = json.loads(content)
            
            # Ensure date is set
            briefing['date'] = today_str
            
            # Attach Raw Data for downstream agents (Web Developer)
            briefing['raw_market_data'] = context_data['market_data']
            briefing['macro'] = macro
            good = [s for s in (sigma.get('sources') or []) if s['ok']]
            briefing['sigma'] = [{k: s.get(k) for k in ('short', 'label', 'title', 'published', 'url')} for s in good] or None
            briefing['source'] = ' • '.join(filter(None, [
                *[s['short'] for s in good],
                'Yahoo Finance' if context_data['market_data'] else None,
                'FRED' if macro.get('cpi_yoy') is not None else None,
                'Insurance Journal, CNBC' if context_data['news_headlines'] else None]))
            
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
