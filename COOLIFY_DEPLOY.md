# Coolify Deployment Guide for Sterling Lab

## Step 1: Access Coolify
Open your browser to: **http://165.22.146.182:8000**

## Step 2: Create New Project
1. Click **"+ New"** → **"Project"**
2. Name it: `Sterling Lab`

## Step 3: Add GitHub Repository
1. In the project, click **"+ New"** → **"Application"**
2. Select **"Public Repository"** (or connect your GitHub account)
3. Enter repository URL: `https://github.com/YOUR_USERNAME/sterling_lab`
   - Replace with your actual GitHub repo URL
4. Branch: `main`

## Step 4: Configure Build Settings
1. **Build Pack**: Select **"Dockerfile"**
2. **Port**: `80` ⚠️ **CRITICAL: Must be 80, NOT 8501!**
   - Port 80 = Nginx (serves dashboard + proxies Streamlit)
   - Port 8501 = Streamlit only (bypasses dashboard)
3. **Domain**: `swaynesystems.ai` (or click to auto-generate)

## Step 5: Environment Variables
Add these if using SSH tunnel to Mac Studio:
```
OLLAMA_HOST=http://host.docker.internal:11434
```

**Note**: You'll need to configure Docker to allow container → host access, OR install Ollama in the container.

## Step 6: Enable Auto-Deploy
1. Go to **"Source"** tab
2. Enable **"Automatic Deployment"**
3. Coolify will create a webhook in your GitHub repo

## Step 7: Deploy
Click **"Deploy"** button

Coolify will:
- Pull from GitHub
- Build the Docker image
- Start the container
- Provision Let's Encrypt certificate
- Route traffic from swaynesystems.ai

## Accessing Your App
Once deployed: **https://swaynesystems.ai**

## AI Agent Workflow
Your AI agents can now:
```bash
git add .
git commit -m "AI update: ..."
git push origin main
```
→ Coolify automatically deploys!

## Important: SSH Tunnel Consideration
Since you're using SSH tunnel to Mac Studio for Ollama, you have 2 options:

**Option A: Continue using tunnel**
- Need to configure Docker networking to access host
- Add `--add-host=host.docker.internal:host-gateway` to container

**Option B: Install Ollama in container** 
- Pull models into container (requires significant space)
- Slower performance than Mac Studio

Recommend **Option A** - I can help configure after initial Coolify setup.

---

## Verifying Successful Deployment

### Check Startup Logs

After deployment, immediately check if all services started correctly:

```bash
# Find container
docker ps | grep sterling

# View startup sequence
docker logs <container_id> --tail 100
```

**Expected Output:**
```
==================================
🚀 STERLING LAB STARTUP SEQUENCE
==================================

[1/7] Running RAG System Diagnostics...
[2/7] Verifying Dashboard Files...
✅ Dashboard files verified at /app/dashboard
[3/7] Testing Nginx Configuration...
✅ Nginx config is valid
[4/7] Starting Streamlit on port 8501...
✅ Streamlit started with PID: 123
[5/7] Waiting for Streamlit to be ready...
✅ Streamlit is responding on port 8501
[6/7] Starting Nginx on port 80...
✅ Nginx started with PID: 456
[7/7] Verifying Nginx is serving traffic...
✅ Dashboard is accessible at /
✅ Streamlit proxy is accessible at /lab
==================================
✅ ALL SERVICES STARTED SUCCESSFULLY
```

> **If you see any ❌ FATAL errors**, the logs will show exactly what failed.

---

## Troubleshooting RAG Issues

### Pre-Deployment Checklist

Before deploying, ensure these requirements are met:

1. **✅ Embedding Model on Mac Studio**
   ```bash
   # SSH to Mac Studio
   ollama list | grep nomic
   ```
   - Should show: `nomic-embed-text` or `nomic-embed-text:latest`
   - If missing: `ollama pull nomic-embed-text`

2. **✅ SSH Tunnel Active**
   ```bash
   # On deployment server
   curl http://localhost:11434/api/version
   ```
   - Should return: `{"version":"0.x.x"}`
   - Verify tunnel in `/var/log/sterling-tunnel.log`

3. **✅ ChromaDB Populated**
   ```bash
   # Local machine
   ls -la chroma_db/
   ```
   - Should show: `chroma.sqlite3` and UUID directory
   - If empty: Run `python ingest_sterling.py`

### Diagnostic Commands

Run these inside the deployed container:

```bash
# Find container ID
docker ps | grep sterling

# Run diagnostics
docker exec <container_id> python rag_diagnostics.py

# Check logs
docker logs <container_id> --tail 100
```

### Common Issues

#### Issue: "RAG returns zero documents"

**Symptom**: "View Source Documents" expander is empty
**Cause**: Embedding model unavailable on Mac Studio
**Fix**:
```bash
# On Mac Studio
ollama pull nomic-embed-text

# Verify from droplet
curl -X POST http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"test"}'
# Should return: {"embedding":[...]}
```

#### Issue: "Connection to Ollama failed"

**Symptom**: `❌ Ollama: Unreachable` in System Diagnostics
**Cause**: SSH tunnel down or `OLLAMA_HOST` misconfigured
**Fix**:
1. Check environment variable in Coolify:
   - Go to Application → Environment
   - Verify: `OLLAMA_HOST=http://host.docker.internal:11434`
2. Restart tunnel on Mac Studio:
   ```bash
   ssh -R 11434:localhost:11434 root@165.22.146.182
   ```

#### Issue: "ChromaDB not found"

**Symptom**: `❌ ChromaDB: NOT FOUND` 
**Cause**: `chroma_db/` not committed to Git or `.gitignore` blocking it
**Fix**:
```bash
# Check if in Git
git ls-files | grep chroma_db

# If missing, add and push
git add chroma_db/
git commit -m "Add populated ChromaDB"
git push origin main
```

### Debug Mode

To get verbose RAG output, add this to Coolify environment:
```
STREAMLIT_LOGGER_LEVEL=debug
```

Then check container logs for detailed ChromaDB queries.
