#!/bin/bash

# ComfyUI Tunnel Keepalive for M3 Mac Studio
# Maintains reverse SSH tunnel from M3 to DigitalOcean server for ComfyUI access

REMOTE_HOST="root@165.22.146.182"
LOCAL_PORT=8188
REMOTE_PORT=8188

while true; do
    echo "[$(date)] Starting ComfyUI tunnel: localhost:${LOCAL_PORT} -> ${REMOTE_HOST}:${REMOTE_PORT}"
    
    # Start reverse tunnel with keepalive
    ssh -N -R 0.0.0.0:${REMOTE_PORT}:localhost:${LOCAL_PORT} \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -o StrictHostKeyChecking=no \
        ${REMOTE_HOST}
    
    # If SSH exits, log it and restart after delay
    EXIT_CODE=$?
    echo "[$(date)] Tunnel died with exit code ${EXIT_CODE}. Restarting in 10 seconds..."
    sleep 10
done
