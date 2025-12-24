#!/bin/bash
set -e

echo "=================================="
echo "🚀 STERLING LAB STARTUP SEQUENCE"
echo "=================================="
echo ""

# Step 1: Verify Dashboard Exists
echo "[1/8] Verifying Dashboard Files..."
if [ ! -d "/app/dashboard" ]; then
    echo "❌ FATAL: /app/dashboard directory not found!"
    exit 1
fi
if [ ! -f "/app/dashboard/index.html" ]; then
    echo "❌ FATAL: /app/dashboard/index.html not found!"
    exit 1
fi
echo "✅ Dashboard files verified at /app/dashboard"

# Step 2: Start Nginx Early (Critical for Health Checks)
echo "[2/8] Starting Nginx on port 80..."
nginx -g 'daemon off;' &
NGINX_PID=$!
echo "✅ Nginx started with PID: $NGINX_PID"
sleep 2 # Allow bind

# Step 3: Start Streamlit
echo "[3/8] Starting Streamlit on port 8501..."
streamlit run chat_app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.baseUrlPath=/lab \
    2>&1 | tee /tmp/streamlit.log &
STREAMLIT_PID=$!

# Step 4: Start Bedrock Chat API
echo "[4/8] Starting Bedrock Chat API..."
python bedrock_api.py 2>&1 | tee /tmp/bedrock_api.log &
API_PID=$!

# Step 5: Run RAG Ingestion (Background)
# This was blocking startup!
echo "[5/8] Launching Background RAG Ingestion..."
    echo "   [BG] Checking Knowledge Bases..."
    
    # 1. Sterling Lab Public RAG (Synthetic)
    if [ -f "/app/chroma_db_synthetic/chroma.sqlite3" ]; then
        echo "   [RAG] Public DB exists. Skipping ingestion."
    elif [ -f "/app/ingest_lab_knowledge.py" ]; then
        echo "   [RAG] Ingesting Public Knowledge..."
        python ingest_lab_knowledge.py || echo "⚠️  Public Ingest Warnings"
    fi
    
    # 2. Sterling Estate Private RAG
    if [ -f "/app/ingest_sterling.py" ]; then
         # Also writes to synthetic DB per ingest_sterling.py
         if [ ! -f "/app/chroma_db_synthetic/chroma.sqlite3" ]; then
            echo "   [RAG] Ingesting Estate Knowledge..."
            python ingest_sterling.py || echo "⚠️  Estate Ingest Warnings"
         fi
    fi

    # 3. Bedrock Insurance RAG (Swiss Re Sigma)
    if [ -f "/app/bedrock_agents/data/chroma_bedrock_intel/chroma.sqlite3" ]; then
        echo "   [RAG] Bedrock DB exists. Skipping ingestion."
    elif [ -f "/app/bedrock_agents/ingest_sigma.py" ]; then
        echo "   [RAG] Ingesting Bedrock (Sigma) Knowledge..."
        python bedrock_agents/ingest_sigma.py || echo "⚠️  Bedrock Ingest Warnings"
    fi
    
    echo "   [BG] Running Diagnostics..."
    python rag_diagnostics.py || echo "⚠️  Diagnostic Warnings"
    
    echo "✅ Background Checks Complete"
) &

# Step 6: Wait/Monitor
echo "[6/8] System started. Monitoring PIDs..."
echo "      Nginx: $NGINX_PID"
echo "      App: $STREAMLIT_PID"

wait $NGINX_PID
