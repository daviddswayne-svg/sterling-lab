#!/bin/bash
# M1 Mac Studio - Tunnel & Ollama Keepalive Script
# Ensures Ollama is running and SSH tunnel to droplet is active
# Run at startup and every 2 hours via cron

LOGFILE="$HOME/tunnel_keepalive_m1.log"
DROPLET="root@165.22.146.182"
TUNNEL_PORT=11434
REMOTE_PORT=12434  # Different port for M1!

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

log "=========================================="
log "M1 Keepalive Check Started"
log "=========================================="

# 1. Check if Ollama is running
log "[1/3] Checking Ollama status..."
if pgrep -x "ollama" > /dev/null; then
    log "✅ Ollama is running"
else
    log "⚠️  Ollama not running, starting..."
    ollama serve > /dev/null 2>&1 &
    sleep 3
    
    if pgrep -x "ollama" > /dev/null; then
        log "✅ Ollama started successfully"
    else
        log "❌ ERROR: Failed to start Ollama"
    fi
fi

# 2. Check Ollama API
log "[2/3] Testing Ollama API..."
if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    VERSION=$(curl -s http://localhost:11434/api/version | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    log "✅ Ollama API responding (version: $VERSION)"
else
    log "❌ ERROR: Ollama API not responding"
fi

# 3. Check SSH Tunnel
log "[3/3] Checking SSH tunnel to droplet..."

# Check if tunnel is already running
TUNNEL_PID=$(pgrep -f "ssh.*$DROPLET.*$REMOTE_PORT:localhost:$TUNNEL_PORT")

if [ -n "$TUNNEL_PID" ]; then
    # Tunnel process exists, test if it works
    log "   Found tunnel process (PID: $TUNNEL_PID), testing..."
    
    if ssh -O check -S ~/.ssh/tunnel-m1-control $DROPLET 2>/dev/null; then
        log "✅ SSH tunnel is active and healthy"
    else
        log "⚠️  Tunnel process exists but connection dead, restarting..."
        kill $TUNNEL_PID 2>/dev/null
        sleep 2
    fi
fi

# Start tunnel if not running or was killed
TUNNEL_PID=$(pgrep -f "ssh.*$DROPLET.*$REMOTE_PORT:localhost:$TUNNEL_PORT")
if [ -z "$TUNNEL_PID" ]; then
    log "   Starting new SSH tunnel..."
    
    # Create tunnel with control socket for health checks
    ssh -f -N \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -M -S ~/.ssh/tunnel-m1-control \
        -R $REMOTE_PORT:localhost:$TUNNEL_PORT \
        $DROPLET
    
    sleep 2
    
    if ssh -O check -S ~/.ssh/tunnel-m1-control $DROPLET 2>/dev/null; then
        NEW_PID=$(pgrep -f "ssh.*$DROPLET.*$REMOTE_PORT:localhost:$TUNNEL_PORT")
        log "✅ SSH tunnel established (PID: $NEW_PID)"
    else
        log "❌ ERROR: Failed to establish SSH tunnel"
    fi
else
    log "✅ SSH tunnel already active (PID: $TUNNEL_PID)"
fi

log "=========================================="
log "M1 Keepalive Check Complete"
log "=========================================="
echo ""
