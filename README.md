# Sterling Lab - AI-Powered Estate Intelligence

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

### Docker (Coolify)
```bash
# Automatic deployment via Coolify
# Push to main branch → auto-deploys
```

### Manual (Traditional)
```bash
git push live main  # Deploys to swaynesystems.ai:8443
```

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
git push origin main
```
→ Coolify automatically deploys changes

---

Built with ❤️ for the Sterling Estate
