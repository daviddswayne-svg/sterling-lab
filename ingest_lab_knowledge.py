#!/usr/bin/env python3
"""
Ingest Complete Lab Knowledge to Public ChromaDB
Includes ALL documentation: README, SITE_KNOWLEDGE, deployment guides, etc.
"""

import os
import sys
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_FILE = os.path.join(SCRIPT_DIR, "lab_knowledge_complete.txt")
CHROMA_PATH = os.path.join(SCRIPT_DIR, "chroma_db_public")
EMBEDDING_MODEL = "nomic-embed-text"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

def ingest_knowledge():
    """Ingest complete lab knowledge into public ChromaDB."""
    print("=" * 60)
    print("🔬 COMPLETE Lab Knowledge Ingestion")
    print("=" * 60)
    
    # Read knowledge file
    print(f"\n📖 Reading comprehensive knowledge from: {KNOWLEDGE_FILE}")
    with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"✅ Loaded {len(content)} characters ({len(content.split())} words)")
    
    # Initialize embeddings
    print(f"\n🔗 Connecting to Ollama at {OLLAMA_HOST}")
    print(f"📊 Using embedding model: {EMBEDDING_MODEL}")
    
    try:
        embeddings = OllamaEmbeddings(
            model=EMBEDDING_MODEL,
            base_url=OLLAMA_HOST
        )
    except Exception as e:
        print(f"❌ Failed to connect to Ollama: {e}")
        print(f"💡 Ensure Ollama is running with: ollama serve")
        print(f"💡 And model is available: ollama pull {EMBEDDING_MODEL}")
        sys.exit(1)
    
    # Split text with improved chunking
    print(f"\n✂️  Splitting text into semantic chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,  # Optimal size for coherent sections
        chunk_overlap=150,  # Good overlap to preserve context across chunks
        separators=["\n## ", "\n### ", "\n#### ", "\n\n", "\n", ". ", " ", ""],
        length_function=len
    )
    
    chunks = text_splitter.split_text(content)
    print(f"✅ Created {len(chunks)} chunks")
    print(f"   Average chunk size: {len(content) // len(chunks)} characters")
    
    # Create documents
    documents = [
        Document(
            page_content=chunk,
            metadata={
                "source": "comprehensive_lab_docs",
                "chunk_id": i,
                "type": "public_knowledge",
                "total_chunks": len(chunks)
            }
        )
        for i, chunk in enumerate(chunks)
    ]
    
    # Create/update ChromaDB
    print(f"\n💾 Storing in ChromaDB at: {CHROMA_PATH}")
    
    try:
        db = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=CHROMA_PATH
        )
        print(f"✅ Successfully ingested {len(documents)} documents")
        
        # Test retrieval with multiple queries
        print(f"\n🧪 Testing retrieval with sample questions...")
        
        test_queries = [
            "What is Council mode?",
            "How do I deploy to Coolify?",
            "What models are available?",
            "Tell me about the architecture"
        ]
        
        for query in test_queries:
            results = db.similarity_search(query, k=2)
            print(f"\n   Q: '{query}'")
            print(f"   → Retrieved {len(results)} results")
            print(f"   → First result: {results[0].page_content[:80]}...")
        
    except Exception as e:
        print(f"❌ ChromaDB error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ COMPREHENSIVE KNOWLEDGE BASE INGESTION COMPLETE!")
    print(f"📊 Total documents: {len(documents)}")
    print(f"📄 Source characters: {len(content):,}")
    print(f"💾 Database location: {CHROMA_PATH}")
    print("=" * 60)

if __name__ == "__main__":
    ingest_knowledge()
