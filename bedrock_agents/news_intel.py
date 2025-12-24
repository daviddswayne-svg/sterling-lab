import feedparser
import random
from datetime import datetime
from ollama import Client
import os

# Configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
# Using a fast, smart model for summarization
MODEL = "qwen2.5-coder:32b" 

RSS_FEEDS = [
    "https://openai.com/blog/rss.xml",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/artificial-intelligence/index.xml",
    "https://blogs.microsoft.com/ai/feed/"
]

class NewsIntelligence:
    def __init__(self):
        self.client = Client(host=OLLAMA_HOST)

    def fetch_latest_news(self):
        """Fetches and aggregates the latest AI news headlines."""
        articles = []
        print("📡 Scanning RSS frequencies for AI signals...")
        
        for url in RSS_FEEDS:
            try:
                feed = feedparser.parse(url)
                # Get top 2 from each feed to ensure variety
                for entry in feed.entries[:2]:
                    articles.append({
                        "title": entry.title,
                        "link": entry.link,
                        "summary": entry.get('summary', '')[:200] + "...", # Truncate for prompt efficiency
                        "source": feed.feed.get('title', 'Unknown Source')
                    })
            except Exception as e:
                print(f"⚠️ Signal lost from {url}: {e}")
        
        # Shuffle to avoid same-source clustering
        random.shuffle(articles)
        return articles[:5] # Return top 5 diverse stories

    def generate_brief(self):
        """Generates a cohesive 'Welcome Brief' connecting news to Swayne Systems."""
        try:
            articles = self.fetch_latest_news()
        except Exception as e:
            print(f"⚠️ RSS Fetch Error: {e}")
            articles = [] # Trigger fallback handling

        # FALLBACK DATA (If RSS or Ollama fails, use this so UI is never 'Offline')
        fallback_brief = {
            "headline": "Intelligence Systems Active",
            "body": "Global data streams indicate accelerating demand for autonomous infrastructure. Swayne Systems is calibrated to support high-fidelity agentic workflows and real-time logic deployment.",
            "sentiment": "STABLE"
        }
        
        if not articles:
            print("⚠️ No articles found. Using operational fallback.")
            return fallback_brief

        # Format context for LLM
        news_context = "\n".join([f"- {a['title']} ({a['source']})" for a in articles])
        
        prompt = f"""You are the Voice of Swayne Systems, an advanced AI infrastructure platform.
        
Current Global AI News:
{news_context}

Task:
Write a short, high-tech, welcoming "Morning Brief" for the dashboard user.
1. Synthesize the news trends into a single cohesive narrative about the "Future of Automation".
2. Connect it to Swayne Systems (we build the infrastructure they are talking about).
3. Be confident, futuristic, and slightly mysterious (Cyberpunk/Bloomberg terminal vibe).
4. Short! Max 3 sentences.

Output JSON format:
{{
  "headline": "A short, punchy 3-5 word headline summarizing the vibe",
  "body": "The 3 sentence narrative.",
  "sentiment": "One word mood (e.g. ACCELERATING, DISRUPTIVE, STABLE)"
}}
"""
        
        try:
            print("🧠 Neural Engine Digesting Information...")
            response = self.client.chat(model=MODEL, messages=[{'role': 'user', 'content': prompt}], format='json')
            content = response['message']['content']
            
            import json
            data = json.loads(content)
            return data
            
        except Exception as e:
            print(f"❌ Synthesis Error: {e}")
            # Return the safe fallback instead of an error state
            return fallback_brief

if __name__ == "__main__":
    intel = NewsIntelligence()
    print(intel.generate_brief())
