#!/bin/bash
set -e

echo "=================================="
echo "🚀 STERLING LAB STARTUP SEQUENCE"
echo "=================================="
echo ""

# Step 1: Run Diagnostics
echo "[1/7] Running RAG System Diagnostics..."
python rag_diagnostics.py || echo "⚠️  Warning: Some diagnostic checks failed."
echo ""

# Step 2: Verify Dashboard Exists
echo "[2/7] Verifying Dashboard Files..."
if [ ! -d "/app/dashboard" ]; then
    echo "❌ FATAL: /app/dashboard directory not found!"
    exit 1
fi

if [ ! -f "/app/dashboard/index.html" ]; then
    echo "❌ FATAL: /app/dashboard/index.html not found!"
    exit 1
fi

echo "✅ Dashboard files verified at /app/dashboard"
ls -lah /app/dashboard/
echo ""

# Step 3: Test Nginx Configuration
echo "[3/7] Testing Nginx Configuration..."
nginx -t
echo "✅ Nginx config is valid"
echo ""

# Step 3.5: Start Bedrock Chat API
echo "[3.5/7] Starting Bedrock Chat API..."
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
    # Don't exit, might be slow startup, but warn
fi
echo ""

# Step 4: Start Streamlit
echo "[4/7] Starting Streamlit on port 8501..."
streamlit run chat_app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    2>&1 | tee /tmp/streamlit.log &

STREAMLIT_PID=$!
echo "✅ Streamlit started with PID: $STREAMLIT_PID"
echo ""

# Step 5: Wait for Streamlit to be Ready
echo "[5/7] Waiting for Streamlit to be ready..."
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

# Step 6: Start Nginx
echo "[6/7] Starting Nginx on port 80..."
nginx -g 'daemon off;' &
NGINX_PID=$!
echo "✅ Nginx started with PID: $NGINX_PID"
echo ""

# Step 7: Verify Nginx is Actually Running
echo "[7/7] Verifying Nginx is serving traffic..."
sleep 2  # Give Nginx time to initialize

# Check if Nginx process is still alive
if ! ps -p $NGINX_PID > /dev/null 2>&1; then
    echo "❌ FATAL: Nginx process died immediately after starting!"
    echo "Nginx error log should be visible above. Checking pid..."
    ps aux | grep nginx
    exit 1
fi

# Test Main App route
if curl -s -I http://127.0.0.1:80/ 2>&1 | head -1 | grep -q "HTTP"; then
    echo "✅ App is accessible at /"
else
    echo "⚠️  WARNING: App test failed - check nginx error logs above"
fi

echo ""
echo "=================================="
echo "✅ ALL SERVICES STARTED SUCCESSFULLY"
echo "Streamlit PID: $STREAMLIT_PID"
echo "Nginx PID: $NGINX_PID"
echo "=================================="
echo ""
echo "📡 Monitoring Nginx (foreground)..."
echo "   Dashboard: http://localhost/"
echo "   Lab: http://localhost/lab"
echo ""

# Keep Nginx running in foreground
wait $NGINX_PID
