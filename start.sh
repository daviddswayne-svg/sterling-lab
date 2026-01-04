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

# Step 6: RAG Ingestion (First Boot: Sync, Subsequent: Skip)
echo "[6/8] Checking Knowledge Bases..."

# First-boot detection: If DBs don't exist, run ingestion synchronously
FIRST_BOOT=false

# 1. Sterling Lab Public RAG (Synthetic)
if [ -f "/app/chroma_db_synthetic/chroma.sqlite3" ]; then
    echo "   [RAG] Public DB exists. Skipping ingestion."
elif [ -f "/app/ingest_lab_knowledge.py" ]; then
    echo "   [RAG] First boot detected. Ingesting Public Knowledge..."
    FIRST_BOOT=true
    python ingest_lab_knowledge.py 2>&1 | tee /tmp/ingest_public.log || {
        echo "⚠️  Public Ingest Failed - Check /tmp/ingest_public.log"
    }
fi

# 2. Sterling Estate Private RAG
if [ -f "/app/ingest_sterling.py" ] && [ ! -f "/app/chroma_db_synthetic/chroma.sqlite3" ]; then
    echo "   [RAG] Ingesting Estate Knowledge..."
    python ingest_sterling.py 2>&1 | tee /tmp/ingest_estate.log || {
        echo "⚠️  Estate Ingest Failed - Check /tmp/ingest_estate.log"
    }
fi

# 3. Bedrock Insurance RAG (Swiss Re Sigma)
if [ -f "/app/bedrock_agents/data/chroma_bedrock_intel/chroma.sqlite3" ]; then
    echo "   [RAG] Bedrock DB exists. Skipping ingestion."
elif [ -f "/app/bedrock_agents/ingest_sigma.py" ]; then
    echo "   [RAG] First boot detected. Ingesting Bedrock (Sigma) Knowledge..."
    FIRST_BOOT=true
    python bedrock_agents/ingest_sigma.py 2>&1 | tee /tmp/ingest_bedrock.log || {
        echo "⚠️  Bedrock Ingest Failed - Check /tmp/ingest_bedrock.log"
    }
fi

if [ "$FIRST_BOOT" = true ]; then
    echo "✅ First-boot ingestion complete. ChromaDB initialized."
else
    echo "✅ Using existing ChromaDB data."
fi

# Diagnostics (Background, non-blocking)
(
    echo "[BG] Running Diagnostics..."
    python rag_diagnostics.py 2>&1 | tee /tmp/diagnostics.log || echo "⚠️  Diagnostic Warnings"
    echo "✅ Background Diagnostics Complete"
) &

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
