from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader
from pathlib import Path
import os
import re
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
            print(f"⚠️ Manual .env file reading failed: {e}")
    
    print("✅ .env file loaded successfully")
except Exception as e:
    print(f"⚠️ Warning: Could not load .env file: {e}")

def clean_text(text):
    """Clean and normalize extracted text"""
    if not text:
        return ""
    
    # Remove excessive whitespace and newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Replace multiple newlines with double newlines
    text = re.sub(r' +', ' ', text)  # Replace multiple spaces with single space
    text = re.sub(r'\n +', '\n', text)  # Remove leading spaces after newlines
    text = re.sub(r' +\n', '\n', text)  # Remove trailing spaces before newlines
    
    # Clean up common PDF artifacts - fix broken words more aggressively
    text = re.sub(r'([a-zA-Z])\n([a-zA-Z])', r'\1 \2', text)  # Fix broken words (add space between letters)
    text = re.sub(r'([a-zA-Z])\s*\n\s*([a-zA-Z])', r'\1 \2', text)  # Fix broken words with spaces around newlines
    
    # Handle specific PDF formatting patterns - add spaces between words
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)  # Add space between lowercase and uppercase
    text = re.sub(r'([A-Z])([a-z])', r'\1 \2', text)  # Add space between uppercase and lowercase (but be careful)
    
    # Remove isolated characters that are likely artifacts
    text = re.sub(r'\n([a-zA-Z])\n', r' \1 ', text)
    text = re.sub(r'\s+([a-zA-Z])\s+', r' \1 ', text)  # Clean up single letters surrounded by spaces
    
    # Improve paragraph structure
    text = re.sub(r'\n{3,}', '\n\n', text)  # Limit consecutive newlines to 2
    
    # Clean up bullet points and lists
    text = re.sub(r'\n\s*●\s*\n', '\n• ', text)  # Convert bullet points
    text = re.sub(r'\n\s*-\s*\n', '\n- ', text)  # Convert dashes
    
    # Final cleanup
    text = text.strip()
    
    # Post-processing: improve readability
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line:
            # Skip lines that are just single characters or very short fragments
            if len(line) > 2 or line.isupper() or line.isdigit():
                cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Final text cleanup - remove extra spaces at word boundaries
    text = re.sub(r' ([A-Z])', r'\1', text)  # Remove space before capital letters
    text = re.sub(r' +', ' ', text)  # Clean up any remaining multiple spaces
    
    return text.strip()

def load_pdf_file(file_path):
    """Load PDF files with improved text extraction and cleaning"""
    try:
        # Try PyPDF2 first
        import PyPDF2
        docs = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            print(f"📖 Processing PDF: {file_path} ({len(pdf_reader.pages)} pages)")
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        # Clean the extracted text
                        cleaned_text = clean_text(text)
                        
                        if cleaned_text and len(cleaned_text.strip()) > 50:  # Only add substantial content
                            from langchain.schema import Document
                            docs.append(Document(
                                page_content=cleaned_text, 
                                metadata={"source": str(file_path), "page": page_num + 1}
                            ))
                            print(f"  ✅ Page {page_num + 1}: {len(cleaned_text)} chars")
                        else:
                            print(f"  ⚠️ Page {page_num + 1}: Insufficient content after cleaning")
                    else:
                        print(f"  ⚠️ Page {page_num + 1}: No text extracted")
                        
                except Exception as e:
                    print(f"  ❌ Error processing page {page_num + 1}: {e}")
                    continue
        
        if not docs:
            print(f"⚠️ No usable content extracted from {file_path}")
            
        return docs
        
    except Exception as e:
        print(f"❌ Error loading PDF {file_path}: {e}")
        return []

def build_index(src_dir="docs", index_path="faiss_index"):
    # Load all supported files from the docs directory
    docs = []
    docs_path = Path(src_dir)
    
    if not docs_path.exists():
        print(f"❌ Directory {src_dir} does not exist")
        return
    
    # Process different file types
    for file_path in docs_path.iterdir():
        if file_path.is_file():
            try:
                file_suffix = file_path.suffix.lower()
                
                if file_suffix == '.pdf':
                    # Handle PDF files
                    pdf_docs = load_pdf_file(file_path)
                    docs.extend(pdf_docs)
                    print(f"✅ Loaded PDF: {file_path} ({len(pdf_docs)} pages)")
                    
                elif file_suffix == '.txt':
                    # Handle .txt files
                    loader = TextLoader(str(file_path))
                    txt_docs = loader.load()
                    docs.extend(txt_docs)
                    print(f"✅ Loaded text: {file_path}")
                    
                elif file_suffix == '':
                    # Handle files without extension
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Check if it's readable text (not binary)
                            if content.isprintable() or '\n' in content:
                                from langchain.schema import Document
                                docs.append(Document(page_content=content, metadata={"source": str(file_path)}))
                                print(f"✅ Loaded: {file_path} (no extension)")
                            else:
                                print(f"⚠️ Skipped: {file_path} (appears to be binary)")
                                continue
                    except UnicodeDecodeError:
                        print(f"⚠️ Skipped: {file_path} (not readable text)")
                        continue
                        
                else:
                    print(f"⚠️ Skipped: {file_path} (unsupported file type: {file_suffix})")
                    
            except Exception as e:
                print(f"❌ Error loading {file_path}: {e}")
    
    if not docs:
        print("❌ No documents found to process")
        return
    
    print(f"📊 Total documents loaded: {len(docs)}")
    
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
        print("🔧 Building vector index...")
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        vector = FAISS.from_documents(docs, embeddings)
        vector.save_local(index_path)
        print("✅ Index built successfully:", index_path)
        print(f"📊 Total documents processed: {len(docs)}")
        print(f"📁 Index saved to: {index_path}")
    except Exception as e:
        print(f"❌ Error building index: {e}")
        print("Please check your OpenAI API key is valid")

if __name__ == "__main__":
    build_index()
