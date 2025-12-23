#!/bin/bash
#
# Sterling Lab SSH Tunnel
# Maintains reverse SSH tunnel from Mac Studio to DigitalOcean droplet
# Port 11434: Ollama API
#

REMOTE_HOST="165.22.146.182"
REMOTE_USER="root"
SSH_KEY="$HOME/.ssh/sterling_tunnel"
REMOTE_PORT="11434"
LOCAL_PORT="11434"

exec /opt/homebrew/bin/autossh -M 0 \
  -N \
  -R 0.0.0.0:8888:localhost:8888 \
  -R 0.0.0.0:${REMOTE_PORT}:localhost:${LOCAL_PORT} \
  -R 0.0.0.0:8001:localhost:8000 \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes \
  -o StrictHostKeyChecking=no \
  -i "${SSH_KEY}" \
  ${REMOTE_USER}@${REMOTE_HOST}
