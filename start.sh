#!/bin/bash
set -e

echo "=================================="
echo "🚀 STERLING LAB STARTUP SEQUENCE"
echo "=================================="
echo ""

# Step 1: Run Diagnostics
echo "[1/5] Running RAG System Diagnostics..."
python rag_diagnostics.py || echo "⚠️  Warning: Some diagnostic checks failed."
echo ""

# Step 2: Verify Dashboard Exists (will be served by separate Nginx container)
echo "[2/5] Verifying Dashboard Files..."
if [ ! -d "/app/dashboard" ]; then
    echo "❌ FATAL: /app/dashboard directory not found!"
    exit 1
fi

if [ ! -f "/app/dashboard/index.html" ]; then
    echo "❌ FATAL: /app/dashboard/index.html not found!"
    exit 1
fi

echo "✅ Dashboard files verified at /app/dashboard"
echo ""

# Step 3: Start Bedrock Chat API
echo "[3/5] Starting Bedrock Chat API..."
python bedrock_api.py > /tmp/bedrock_api.log 2>&1 &
API_PID=$!
echo "✅ Bedrock API started with PID: $API_PID"

# Wait for API to be ready
echo "Waiting for Bedrock API port 5000..."
MAX_WAIT_API=15
COUNTER_API=0
while [ $COUNTER_API -lt $MAX_WAIT_API ]; do
    if curl -s http://127.0.0.1:5000/health > /dev/null 2>&1; then
        echo "✅ Bedrock API is responding on port 5000"
        break
    fi
    echo "   Still waiting for API... ($COUNTER_API/$MAX_WAIT_API)"
    sleep 1
    COUNTER_API=$((COUNTER_API + 1))
done

if [ $COUNTER_API -eq $MAX_WAIT_API ]; then
    echo "⚠️  WARNING: Bedrock API didn't respond in time. Checking logs:"
    tail -n 20 /tmp/bedrock_api.log
fi
echo ""

# Step 4: Start Streamlit
echo "[4/5] Starting Streamlit on port 8501..."
streamlit run chat_app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.baseUrlPath=/lab \
    2>&1 | tee /tmp/streamlit.log &

STREAMLIT_PID=$!
echo "✅ Streamlit started with PID: $STREAMLIT_PID"
echo ""

# Step 5: Wait for Streamlit to be Ready
echo "[5/5] Waiting for Streamlit to be ready..."
MAX_WAIT=30
COUNTER=0
while [ $COUNTER -lt $MAX_WAIT ]; do
    if curl -s http://127.0.0.1:8501/_stcore/health > /dev/null 2>&1; then
        echo "✅ Streamlit is responding on port 8501"
        break
    fi
    echo "   Still waiting... ($COUNTER/$MAX_WAIT)"
    sleep 1
    COUNTER=$((COUNTER + 1))
done

if [ $COUNTER -eq $MAX_WAIT ]; then
    echo "❌ FATAL: Streamlit failed to start within ${MAX_WAIT}s"
    echo "Streamlit logs:"
    tail -20 /tmp/streamlit.log
    exit 1
fi
echo ""

echo "=================================="
echo "✅ ALL SERVICES STARTED SUCCESSFULLY"
echo "Streamlit PID: $STREAMLIT_PID"
echo "Bedrock API PID: $API_PID"
echo "=================================="
echo ""
echo "📡 Application ready for Nginx proxy"
echo "   Streamlit endpoint: http://localhost:8501"
echo "   Bedrock API endpoint: http://localhost:5000"
echo ""

# Keep Streamlit running in foreground (Docker best practice)
wait $STREAMLIT_PID

