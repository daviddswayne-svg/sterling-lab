from bedrock_agents.market_intel import MarketIntelligence
import json

def test_intel():
    print("🧪 Initializing Market Intelligence...")
    intel = MarketIntelligence()
    
    print("\n📊 Testing Market Data Fetch (yfinance)...")
    data = intel.fetch_market_data()
    print(f"   Received: {json.dumps(data, indent=2)}")
    
    print("\n📰 Testing News Fetch (Mock)...")
    news = intel.fetch_news_headlines()
    print(f"   Received: {news}")
    
    print("\n🧠 Testing RAG Query (Swiss Re Sigma)...")
    rag = intel.query_sigma_rag("outlook for 2026")
    print(f"   Context Length: {len(rag)}")
    print(f"   Snippet: {rag[:200]}...")

if __name__ == "__main__":
    test_intel()
