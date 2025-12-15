import os
import shutil
from langchain_community.document_loaders import TextLoader,  UnstructuredMarkdownLoader, UnstructuredEmailLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

# Determine script directory to safely locate files
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILES = [
    (os.path.join(SCRIPT_DIR, "Last_Will_2020.txt"), TextLoader),
    (os.path.join(SCRIPT_DIR, "Assets_Estimate.csv"), CSVLoader),
    (os.path.join(SCRIPT_DIR, "Secret_Email.eml"), UnstructuredEmailLoader),
    (os.path.join(SCRIPT_DIR, "Groundskeeper_Log.md"), UnstructuredMarkdownLoader),
]
CHROMA_PATH = os.path.join(SCRIPT_DIR, "chroma_db")
EMBEDDING_MODEL = "nomic-embed-text:latest"

def ingest_data():
    print("--- 0. DEBUG: Checking Ollama Connection ---")
    import os
    print(f"OLLAMA_HOST: {os.environ.get('OLLAMA_HOST', 'Not Set')}")
    
    try:
        from ollama import Client
        client = Client(host='http://localhost:11434')
        print("Available Models (via ollama lib):")
        print(client.list())
    except Exception as e:
        print(f"DEBUG: Ollama lib failed: {e}")

    print("--- 1. Loading Documents ---")
    documents = []
    for filename, LoaderClass in DATA_FILES:
        if os.path.exists(filename):
            print(f"Loading {filename}...")
            try:
                loader = LoaderClass(filename)
                documents.extend(loader.load())
            except Exception as e:
                print(f"Error loading {filename}: {e}")
        else:
            print(f"Warning: {filename} not found.")

    print(f"Loaded {len(documents)} document(s).")

    print("--- 2. Splitting Text ---")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks.")

    print("--- 3. Vectorizing & Persisting (Chroma) ---")
    # Clean up existing DB if wanted, or just append. 
    # For this test kit, let's clear it to ensure fresh start.
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    
    # Batch add to Chroma
    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH
    )
    print(f"Database persisted to {CHROMA_PATH}")
    return db

def query_database(db):
    print("--- 4. Querying: 'Where is the blue envelope?' ---")
    query = "Where is the blue envelope?"
    results = db.similarity_search(query, k=3)
    
    print("\nTop Answers Found:")
    for i, res in enumerate(results):
        print(f"\n[{i+1}] Source: {res.metadata.get('source', 'Unknown')}")
        print(f"Content: {res.page_content.strip()}")

if __name__ == "__main__":
    if not os.path.exists("./chroma_db"):
        print("Initializing Database...")
        db = ingest_data()
    else:
        # If we didn't want to re-ingest every time, we'd load here. 
        # But for the test kit, let's always re-ingest to be safe.
        db = ingest_data()
    
    query_database(db)
