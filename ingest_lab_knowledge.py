#!/usr/bin/env python3
"""
Ingest Lab Knowledge to Public ChromaDB
Creates a separate knowledge base for the public Antigravity chat
"""

import os
import sys
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_FILE = os.path.join(SCRIPT_DIR, "lab_knowledge_synthetic.txt")
CHROMA_PATH = os.path.join(SCRIPT_DIR, "chroma_db_public")
EMBEDDING_MODEL = "nomic-embed-text"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

def ingest_knowledge():
    """Ingest lab knowledge into public ChromaDB."""
    print("=" * 60)
    print("🔬 Lab Knowledge Ingestion for Public Chr omaDB")
    print("=" * 60)
    
    # Read knowledge file
    print(f"\n📖 Reading knowledge from: {KNOWLEDGE_FILE}")
    with open(KNOWLEDGE_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"✅ Loaded {len(content)} characters")
    
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
    
    # Split text into chunks
    print(f"\n✂️  Splitting text into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""]
    )
    
    chunks = text_splitter.split_text(content)
    print(f"✅ Created {len(chunks)} chunks")
    
    # Create documents
    documents = [
        Document(
            page_content=chunk,
            metadata={
                "source": "lab_knowledge_synthetic.txt",
                "chunk_id": i,
                "type": "public_knowledge"
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
        
        # Test retrieval
        print(f"\n🧪 Testing retrieval...")
        test_query = "What is Council mode?"
        results = db.similarity_search(test_query, k=2)
        print(f"✅ Retrieved {len(results)} results for '{test_query}'")
        print(f"   First result preview: {results[0].page_content[:100]}...")
        
    except Exception as e:
        print(f"❌ ChromaDB error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ PUBLIC KNOWLEDGE BASE INGESTION COMPLETE!")
    print(f"📊 Total documents: {len(documents)}")
    print(f"💾 Database location: {CHROMA_PATH}")
    print("=" * 60)

if __name__ == "__main__":
    ingest_knowledge()
