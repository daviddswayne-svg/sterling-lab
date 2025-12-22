#!/bin/bash
# Start Simple HTTP Video Server on Port 8888
# Serves content from ~/Movies/SiteVideos

VIDEO_DIR="$HOME/Movies/SiteVideos"
PORT=8888

# Create dir if not exists
if [ ! -d "$VIDEO_DIR" ]; then
    mkdir -p "$VIDEO_DIR"
    echo "Created video directory: $VIDEO_DIR"
fi

# Check if already running
if pgrep -f "python3 -m http.server $PORT" > /dev/null; then
    echo "Video server already running on port $PORT"
else
    echo "Starting video server on port $PORT..."
    cd "$VIDEO_DIR"
    nohup python3 -m http.server $PORT > /dev/null 2>&1 &
    echo "Video server started (PID $!)"
fi
