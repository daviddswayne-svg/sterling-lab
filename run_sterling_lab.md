---
description: Run the Sterling Lab RAG Protocol (Local LLM + Chat App)
---

# Sterling Lab Protocol

This workflow outlines the steps to run the Sterling Lab local RAG system, including data ingestion, verification, and the persistent chat interface.

## 1. Prerequisites
- **OS**: macOS (recommended)
- **Repo/Folder**: `sterling_lab` (located in scratch or home)
- **Local LLM**: Ollama installed with `llama3.3:latest` and `nomic-embed-text`.
- **Python**: 3.9+ with `venv`.

## 2. Setup & Installation
If running for the first time:

```bash
cd /Users/daviddswayne/.gemini/antigravity/scratch/sterling_lab
python3 -m venv venv
source venv/bin/activate
pip install langchain-chroma langchain-ollama langchain-community unstructured markdown streamlit
ollama pull nomic-embed-text
ollama pull llama3.3:latest
```

## 3. Data Ingestion (ResetDB)
To process the raw files (`.txt`, `.csv`, `.eml`, `.md`) into the vector database (`chroma_db`):

```bash
# This will wipe existing chroma_db and re-create it
./venv/bin/python ingest_sterling.py
```

**Verification**: Ensure `./chroma_db` folder exists after running.

## 4. Backend Verification
To test if the LLM can access the data without the UI:

```bash
./venv/bin/python verify_llm.py
```
*Expected Output*: "The Blue Envelope is hidden..."

## 5. Run Chat Application
To start the persistent web interface:

```bash
./venv/bin/streamlit run chat_app.py
```
- **URL**: `http://localhost:8501`
- **Features**: Chat history is saved to `chat_history.db`.
- **Debugging**: Check the sidebar to see which source documents were retrieved for the answer.
