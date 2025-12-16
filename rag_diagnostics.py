#!/usr/bin/env python3
"""
RAG System Diagnostics for Sterling Lab
Tests all components of the RAG pipeline to identify issues.
"""

import os
import sys
import requests
from pathlib import Path

# Color codes for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_status(check_name, passed, message=""):
    """Print formatted status line."""
    status = f"{GREEN}✅ PASS{RESET}" if passed else f"{RED}❌ FAIL{RESET}"
    print(f"{status} | {check_name}")
    if message:
        print(f"       {message}")

def test_ollama_connection(host):
    """Test connection to Ollama API."""
    print(f"\n{BOLD}[1] Testing Ollama Connection{RESET}")
    print(f"    Host: {host}")
    
    try:
        response = requests.get(f"{host}/api/version", timeout=5)
        if response.status_code == 200:
            version = response.json().get('version', 'Unknown')
            print_status("Ollama API Reachable", True, f"Version: {version}")
            return True
        else:
            print_status("Ollama API Reachable", False, f"HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_status("Ollama API Reachable", False, f"Cannot connect to {host}")
        return False
    except Exception as e:
        print_status("Ollama API Reachable", False, str(e))
        return False

def test_embedding_model(host, model_name):
    """Test if embedding model is available."""
    print(f"\n{BOLD}[2] Testing Embedding Model{RESET}")
    print(f"    Model: {model_name}")
    
    try:
        response = requests.get(f"{host}/api/tags", timeout=5)
        if response.status_code != 200:
            print_status("Fetch Model List", False, f"HTTP {response.status_code}")
            return False
        
        models = [m['name'] for m in response.json()['models']]
        
        # Check for exact match or with :latest tag
        found = False
        matched_name = None
        for model in models:
            if model == model_name or model == f"{model_name}:latest" or model.startswith(f"{model_name}:"):
                found = True
                matched_name = model
                break
        
        if found:
            print_status("Embedding Model Available", True, f"Found: {matched_name}")
            return True
        else:
            print_status("Embedding Model Available", False, 
                        f"'{model_name}' not found in: {', '.join(models[:5])}")
            print(f"\n{YELLOW}       💡 FIX: Run on Mac Studio:{RESET}")
            print(f"       ollama pull {model_name}")
            return False
            
    except Exception as e:
        print_status("Embedding Model Available", False, str(e))
        return False

def test_embedding_generation(host, model_name):
    """Test actual embedding generation."""
    print(f"\n{BOLD}[3] Testing Embedding Generation{RESET}")
    
    try:
        # Use Ollama's embed API
        payload = {
            "model": model_name,
            "prompt": "test query"
        }
        response = requests.post(f"{host}/api/embeddings", json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            embedding = data.get('embedding', [])
            if embedding and len(embedding) > 0:
                print_status("Generate Embeddings", True, f"Vector dim: {len(embedding)}")
                return True
            else:
                print_status("Generate Embeddings", False, "Empty embedding returned")
                return False
        else:
            print_status("Generate Embeddings", False, 
                        f"HTTP {response.status_code}: {response.text[:100]}")
            return False
            
    except Exception as e:
        print_status("Generate Embeddings", False, str(e))
        return False

def test_chromadb_presence(chroma_path):
    """Test if ChromaDB exists locally."""
    print(f"\n{BOLD}[4] Testing ChromaDB Presence{RESET}")
    print(f"    Path: {chroma_path}")
    
    if not os.path.exists(chroma_path):
        print_status("ChromaDB Directory", False, f"Path does not exist")
        print(f"\n{YELLOW}       💡 FIX: Run ingestion:{RESET}")
        print(f"       python ingest_sterling.py")
        return False
    
    # Check for essential files
    chroma_sqlite = os.path.join(chroma_path, "chroma.sqlite3")
    if not os.path.exists(chroma_sqlite):
        print_status("ChromaDB Files", False, "chroma.sqlite3 missing")
        return False
    
    # Count files
    file_count = sum([len(files) for r, d, files in os.walk(chroma_path)])
    print_status("ChromaDB Directory", True, f"{file_count} files found")
    return True

def test_chromadb_query(chroma_path, host, model_name):
    """Test actual ChromaDB query."""
    print(f"\n{BOLD}[5] Testing End-to-End RAG Retrieval{RESET}")
    print(f"    Query: 'Where is the blue envelope?'")
    
    try:
        from langchain_chroma import Chroma
        from langchain_ollama import OllamaEmbeddings
        
        embeddings = OllamaEmbeddings(model=model_name, base_url=host)
        db = Chroma(persist_directory=chroma_path, embedding_function=embeddings)
        
        results = db.similarity_search("Where is the blue envelope?", k=3)
        
        if len(results) == 0:
            print_status("ChromaDB Query", False, "Zero results returned")
            print(f"\n{YELLOW}       💡 This means:{RESET}")
            print(f"       - ChromaDB is loaded but retrieval fails")
            print(f"       - Likely cause: Embedding model mismatch or unavailable")
            return False
        
        print_status("ChromaDB Query", True, f"{len(results)} documents retrieved")
        
        # Show preview
        for i, doc in enumerate(results):
            source = doc.metadata.get('source', 'Unknown')
            preview = doc.page_content[:100].replace('\n', ' ')
            print(f"       [{i+1}] {source}: {preview}...")
        
        # Check if correct answer is in results
        correct_source = "Assets_Estimate.csv"
        found_correct = any(correct_source in doc.metadata.get('source', '') for doc in results)
        
        if found_correct:
            print(f"\n{GREEN}       ✓ Correct source document found!{RESET}")
        else:
            print(f"\n{YELLOW}       ⚠ Expected '{correct_source}' not in results{RESET}")
        
        return True
        
    except ImportError as e:
        print_status("ChromaDB Query", False, f"Missing dependency: {e}")
        print(f"\n{YELLOW}       💡 FIX: Install dependencies:{RESET}")
        print(f"       pip install langchain-chroma langchain-ollama")
        return False
    except Exception as e:
        print_status("ChromaDB Query", False, str(e))
        return False

def main():
    """Run all diagnostic tests."""
    print(f"{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}Sterling Lab RAG Diagnostics{RESET}")
    print(f"{BOLD}{'='*60}{RESET}")
    
    # Configuration
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    EMBEDDING_MODEL = "nomic-embed-text"
    CHROMA_PATH = os.path.join(SCRIPT_DIR, "chroma_db")
    
    print(f"\nConfiguration:")
    print(f"  OLLAMA_HOST: {OLLAMA_HOST}")
    print(f"  EMBEDDING_MODEL: {EMBEDDING_MODEL}")
    print(f"  CHROMA_PATH: {CHROMA_PATH}")
    
    # Run tests
    results = []
    
    results.append(test_ollama_connection(OLLAMA_HOST))
    results.append(test_embedding_model(OLLAMA_HOST, EMBEDDING_MODEL))
    
    # Only test embedding generation if previous tests passed
    if results[-1]:
        results.append(test_embedding_generation(OLLAMA_HOST, EMBEDDING_MODEL))
    else:
        print(f"\n{YELLOW}[3] Skipping embedding generation test (model not available){RESET}")
        results.append(False)
    
    results.append(test_chromadb_presence(CHROMA_PATH))
    
    # Only test query if all previous tests passed
    if all(results):
        results.append(test_chromadb_query(CHROMA_PATH, OLLAMA_HOST, EMBEDDING_MODEL))
    else:
        print(f"\n{YELLOW}[5] Skipping end-to-end test (prerequisites failed){RESET}")
        results.append(False)
    
    # Summary
    print(f"\n{BOLD}{'='*60}{RESET}")
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"{GREEN}{BOLD}✅ ALL CHECKS PASSED ({passed}/{total}){RESET}")
        print(f"\n{GREEN}Your RAG system is properly configured!{RESET}")
        return 0
    else:
        print(f"{RED}{BOLD}❌ SOME CHECKS FAILED ({passed}/{total}){RESET}")
        print(f"\n{YELLOW}Please fix the issues above and re-run this script.{RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
