import yfinance as yf
import random
from datetime import datetime, timedelta
import feedparser
from .config import OLLAMA_HOST, TICKERS

INSURANCE_RSS_FEEDS = [
    "https://www.insurancejournal.com/rss/news/",
    "https://www.cnbc.com/id/10000664/device/rss/rss.html"  # CNBC Finance
]

class MarketIntelligence:
    def __init__(self):
        # RAG disabled - using live data feeds instead
        pass

    def fetch_market_data(self):
        """Fetches real market data using yfinance.

        Returns only tickers that were actually retrieved. Never fabricates values: a missing ticker
        is simply absent, and downstream code shows "—" for it.
        """
        data = {}
        print("📊 Fetching Market Data...")
        try:
            history = yf.download(" ".join(TICKERS), period="1mo", progress=False, auto_adjust=True)
        except Exception as e:
            print(f"❌ Market Data Fetch Failed: {e}")
            return {}

        for ticker in TICKERS:
            try:
                close = history['Close'][ticker].dropna()
                if len(close) < 2:
                    raise ValueError("fewer than 2 closes")
                current, prev = float(close.iloc[-1]), float(close.iloc[-2])
                data[ticker] = {
                    "price": round(current, 2),
                    "change_pct": round((current - prev) / prev * 100, 2),
                    "return_1m_pct": round((current - float(close.iloc[0])) / float(close.iloc[0]) * 100, 2),
                    "volatility_30d": round(float(close.pct_change().dropna().std() * 100), 2),
                    "as_of": close.index[-1].strftime("%Y-%m-%d"),
                }
            except Exception as e:
                print(f"⚠️ No data for {ticker}: {e}")
        return data

    def fetch_macro(self):
        """US CPI year-over-year (FRED public CSV). Returns {} if unavailable; never a guess."""
        try:
            import requests
            r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL&cosd=2024-01-01", timeout=15)
            r.raise_for_status()
            rows = [ln.split(",") for ln in r.text.strip().splitlines()[1:]]
            idx = [float(v) for _, v in rows if v not in ("", ".")]
            if len(idx) < 14:
                return {}
            yoy = (idx[-1] / idx[-13] - 1) * 100
            yoy_prev = (idx[-2] / idx[-14] - 1) * 100
            return {"cpi_yoy": round(yoy, 1), "cpi_yoy_prev": round(yoy_prev, 1)}
        except Exception as e:
            print(f"⚠️ Macro fetch failed: {e}")
            return {}

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
            print(f"⚠️ News Fetch Failed: {e}. No headlines this run (not inventing any).")
            return []

    def read_sigma(self):
        """Reads the current Swiss Re publications (see sigma_report.py). Returns the full context dict."""
        from .sigma_report import get_sigma_context
        return get_sigma_context()

    def _legacy_sigma_stub(self):
        """OLD hardcoded sentence that was passed off as the Swiss Re report. Kept only for reference; unused."""
        return "Market analysis powered by real-time data feeds. Global reinsurance markets continue to adjust to elevated catastrophe losses and persistent inflation. Property catastrophe rates remain firm heading into 2025 renewals."

    def get_full_briefing_context(self):
        """Aggregates all intel for the Content Director."""
        market_data = self.fetch_market_data()
        macro = self.fetch_macro()
        news = self.fetch_news_headlines()
        sigma = self.read_sigma()
        
        return {
            "market_data": market_data,
            "macro": macro,
            "news_headlines": news,
            "sigma": sigma,
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    intel = MarketIntelligence()
    print(intel.get_full_briefing_context())
