#!/bin/bash
# hot_swap.sh
# Instantly updates the running site content WITHOUT a rebuild.

echo "🔥 Initiating Hot-Swap..."

# 1. Find the running container
# Pick the SITE container, not a Coolify helper (the old `docker ps -q | head -n 1` could grab either).
CONTAINER_ID=$(ssh -o StrictHostKeyChecking=no -i ~/.ssh/sterling_tunnel root@165.22.146.182 "docker ps --format '{{.ID}} {{.Names}}' | grep -v coolify | head -n 1 | cut -d' ' -f1")

if [ -z "$CONTAINER_ID" ]; then
    echo "❌ Error: No running container found!"
    exit 1
fi

echo "🎯 Target Container: $CONTAINER_ID"

# 2. Copy Files (Hot-Patch)
# We assume the files are currently correct LOCALLY (in the current directory)
# First scp them to the server temp, then docker cp? 
# Or assume they are on the server (git pulled).
# The PublishingManager runs LOCALLY on Mac Studio.
# It pushes to git 'live' (Server).
# The git hook on server updates /var/www/swaynesystems.ai
# So we just need to tell the server to copy from /var/www to container.

# --bedrock: the daily staff meeting only changes the Bedrock page, its replay log and generated images.
if [ "$1" = "--bedrock" ]; then
    echo "📂 Injecting Bedrock update..."
    ssh -o StrictHostKeyChecking=no -i ~/.ssh/sterling_tunnel root@165.22.146.182 "
        docker cp /var/www/swaynesystems.ai/dashboard/bedrock/index.html $CONTAINER_ID:/app/dashboard/bedrock/index.html && \\
        docker cp /var/www/swaynesystems.ai/dashboard/bedrock/meeting_latest.json $CONTAINER_ID:/app/dashboard/bedrock/meeting_latest.json && \\
        docker cp /var/www/swaynesystems.ai/dashboard/assets/. $CONTAINER_ID:/app/dashboard/assets/ && \\
        echo '✅ Bedrock content injected'
    "
    exit $?
fi

echo "📂 Injecting content..."
ssh -o StrictHostKeyChecking=no -i ~/.ssh/sterling_tunnel root@165.22.146.182 "
    docker cp /var/www/swaynesystems.ai/dashboard/bedrock/index.html $CONTAINER_ID:/app/dashboard/bedrock/index.html && \
    docker cp /var/www/swaynesystems.ai/dashboard/style.css $CONTAINER_ID:/app/dashboard/style.css && \
    docker cp /var/www/swaynesystems.ai/dashboard/assets $CONTAINER_ID:/app/dashboard/ && \
    docker cp /var/www/swaynesystems.ai/bedrock_api.py $CONTAINER_ID:/app/bedrock_api.py && \
    docker cp /var/www/swaynesystems.ai/bedrock_agents $CONTAINER_ID:/app/ && \
    docker cp /var/www/swaynesystems.ai/nginx.conf $CONTAINER_ID:/etc/nginx/nginx.conf && \
    docker exec $CONTAINER_ID nginx -s reload && \
    echo '✅ Content Injected (Skipping API Restart to preserve connection)'
"

echo "✨ Hot-Swap Complete! Site updated instantly."
