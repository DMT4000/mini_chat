from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
print("🔍 Loading .env file...")
try:
    # Try multiple approaches to load the .env file
    load_dotenv()
    load_dotenv('.env')
    load_dotenv(Path('.env'))
    
    # Manual fallback: read .env file directly
    if not os.getenv("OPENAI_API_KEY"):
        print("🔍 Trying manual .env file reading...")
        try:
            with open('.env', 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"📄 .env file content length: {len(content)}")
                lines = content.split('\n')
                print(f"📄 Number of lines: {len(lines)}")
                for i, line in enumerate(lines):
                    # Handle BOM and check for OPENAI_API_KEY
                    line_clean = line.strip()
                    if line_clean.startswith('OPENAI_API_KEY=') or line_clean.startswith('\ufeffOPENAI_API_KEY='):
                        # Remove BOM if present and get the API key
                        if line_clean.startswith('\ufeffOPENAI_API_KEY='):
                            api_key = line_clean[len('\ufeffOPENAI_API_KEY='):].strip()
                        else:
                            api_key = line_clean[len('OPENAI_API_KEY='):].strip()
                        os.environ['OPENAI_API_KEY'] = api_key
                        print(f"✅ API key loaded manually from line {i+1}")
                        print(f"🔑 API key starts with: {api_key[:10]}...")
                        break
                else:
                    print("❌ No OPENAI_API_KEY found in .env file")
        except Exception as e:
            print(f"⚠️ Manual .env reading failed: {e}")
    
    print("✅ .env file loaded successfully")
except Exception as e:
    print(f"⚠️ Warning: Could not load .env file: {e}")

def build_index(src_dir="docs", index_path="faiss_index"):
    # Load all text files from the docs directory
    docs = []
    docs_path = Path(src_dir)
    
    if not docs_path.exists():
        print(f"❌ Directory {src_dir} does not exist")
        return
    
    for file_path in docs_path.glob("*.txt"):
        try:
            loader = TextLoader(str(file_path))
            docs.extend(loader.load())
            print(f"✅ Loaded: {file_path}")
        except Exception as e:
            print(f"❌ Error loading {file_path}: {e}")
    
    if not docs:
        print("❌ No documents found to process")
        return
    
    # Check if OpenAI API key is set
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"🔑 API Key loaded: {'Yes' if api_key and api_key != 'your_openai_api_key_here' else 'No'}")
    if api_key:
        print(f"🔑 API Key starts with: {api_key[:10]}...")
    
    if not api_key or api_key == "your_openai_api_key_here":
        print("❌ OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key:")
        print("  Windows: set OPENAI_API_KEY=your_api_key_here")
        print("  Linux/Mac: export OPENAI_API_KEY=your_api_key_here")
        print("  Or create a .env file with: OPENAI_API_KEY=your_api_key_here")
        return
    
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        vector = FAISS.from_documents(docs, embeddings)
        vector.save_local(index_path)
        print("✅ index built:", index_path)
    except Exception as e:
        print(f"❌ Error building index: {e}")
        print("Please check your OpenAI API key is valid")

if __name__ == "__main__":
    build_index()
