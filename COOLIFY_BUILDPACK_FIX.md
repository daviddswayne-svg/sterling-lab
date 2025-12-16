# ⚠️ CRITICAL FIX NEEDED IN COOLIFY UI

## Problem

The deployment is using **Python buildpack** (auto-detected) instead of **Dockerfile**.

Evidence: Error shows `/var/www/swaynesystems.ai/venv/` which means pip is installing packages, NOT Docker.

## Fix Required

### Step 1: Change Build Pack in Coolify UI

1. Go to Coolify: `http://165.22.146.182:8000`
2. Navigate to Sterling Lab application
3. Go to **Configuration** tab
4. Find **"Build Pack"** setting
5. **Change from "Python" (or "Nixpacks") to "Dockerfile"**
6. Save and **Redeploy**

### Step 2: Verify Docker Build

After redeployment, check that:
- Build logs show Docker building FROM python:3.12-slim
- No mention of venv or pip installing directly
- Container runs our start.sh script

## Why This Matters

**Python Buildpack:**
- Auto-detects Python, creates venv
- Installs requirements.txt to venv
- Doesn't use Dockerfile, nginx.conf, or start.sh
- Missing Nginx = no dashboard routing

**Dockerfile Mode:**
- Uses our Dockerfile
- Installs Nginx
- Runs our 7-step startup verification
- Dashboard at /, Streamlit at /lab

## Alternative: Add .coolify File

I've created `.coolify` file with:
```
buildPack: dockerfile
```

But Coolify's UI setting likely overrides this. **Manual UI change is required.**
