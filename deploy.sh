#!/bin/bash
# deploy.sh
# Safely deploys code to the Sterling Lab live environment

echo "🚀 Starting Deployment to SwayneSystems.ai..."

# Check if 'live' remote exists
if ! git remote | grep -q "^live$"; then
    echo "⚠️  Remote 'live' not found. Adding it now..."
    git remote add live root@165.22.146.182:/var/www/swaynesystems.ai.git
fi

# Confirm with user
read -p "❓ Are you sure you want to deploy to LIVE? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled."
    exit 1
fi

echo "📦 Pushing to Live Server..."
git push live main

echo "☁️  Syncing with GitHub Backup..."
git push origin main

echo "✅ Deployment Triggered! Check Coolify for build status."
