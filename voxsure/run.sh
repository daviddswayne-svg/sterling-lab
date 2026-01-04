#!/bin/bash

# Kill background processes on exit
trap 'kill $(jobs -p)' EXIT

# Clean up existing processes on our ports
lsof -ti:12345,12346 | xargs kill -9 > /dev/null 2>&1

echo "📦 Checking dependencies..."
python3 -m pip install fastapi uvicorn trimesh numpy Pillow python-multipart rtree > /dev/null 2>&1

# Start Backend
echo "📡 Starting Backend API on http://127.0.0.1:12346..."
cd /Users/daviddswayne/.gemini/antigravity/scratch/voxsure/backend
python3 main.py &

# Start Frontend
echo "🌐 Starting Frontend Dashboard on http://127.0.0.1:12345..."
cd /Users/daviddswayne/.gemini/antigravity/scratch/voxsure/app
python3 -m http.server 12345 --bind 127.0.0.1 &

sleep 3
echo "------------------------------------------------"
echo "✅ VoxSure is officially LIVE!"
echo "📍 Access the app here: http://127.0.0.1:12345"
echo "------------------------------------------------"
echo "Press Ctrl+C to stop all services."

wait
