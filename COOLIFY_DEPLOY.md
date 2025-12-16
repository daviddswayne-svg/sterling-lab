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
2. **Port**: `8501`
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
