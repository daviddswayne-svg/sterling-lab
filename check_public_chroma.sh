#!/bin/bash
# Auto-ingest public knowledge if ChromaDB is empty

echo "🔍 Checking public ChromaDB status..."

PYTHON_CHECK='
from chromadb import PersistentClient
try:
    client = PersistentClient(path="/app/chroma_db_public")
    collections = client.list_collections()
    if len(collections) == 0:
        print("EMPTY")
    else:
        total = sum([c.count() for c in collections])
        if total == 0:
            print("EMPTY")
        else:
            print(f"OK:{total}")
except Exception as e:
    print(f"ERROR:{e}")
'

STATUS=$(python3 -c "$PYTHON_CHECK")

if [[ "$STATUS" == "EMPTY" ]] || [[ "$STATUS" == ERROR* ]]; then
    echo "⚠️  Public ChromaDB is empty or broken, re-ingesting..."
    python3 /app/ingest_lab_knowledge.py
    echo "✅ Public knowledge ingested"
else
    echo "✅ Public ChromaDB OK ($STATUS documents)"
fi
