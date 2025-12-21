#!/usr/bin/env python3
"""Test public RAG system locally"""

import os
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from ollama import Client

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(SCRIPT_DIR, "chroma_db_public")
OLLAMA_HOST = "http://localhost:11434"

print("🧪 Testing Public RAG System\n")
print(f"ChromaDB Path: {CHROMA_PATH}")
print(f"Exists: {os.path.exists(CHROMA_PATH)}\n")

# Load ChromaDB
embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_HOST)
db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)

# Test query
test_question = "What is Council mode?"
print(f"Test Question: '{test_question}'\n")

# Retrieve
relevant_docs = db.similarity_search(test_question, k=3)
print(f"Retrieved {len(relevant_docs)} documents:\n")

for i, doc in enumerate(relevant_docs, 1):
    print(f"--- Document {i} ---")
    print(f"Content: {doc.page_content[:200]}...")
    print(f"Metadata: {doc.metadata}\n")

# Build context
context = "\n\n".join([doc.page_content for doc in relevant_docs])
print(f"Total context length: {len(context)} characters\n")

# Test with Qwen
print("Querying Qwen with context...\n")

messages = [
    {
        "role": "system",
        "content": "You are a helpful AI assistant for Swayne Systems. Use the provided context to answer accurately. Keep responses concise (2-3 paragraphs)."
    },
    {
        "role": "user",
        "content": f"CONTEXT:\n{context}\n\nQUESTION: {test_question}"
    }
]

client = Client(host=OLLAMA_HOST)
response = client.chat(
    model='qwen2.5-coder:32b',
    messages=messages,
    stream=False
)

print("RESPONSE:")
print(response['message']['content'])
