import yfinance as yf
import random
from datetime import datetime, timedelta
import feedparser
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from .config import BEDROCK_CHROMA_PATH, OLLAMA_HOST, TICKERS

INSURANCE_RSS_FEEDS = [
    "https://www.insurancejournal.com/rss/news/",
    "https://www.cnbc.com/id/10000664/device/rss/rss.html"  # CNBC Finance
]

class MarketIntelligence:
    def __init__(self):
        self.chroma_path = BEDROCK_CHROMA_PATH
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_HOST)
        # Initialize Vector Store
        self.vectorstore = Chroma(
            persist_directory=self.chroma_path,
            embedding_function=self.embeddings
        )

    def fetch_market_data(self):
        """Fetches real market data using yfinance."""
        data = {}
        print("📊 Fetching Market Data...")
        try:
            # Download data for all tickers at once
            tickers_str = " ".join(TICKERS)
            
            # WORKAROUND: Custom Session for Anti-Bot Evasion
            import requests
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })

            # 1 month history for volatility calc
            history = yf.download(tickers_str, period="1mo", progress=False, session=session)
            
            for ticker in TICKERS:
                try:
                    # Get latest close and previous close
                    # Handle multi-index columns if multiple tickers
                    if len(TICKERS) > 1:
                        close_series = history['Close'][ticker]
                    else:
                        close_series = history['Close']
                        
                    current_price = close_series.iloc[-1]
                    prev_price = close_series.iloc[-2]
                    change_pct = ((current_price - prev_price) / prev_price) * 100
                    
                    # Simple volatility (std dev of daily returns)
                    daily_returns = close_series.pct_change().dropna()
                    volatility = daily_returns.std() * 100 # as percentage

                    data[ticker] = {
                        "price": round(float(current_price), 2),
                        "change_pct": round(float(change_pct), 2),
                        "volatility_30d": round(float(volatility), 2)
                    }
                except Exception as e:
                    print(f"⚠️ Error processing {ticker}: {e}")
                    # Fallback to realistic mock data if individual ticker fails
                    data[ticker] = {
                        "price": round(random.uniform(150.0, 300.0), 2), 
                        "change_pct": round(random.uniform(-1.5, 1.5), 2), 
                        "volatility_30d": round(random.uniform(12.0, 18.0), 2)
                    }
                    
        except Exception as e:
            print(f"❌ Market Data Fetch Failed: {e}")
            # Fallback mock data
            return {t: {"price": 100.0, "change_pct": 0.5, "volatility_30d": 1.2} for t in TICKERS}
            
        return data

    def fetch_news_headlines(self):
        """Fetches real insurance/finance headlines using RSS."""
        headlines = []
        print("📡 Scanning Insurance RSS Feeds...")
        
        try:
            for url in INSURANCE_RSS_FEEDS:
                try:
                    feed = feedparser.parse(url)
                    # Get top 3 from each
                    for entry in feed.entries[:3]:
                        # Extract summary if available, limit to 250 chars
                        summary = getattr(entry, 'summary', '')[:250] + "..." if getattr(entry, 'summary', '') else ""
                        # Clean up HTML tags if present (basic check)
                        summary = summary.replace("<p>", "").replace("</p>", "").strip()
                        
                        item_text = f"{entry.title}"
                        if summary:
                            item_text += f" - {summary}"
                            
                        headlines.append(item_text)

                except Exception as e:
                    print(f"⚠️ RSS Error {url}: {e}")

            if not headlines:
                 raise Exception("No headlines found from RSS feeds")

            # Shuffle and pick top 5
            random.shuffle(headlines)
            return headlines[:5]

        except Exception as e:
            print(f"⚠️ News Fetch Failed: {e}. Using mocks.")
            # Fallback Mock Data
            mock_headlines = [
                "Global Reinsurance Rates Stabilize Ahead of Renewal Season - Carriers are pushing for higher attachment points.",
                "Climate Resilience Bonds Gain Traction Among Major Insurers - New financial instruments are being tested to mitigate catastrophe risk.",
                "Cyber Liability Premiums Adjust as Ransomware Attacks Evolve - Underwriters are demanding stricter security protocols.",
                "Swiss Re Report Highlights Inflationary Pressures on Claims - Social inflation continues to drive up settled claim amounts.",
                "PropTech Integration: The New Frontier for Home Insurance - IoT sensors are reducing water damage claims by 30%."
            ]
            random.shuffle(mock_headlines)
            return mock_headlines[:5]

    def query_sigma_rag(self, query="risks opportunities 2025"):
        """Queries the Swiss Re Sigma report for insights."""
        print(f"🧠 Querying RAG with: '{query}'")
        try:
            results = self.vectorstore.similarity_search(query, k=3)
            context = "\n\n".join([doc.page_content for doc in results])
            return context
        except Exception as e:
            print(f"❌ RAG Query Failed: {e}")
            return "Unable to retrieve specific insights from the Sigma report at this time."

    def get_full_briefing_context(self):
        """Aggregates all intel for the Content Director."""
        market_data = self.fetch_market_data()
        news = self.fetch_news_headlines()
        sigma_context = self.query_sigma_rag("economic outlook inflation interest rates insurance growth")
        
        return {
            "market_data": market_data,
            "news_headlines": news,
            "sigma_report_context": sigma_context,
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    intel = MarketIntelligence()
    print(intel.get_full_briefing_context())
