#!/bin/bash
#
# Sterling Lab SSH Tunnel — the ONE reverse tunnel from the Mac Studio M3 to the droplet
#   8888  video server     11434  Ollama (site AI)     8002  ESC API     9101  Bedrock trigger
# (m3_keepalive.sh no longer runs its own tunnel for 11434/8888 — 2026-09-26.)
#
# ExitOnForwardFailure=yes: if any port can't be bound (e.g. the droplet still holds it
# from a dead session), ssh exits and autossh retries until ALL ports are bound — instead
# of staying up forwarding nothing (the 2026-09-26 ESC outage).
# AUTOSSH_GATETIME=0: keep retrying even if the very first attempt fails quickly.
#

REMOTE_HOST="165.22.146.182"
REMOTE_USER="root"
SSH_KEY="$HOME/.ssh/sterling_tunnel"
REMOTE_PORT="11434"
LOCAL_PORT="11434"

export AUTOSSH_GATETIME=0

exec /opt/homebrew/bin/autossh -M 0 \
  -N \
  -R 0.0.0.0:8888:localhost:8888 \
  -R 0.0.0.0:${REMOTE_PORT}:localhost:${LOCAL_PORT} \
  -R 0.0.0.0:8002:localhost:8002 \
  -R 0.0.0.0:9101:localhost:9101 \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes \
  -o StrictHostKeyChecking=no \
  -i "${SSH_KEY}" \
  ${REMOTE_USER}@${REMOTE_HOST}
