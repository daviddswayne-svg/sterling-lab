from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

import os

# Configuration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(SCRIPT_DIR, "chroma_db")
# MUST match the embedding model used during ingestion (ingest_sterling.py)
EMBEDDING_MODEL = "nomic-embed-text" 
LLM_MODEL = "llama3.3:latest"

def verify_llm_access():
    print(f"--- Setting up RAG with LLM: {LLM_MODEL} ---")
    
    # 1. Initialize Embeddings
    print(f"Initializing Embeddings ({EMBEDDING_MODEL})...")
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    
    # 2. Load Vector DB
    print(f"Loading Chroma DB from {CHROMA_PATH}...")
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)
    
    # 3. Initialize LLM
    print(f"Initializing LLM ({LLM_MODEL})...")
    llm = ChatOllama(model=LLM_MODEL, temperature=0)
    
    # 4. Create Retriever
    retriever = db.as_retriever(search_kwargs={"k": 10})
    
    # 5. Create Chain
    # Using a simple RetrievalQA chain for verification
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True
    )
    
    # 6. Run Query
    query = "Please give some family financial advice based on the estate"
    print(f"\nQuerying: '{query}'\n")
    
    try:
        response = qa_chain.invoke({"query": query})
        
        answer = response.get("result")
        source_docs = response.get("source_documents", [])
        
        print("-" * 30)
        print("LLM ANSWER:")
        print(answer)
        print("-" * 30)
        
        print("\nSource Documents Used:")
        for i, doc in enumerate(source_docs):
            source = doc.metadata.get("source", "Unknown")
            print(f"[{i+1}] {source}")
            
    except Exception as e:
        print(f"Error during query execution: {e}")

if __name__ == "__main__":
    verify_llm_access()
