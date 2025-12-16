# Sterling Lab - AI-Powered Estate Intelligence

> [!CAUTION]
> **CRITICAL: This repo has TWO Git remotes**  
> - `origin` → GitHub (**BACKUP ONLY** - does NOT deploy)
> - `live` → Server (**ACTUAL DEPLOYMENT** - this deploys to swaynesystems.ai)
> 
> **Always push to BOTH:**
> ```bash
> git push origin main && git push live main
> ```

Intelligent RAG (Retrieval-Augmented Generation) system for the Sterling Estate, powered by multiple LLM models through a distributed "Council Mode" architecture.

## Features

- **Council Mode**: Multi-agent system with specialized AI personas (Consultant, Analyst, Maverick)
- **RAG Pipeline**: ChromaDB vector database with 8+ estate documents
- **Real-time Streaming**: Live AI responses with token counting
- **Distributed Architecture**: Mac Studio AI backend via SSH tunnel
- **Knowledge Sources**: Internal ChromaDB + PrivateGPT integration

## Architecture

- **Frontend**: Streamlit web interface
- **AI Backend**: Mac Studio M3 via SSH tunnel (port 11434)
- **Models**: llama3.3:70b, qwen2.5-coder:32b, dolphin-llama3, nomic-embed-text
- **Database**: ChromaDB for vector storage, SQLite for chat history

## Deployment

**IMPORTANT:** Must push to `live` remote for deployment (Coolify uses this, NOT GitHub)

```bash
# Correct deployment workflow:
git add .
git commit -m "Your message"
git push origin main  # Backup to GitHub
git push live main    # Deploy to swaynesystems.ai (REQUIRED!)

# Or shorthand to push to both:
git push --all
```

See [COOLIFY_DEPLOY.md](COOLIFY_DEPLOY.md) for full deployment guide.

## Environment Variables

```env
OLLAMA_HOST=http://host.docker.internal:11434  # For Docker deployment
```

## Live Site

- **Production**: https://swaynesystems.ai (via Coolify)
- **Legacy**: https://swaynesystems.ai:8443 (direct Caddy)

## AI Agent Workflow

AI agents can auto-update by:
```bash
git add .
git commit -m "AI update: [description]"
git push origin main  # Backup
git push live main    # Deploy (REQUIRED!)
```
→ Coolify automatically deploys from `live` remote

---

Built with ❤️ for the Sterling Estate
