#!/bin/bash
# M3 Mac Studio - Tunnel & Ollama Keepalive Script
# Ensures Ollama and the video server are running; reports on the SSH tunnel (launchd owns it)
# Run at startup and every 2 hours via cron

LOGFILE="$HOME/tunnel_keepalive_m3.log"
DROPLET="root@165.22.146.182"
TUNNEL_PORT=11434
REMOTE_PORT=11434

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOGFILE"
}

log "=========================================="
log "M3 Keepalive Check Started"
log "=========================================="

# 1. Check if Ollama is running AND responding
log "[1/3] Checking Ollama status..."

# Function to start Ollama
start_ollama() {
    log "   Starting Ollama..."
    ollama serve > /dev/null 2>&1 &
    sleep 5
}

# Check API health
if curl -s --max-time 5 http://localhost:11434/api/version > /dev/null; then
    VERSION=$(curl -s http://localhost:11434/api/version | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    log "✅ Ollama API responding (version: $VERSION)"
else
    log "⚠️  Ollama API NOT responding (or process missing)"
    
    # Check if process exists (zombie?)
    if pgrep -x "ollama" > /dev/null; then
        log "   Found unresponsive 'ollama' process. Force killing..."
        pkill -9 -x ollama
        sleep 2
    fi
    
    # Restart
    start_ollama
    
    if curl -s --max-time 10 http://localhost:11434/api/version > /dev/null; then
        log "✅ Ollama restarted successfully"
    else
        log "❌ ERROR: Failed to restart Ollama (still unresponsive)"
    fi
fi

# 2. Check Video Server
log "[2/3] Checking Video Server..."
$HOME/mac_studio_scripts/start_video_server.sh | while read line; do log "   $line"; done

# 3. Check SSH Tunnel
log "[3/3] SSH tunnel to droplet..."
# The tunnel is owned by launchd (com.swaynesystems.sterling.tunnel -> sterling_tunnel.sh):
# one autossh tunnel for 8888/11434/8002/9101 that restarts itself until every port is
# bound. This script used to start a second tunnel for 11434/8888; its "is it running?"
# pgrep never matched, so from 2026-09 it logged a failed restart every 15 min. Removed
# 2026-09-26 - now it only reports.
if pgrep -f "autossh.*$DROPLET" > /dev/null; then
    log "✅ launchd tunnel (autossh) is running"
else
    log "⚠️  launchd tunnel not running - launchd should restart it (com.swaynesystems.sterling.tunnel)"
fi

log "=========================================="
log "M3 Keepalive Check Complete"
log "=========================================="
echo ""
