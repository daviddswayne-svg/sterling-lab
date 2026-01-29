# MCP Chat - Model Context Protocol Agent

## Overview

MCP Chat is a tool-augmented AI chat interface that replaces traditional RAG (Retrieval-Augmented Generation) with real-time tool execution. Instead of searching a local vector database, the agent fetches **live data** from external sources, eliminating hallucinations.

**Live at:** https://swaynesystems.ai/lab

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Question                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Tool Decision Model                          │
│                      (qwen2.5:14b)                              │
│                                                                 │
│  Analyzes the question and decides which tools to call          │
│  Returns structured tool_calls with function names and args     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Tool Execution                              │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Exa Search  │  │   GitHub    │  │  (Future)   │            │
│  │             │  │   Repos     │  │             │            │
│  │ Real-time   │  │   Commits   │  │ More tools  │            │
│  │ web search  │  │             │  │             │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Synthesis Model                               │
│                     (gemma2:27b)                                │
│                                                                 │
│  Takes tool results + original question                         │
│  Generates a coherent, well-formatted response                  │
│  Streams tokens in real-time for fast UX                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      User Response                              │
│                                                                 │
│  - Formatted answer with markdown                               │
│  - Expandable "Agent Actions" showing tool trace                │
│  - Links and structured data from tools                         │
└─────────────────────────────────────────────────────────────────┘
```

## Two-Model Approach

The system uses two specialized models for optimal performance:

| Model | Role | Why |
|-------|------|-----|
| `qwen2.5:14b` | Tool Decisions | Fast, excellent at function calling and structured output |
| `gemma2:27b` | Response Synthesis | Fast streaming, natural language generation |

This separation allows each model to do what it's best at, resulting in faster responses than using a single large model for everything.

## Available Tools

### 1. Exa Search (`search_web`)

Semantic web search powered by [Exa](https://exa.ai). Returns real, verified search results.

```json
{
  "name": "search_web",
  "parameters": {
    "query": "string - the search query",
    "num_results": "integer - 1-10, default 5"
  }
}
```

**Example queries:**
- "Search for the latest MCP protocol documentation"
- "Find information about Anthropic Claude"

### 2. GitHub Repos (`github_repos`)

Lists repositories for a GitHub user or organization.

```json
{
  "name": "github_repos",
  "parameters": {
    "username": "string - GitHub username or org"
  }
}
```

**Example:** "Show me my GitHub repositories"

### 3. GitHub Commits (`github_commits`)

Gets recent commits from a repository.

```json
{
  "name": "github_commits",
  "parameters": {
    "repo": "string - format: owner/repo",
    "limit": "integer - default 5"
  }
}
```

**Example:** "What are the recent commits in daviddswayne-svg/sterling-lab?"

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OLLAMA_HOST` | Yes | Ollama API endpoint (default: `http://host.docker.internal:11434`) |
| `EXA_API_KEY` | Yes | API key for Exa search |
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Optional | GitHub token for repo/commit access |

### Models (in `chat_app.py`)

```python
TOOL_MODEL = "qwen2.5:14b"   # For tool-calling decisions
SYNTH_MODEL = "gemma2:27b"   # For synthesizing responses
```

## File Structure

```
sterling-lab/
├── chat_app.py          # Main MCP chat application
├── requirements.txt     # Python dependencies (minimal, no ChromaDB)
├── start.sh            # Docker startup script
├── Dockerfile          # Container configuration
└── MCP_CHAT.md         # This documentation
```

## Adding New Tools

1. **Define the tool** in the `TOOLS` list:

```python
{
    "type": "function",
    "function": {
        "name": "my_new_tool",
        "description": "What this tool does - be specific for the LLM",
        "parameters": {
            "type": "object",
            "properties": {
                "param1": {"type": "string", "description": "What this param is for"}
            },
            "required": ["param1"]
        }
    }
}
```

2. **Implement execution** in `execute_tool()`:

```python
elif name == "my_new_tool":
    # Your implementation here
    result["success"] = True
    result["data"] = your_data
```

3. **Format the output** in `format_tool_result()`:

```python
elif name == "my_new_tool":
    lines = ["My tool results:"]
    for item in data:
        lines.append(f"- {item}")
    return "\n".join(lines)
```

## Deployment

### Docker (Coolify)

The app runs in a Docker container with:
- Streamlit on port 8501 (proxied via Nginx)
- Nginx on port 80 (main entry point)

### Git Remotes

```bash
# Push to both GitHub (backup) and live server (deploy)
git push origin main && git push live main
```

### Server Maintenance

```bash
# Clean up Docker images if deployment fails
ssh -i ~/.ssh/sterling_tunnel root@165.22.146.182 "docker system prune -a -f"
```

## Why MCP Over RAG?

| Aspect | RAG | MCP |
|--------|-----|-----|
| Data freshness | Stale (needs re-indexing) | Real-time |
| Hallucinations | Can hallucinate from bad chunks | Grounded in actual API responses |
| Setup complexity | Vector DB, embeddings, chunking | Just API keys |
| Response speed | Fast (local) | Depends on external APIs |
| Maintenance | Index updates, embedding model changes | API version updates |

For this project, MCP was chosen because:
1. **Freshness matters** - web search needs current results
2. **Accuracy matters** - GitHub data should be exact, not approximated
3. **Simplicity** - removed ~150 packages by dropping ChromaDB

## Troubleshooting

### "Tool error: Exa API key not configured"
Set `EXA_API_KEY` in environment variables.

### "TypeError: 'NoneType' object is not iterable"
Fixed in commit `0d9f264`. Update to latest version.

### First request fails with broken code
Cold start issue. The model sometimes returns raw JSON on first request. Subsequent requests work fine.

### Build fails with memory error
The requirements.txt has been trimmed. If issues persist:
```bash
ssh -i ~/.ssh/sterling_tunnel root@165.22.146.182 "docker system prune -a -f"
```

## Future Enhancements

- [ ] Add filesystem tool for local file access
- [ ] Add DeepSeek R1 for deep reasoning (via M1 Ultra)
- [ ] Add weather/location tools
- [ ] Add calendar/scheduling tools
- [ ] Implement tool chaining (use output of one tool as input to another)

---

*Last updated: January 2026*
*Part of the Swayne Systems AI Lab project*
