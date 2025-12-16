#!/bin/bash
set -e

echo "🔍 Running RAG System Diagnostics..."
python rag_diagnostics.py || echo "⚠️  Warning: Some diagnostic checks failed. Check logs above."

echo ""
echo "🚀 Starting Sterling Lab Services..."

# Verify Nginx config before starting
echo "Testing Nginx configuration..."
nginx -t

echo "Starting Streamlit on port 8501..."
# Start Streamlit in the background
# We set baseUrlPath to /lab so Streamlit knows it's serving from a subdirectory
streamlit run chat_app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true --server.baseUrlPath=/lab &

echo "Starting Nginx on port 80..."
# Start Nginx in the foreground
exec nginx -g 'daemon off;'
