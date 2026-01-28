#!/bin/bash
# set -e removed to prevent crash loop on minor errors

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

# DEBUG: Check Volumes and Fix Permissions
echo "[DEBUG] Checking Volume Mounts..."
ls -la /app/chroma_db_synthetic || echo "⚠️ /app/chroma_db_synthetic not found"
ls -la /app/bedrock_agents/data || echo "⚠️ /app/bedrock_agents/data not found"

# Force permissions (Brute Force Fix for Volume Mount issues)
chmod -R 777 /app/chroma_db_synthetic || echo "⚠️ Could not chmod chroma_db_synthetic"
chmod -R 777 /app/bedrock_agents/data || echo "⚠️ Could not chmod bedrock_agents/data"

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

# Step 5: Pre-create ChromaDB Directories (Critical for Volume Mounts)
echo "[5/8] Preparing ChromaDB Storage..."
mkdir -p /app/chroma_db_synthetic
mkdir -p /app/bedrock_agents/data/chroma_bedrock_intel
echo "✅ ChromaDB directories ready"

# Step 6: RAG Disabled - Using MCP Tools Instead
echo "[6/8] RAG Ingestion Skipped (MCP Migration)"
echo "   [INFO] ChromaDB/RAG has been replaced with MCP tools (Exa, GitHub)"
echo "   [INFO] Main chat at /lab uses real-time web search"
echo "✅ MCP-powered system ready"

# Step 8: Start VoxSure Forensic Audit Services
echo "[8/8] Starting VoxSure Forensic Audit Services..."
# Backend on 12346
cd /app/voxsure/backend && python3 main.py 2>&1 | tee /tmp/voxsure_backend.log &
VOXSURE_PID=$!
echo "✅ VoxSure Services started (PID: $VOXSURE_PID)"

# Step 9: Wait/Monitor
echo "[9/9] System started. Monitoring PIDs..."
echo "      Nginx: $NGINX_PID"
echo "      Streamlit: $STREAMLIT_PID"  
echo "      API: $API_PID"
echo "      VoxSure: $VOXSURE_PID"
echo ""
echo "✅ Sterling Lab (Unified) is online!"

wait $NGINX_PID
