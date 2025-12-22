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
python bedrock_api.py > /tmp/bedrock_api.log 2>&1 &
API_PID=$!

# Step 5: Run RAG Ingestion (Background)
# This was blocking startup!
echo "[5/8] Launching Background RAG Ingestion..."
(
    echo "   [BG] Ingesting Public Knowledge Base..."
    if [ -f "/app/ingest_lab_knowledge.py" ]; then
        python ingest_lab_knowledge.py || echo "⚠️  Public Ingest Warnings"
    fi
    
    echo "   [BG] Ingesting Sterling Estate Knowledge..."
    if [ -f "/app/ingest_sterling.py" ]; then
        python ingest_sterling.py || echo "⚠️  Estate Ingest Warnings"
    fi
    
    echo "   [BG] Running Diagnostics..."
    python rag_diagnostics.py || echo "⚠️  Diagnostic Warnings"
    
    echo "✅ Background Ingestion Complete"
) &

# Step 6: Wait/Monitor
echo "[6/8] System started. Monitoring PIDs..."
echo "      Nginx: $NGINX_PID"
echo "      App: $STREAMLIT_PID"

wait $NGINX_PID
