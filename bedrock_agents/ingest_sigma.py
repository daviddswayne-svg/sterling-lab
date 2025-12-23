import os
import sys

# Add parent directory to path to allow importing config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from bedrock_agents.config import DATA_DIR, BEDROCK_CHROMA_PATH, OLLAMA_HOST

def ingest_report():
    pdf_path = os.path.join(DATA_DIR, "sigma_5_2024_outlook.pdf")
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found at {pdf_path}")
        return

    print(f"📄 Loading PDF: {pdf_path}")
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    print(f"   - Loaded {len(docs)} pages.")

    print("✂️  Splitting text...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        add_start_index=True
    )
    splits = text_splitter.split_documents(docs)
    print(f"   - Created {len(splits)} chunks.")

    print(f"💾 Ingesting into ChromaDB at {BEDROCK_CHROMA_PATH}...")
    try:
        embeddings = OllamaEmbeddings(model="nomic-embed-text", base_url=OLLAMA_HOST)
        
        # Clear existing DB to avoid duplicates if re-running (optional, but good for dev)
        # shutil.rmtree(BEDROCK_CHROMA_PATH, ignore_errors=True) 

        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=BEDROCK_CHROMA_PATH
        )
        print("✅ Ingestion Complete!")
        
        # Quick Test
        print("\n🧪 Verifying with test query 'risks'...")
        results = vectorstore.similarity_search("What are the top risks for 2025?", k=1)
        if results:
            print(f"   - Match found: {results[0].page_content[:100]}...")
        else:
            print("   - ⚠️ No results returned from test query.")
            
    except Exception as e:
        print(f"❌ Ingestion Failed: {e}")

if __name__ == "__main__":
    ingest_report()
