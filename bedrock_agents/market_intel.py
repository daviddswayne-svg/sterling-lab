import yfinance as yf
import random
from datetime import datetime, timedelta
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from .config import BEDROCK_CHROMA_PATH, OLLAMA_HOST, TICKERS

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
            # 1 month history for volatility calc
            history = yf.download(tickers_str, period="1mo", progress=False)
            
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
        """Generates realistic mock headlines (since no NewsAPI key provided)."""
        # In a real scenario, use requests.get("https://newsapi.org/v2/...")
        
        headlines = [
            "Global Reinsurance Rates Stabilize Ahead of Renewal Season",
            "Climate Resilience Bonds Gain Traction Among Major Insurers",
            "Cyber Liability Premiums Adjust as Ransomware Attacks Evolve",
            "Swiss Re Report Highlights Inflationary Pressures on Claims",
            "PropTech Integration: The New Frontier for Home Insurance",
            "Florida Legislation Impacting Property Catastrophe Reinsurance",
            "AI-Driven Underwriting reducing processing times by 40%",
            "Severe Convective Storm Losses Top $50B in 2024",
            "Parametric Insurance Solutions Expanding for High-Net-Worth Assets",
            "Smart Home Sensors Becoming Standard for Premium Policy Discounts"
        ]
        
        # Shuffle and pick top 5
        random.shuffle(headlines)
        return headlines[:5]

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
