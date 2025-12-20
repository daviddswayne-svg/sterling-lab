# Frontier Lab Deployment Instructions

## Quick Deploy

```bash
cd /Users/daviddswayne/.gemini/antigravity/scratch/sterling_lab

# 1. Commit changes
git add .
git commit -m "Deploy Frontier Lab to /lab with Sterling Estate branding"

# 2. Push to BOTH remotes (CRITICAL!)
git push origin main
git push live main

# 3. Watch Coolify build
# Navigate to: http://165.22.146.182:8000
# Monitor logs for deployment status
```

## SSH Tunnel Setup (CRITICAL)

You need TWO tunnels running simultaneously:

### Terminal 1: M3 Tunnel (Standard Models)
```bash
ssh -R 11434:localhost:11434 root@165.22.146.182
# Keep this running
```

### Terminal 2: M1 Tunnel (Oracle Deep Reasoning)  
```bash
# From Mac Studio M3, tunnel to M1 then to droplet
ssh -R 12434:localhost:11434 -J thunderbolt root@165.22.146.182
# OR if direct from M1:
ssh -R 12434:localhost:11434 root@165.22.146.182
```

## Coolify Environment Variables

Add these in Coolify dashboard → Application → Environment:

```env
OLLAMA_HOST=http://host.docker.internal:11434
M1_OLLAMA=http://host.docker.internal:12434
AUTO_INGEST_DIR=/app/auto_ingest
```

## Testing After Deployment

1. **Dashboard**: https://swaynesystems.ai/ → Should load normally
2. **Frontier Lab**: https://swaynesystems.ai/lab → Should show Sterling Estate Office
3. **Test Oracle**: Enable Oracle toggle, ask a complex question
4. **Test Council**: Enable Council, ask a question  
5. **Test Vision**: Upload an image in Vision Agent section

## Rollback if Needed

```bash
cd /Users/daviddswayne/.gemini/antigravity/scratch/sterling_lab

# Restore from backup (if you created one)
git revert HEAD
git push origin main
git push live main
```

## What Was Changed

- ✅ `chat_app.py` replaced with Frontier Lab
- ✅ `chroma_db_synthetic` added (106 synthetic nodes)
- ✅ `auto_ingest` directory created
- ✅ pysqlite3 fix added for Docker
- ✅ Paths updated for production
- ✅ Ollama hosts use tunnel endpoints

## Next Steps

1. Set up M1 tunnel (Terminal 2 above)
2. Add environment variables in Coolify
3. Push to deploy
4. Test all features
