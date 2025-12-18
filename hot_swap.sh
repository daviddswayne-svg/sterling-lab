#!/bin/bash
# hot_swap.sh
# Instantly updates the running site content WITHOUT a rebuild.

echo "🔥 Initiating Hot-Swap..."

# 1. Find the running container
CONTAINER_ID=$(ssh -o StrictHostKeyChecking=no -i ~/.ssh/sterling_tunnel root@165.22.146.182 "docker ps -q | head -n 1")

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

echo "📂 Injecting content..."
ssh -o StrictHostKeyChecking=no -i ~/.ssh/sterling_tunnel root@165.22.146.182 "
    docker cp /var/www/swaynesystems.ai/dashboard/bedrock/index.html $CONTAINER_ID:/app/dashboard/bedrock/index.html && \
    docker cp /var/www/swaynesystems.ai/dashboard/style.css $CONTAINER_ID:/app/dashboard/style.css && \
    docker cp /var/www/swaynesystems.ai/dashboard/assets $CONTAINER_ID:/app/dashboard/ && \
    docker cp /var/www/swaynesystems.ai/bedrock_api.py $CONTAINER_ID:/app/bedrock_api.py && \
    docker exec -d $CONTAINER_ID sh -c "pkill -f bedrock_api.py; nohup python bedrock_api.py > /tmp/bedrock_api.log 2>&1 &" && \
    echo '✅ Content Injected & API Restarted'
"

echo "✨ Hot-Swap Complete! Site updated instantly."
