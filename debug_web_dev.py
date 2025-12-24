
from bedrock_agents.staff.web_developer import WebDeveloper
import json

print("--- START WEB DEV DEBUG ---")
dev = WebDeveloper()
brief = {
    "headline": "Test Brief Headline",
    "key_points": ["Point A", "Point B"],
    "summary": "This is a test summary representing the market intelligence."
}

try:
    result = dev.build_page(brief)
    print("\n--- JSON OUTPUT ---")
    print(json.dumps(result, indent=2))
    print("-------------------")
    
    # Validation
    required_keys = [
        "strategy_title", "strategy_desc", 
        "risk_title", "risk_desc", 
        "opp_title", "opp_desc", 
        "insight_title", "insight_desc"
    ]
    
    missing = [k for k in required_keys if k not in result]
    if missing:
        print(f"❌ MISSING KEYS: {missing}")
    else:
        print("✅ All keys present.")
        
except Exception as e:
    print(f"❌ EXECUTION FUNCTION FAILED: {e}")

print("--- END WEB DEV DEBUG ---")
