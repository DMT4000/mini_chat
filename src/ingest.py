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
    """Clean and normalize extracted text with improved PDF handling"""
    if not text:
        return ""
    
    # Remove excessive whitespace and newlines
    text = re.sub(r'\n\s*\n', '\n\n', text)  # Replace multiple newlines with double newlines
    text = re.sub(r' +', ' ', text)  # Replace multiple spaces with single space
    text = re.sub(r'\n +', '\n', text)  # Remove leading spaces after newlines
    text = re.sub(r' +\n', '\n', text)  # Remove trailing spaces before newlines
    
    # Fix broken words more aggressively for complex PDFs
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
    
    # Special handling for cronograma and wellness app documents
    # Preserve important structural elements
    text = re.sub(r'(Fase\s+\d+\.|Gate\s+\d+\.|WS\d+\.|Semana\s+\d+\.)', r'\n\n\1', text)  # Add spacing before phase/gate headers
    text = re.sub(r'(Objetivo\s*:|Alcance\s*y\s*supuestos|Efectos\s*WOW|Entregables\s*:|Tareas\s*:)', r'\n\n\1', text)  # Add spacing before major headers
    
    # Clean up date ranges and time periods
    text = re.sub(r'(\d{1,2})–(\d{1,2})\s*(ago|sep|oct|nov|dic|ene|feb|mar|abr|may|jun|jul)', r'\1–\2 \3', text)  # Fix date ranges
    text = re.sub(r'(\d{1,2})–(\d{1,2})\s*(\d{4})', r'\1–\2 \3', text)  # Fix year ranges
    
    # Clean up common PDF artifacts
    text = re.sub(r'\n\s*([a-zA-Z])\s*\n', r' \1 ', text)  # Fix single letters on separate lines
    text = re.sub(r'([a-zA-Z])\s*\n\s*([a-zA-Z])', r'\1 \2', text)  # Fix broken words
    
    # Improve readability for specific document types
    # For cronograma: preserve phase structure
    text = re.sub(r'(Fase\s+\d+\.\s*[^\n]+)', r'\n\n**\1**\n', text)  # Make phases stand out
    text = re.sub(r'(Gate\s+\d+\.\s*[^\n]+)', r'\n\n**\1**\n', text)  # Make gates stand out
    
    # For wellness app: preserve workstream structure
    text = re.sub(r'(WS\d+\.\s*[^\n]+)', r'\n\n**\1**\n', text)  # Make workstreams stand out
    text = re.sub(r'(Objetivo\s*:[^\n]*)', r'\n\n**\1**\n', text)  # Make objectives stand out
    
    # Final cleanup
    text = text.strip()
    
    # Post-processing: improve readability
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if line:
            # Skip lines that are just single characters or very short fragments
            if len(line) > 2 or line.isupper() or line.isdigit() or line.startswith('•') or line.startswith('-'):
                cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Final text cleanup - remove extra spaces at word boundaries
    text = re.sub(r' ([A-Z])', r'\1', text)  # Remove space before capital letters
    text = re.sub(r' +', ' ', text)  # Clean up any remaining multiple spaces
    
    # Ensure proper spacing around important elements
    text = re.sub(r'(\n\n)([^\n]+)(\n\n)', r'\1\2\3', text)  # Ensure consistent spacing
    
    return text.strip()

def load_pdf_file(file_path):
    """Load PDF files with improved text extraction and logical sectioning"""
    try:
        # Try PyPDF2 first
        import PyPDF2
        docs = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            print(f"📖 Processing PDF: {file_path} ({len(pdf_reader.pages)} pages)")
            
            # Extract all text first
            full_text = ""
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        full_text += text + "\n"
                        print(f"  ✅ Page {page_num + 1}: {len(text)} chars extracted")
                    else:
                        print(f"  ⚠️ Page {page_num + 1}: No text extracted")
                except Exception as e:
                    print(f"  ❌ Error processing page {page_num + 1}: {e}")
                    continue
            
            if not full_text.strip():
                print(f"⚠️ No usable content extracted from {file_path}")
                return []
            
            # Clean the full text
            cleaned_text = clean_text(full_text)
            print(f"📝 Total cleaned text: {len(cleaned_text)} characters")
            
            # Create logical sections based on document type and content
            if "cronograma" in str(file_path).lower():
                docs = _create_cronograma_sections(cleaned_text, file_path)
            elif "wellness" in str(file_path).lower() or "plan de trabajo" in str(file_path).lower():
                docs = _create_wellness_plan_sections(cleaned_text, file_path)
            else:
                # Default: create sections based on content structure
                docs = _create_generic_sections(cleaned_text, file_path)
            
            print(f"📚 Created {len(docs)} logical sections")
            return docs
        
    except Exception as e:
        print(f"❌ Error loading PDF {file_path}: {e}")
        return []

def _create_cronograma_sections(text: str, file_path: str) -> list:
    """Create logical sections for the cronograma document"""
    from langchain.schema import Document
    import re
    
    sections = []
    
    # Split by major phases/gates
    phase_pattern = r'(Fase\s+\d+\.\s*[^\n]+|Gate\s+\d+\.\s*[^\n]+)'
    phases = re.split(phase_pattern, text)
    
    current_section = ""
    section_count = 0
    
    for i, part in enumerate(phases):
        if re.match(phase_pattern, part):
            # This is a phase/gate header
            if current_section.strip():
                # Save previous section
                if len(current_section.strip()) > 100:  # Only add substantial sections
                    sections.append(Document(
                        page_content=current_section.strip(),
                        metadata={
                            "source": str(file_path),
                            "section_type": "cronograma_phase",
                            "section_number": section_count,
                            "content_type": "project_timeline"
                        }
                    ))
                    section_count += 1
            
            # Start new section
            current_section = part + "\n"
        else:
            # This is content for the current phase
            current_section += part + "\n"
    
    # Add the last section
    if current_section.strip() and len(current_section.strip()) > 100:
        sections.append(Document(
            page_content=current_section.strip(),
            metadata={
                "source": str(file_path),
                "section_type": "cronograma_phase",
                "section_number": section_count,
                "content_type": "project_timeline"
            }
        ))
    
    # If no phases found, create time-based sections
    if not sections:
        sections = _create_time_based_sections(text, file_path, "cronograma")
    
    return sections

def _create_wellness_plan_sections(text: str, file_path: str) -> list:
    """Create logical sections for the wellness app plan document"""
    from langchain.schema import Document
    import re
    
    sections = []
    
    # Split by workstreams and major sections
    section_patterns = [
        r'(Workstreams?\s*\(WS\)|WS\d+\.\s*[^\n]+)',  # Workstreams
        r'(Objetivo\s*:|Alcance\s*y\s*supuestos)',    # Objectives and scope
        r'(Efectos\s*WOW|Entregables\s*:)',           # Effects and deliverables
        r'(Tareas\s*:|Entregables\s*:)',              # Tasks and deliverables
    ]
    
    # Try to split by workstreams first
    ws_pattern = r'(WS\d+\.\s*[^\n]+)'
    if re.search(ws_pattern, text):
        sections = _split_by_workstreams(text, file_path)
    else:
        # Fall back to generic sectioning
        sections = _create_generic_sections(text, file_path)
    
    return sections

def _split_by_workstreams(text: str, file_path: str) -> list:
    """Split wellness plan by workstreams"""
    from langchain.schema import Document
    import re
    
    sections = []
    
    # Split by workstream headers
    ws_pattern = r'(WS\d+\.\s*[^\n]+)'
    parts = re.split(ws_pattern, text)
    
    current_section = ""
    section_count = 0
    
    for i, part in enumerate(parts):
        if re.match(ws_pattern, part):
            # This is a workstream header
            if current_section.strip():
                # Save previous section
                if len(current_section.strip()) > 150:  # Only add substantial sections
                    sections.append(Document(
                        page_content=current_section.strip(),
                        metadata={
                            "source": str(file_path),
                            "section_type": "wellness_workstream",
                            "section_number": section_count,
                            "content_type": "app_development_plan"
                        }
                    ))
                    section_count += 1
            
            # Start new section
            current_section = part + "\n"
        else:
            # This is content for the current workstream
            current_section += part + "\n"
    
    # Add the last section
    if current_section.strip() and len(current_section.strip()) > 150:
        sections.append(Document(
            page_content=current_section.strip(),
            metadata={
                "source": str(file_path),
                "section_type": "wellness_workstream",
                "section_number": section_count,
                "content_type": "app_development_plan"
            }
        ))
    
    return sections

def _create_time_based_sections(text: str, file_path: str, doc_type: str) -> list:
    """Create sections based on time periods for timeline documents"""
    from langchain.schema import Document
    import re
    
    sections = []
    
    # Look for time patterns (weeks, months, dates)
    time_pattern = r'(Semana\s+\d+\.\s*[^\n]+|Week\s+\d+|Month\s+\d+|Q\d+|Q[1-4])'
    parts = re.split(time_pattern, text)
    
    current_section = ""
    section_count = 0
    
    for i, part in enumerate(parts):
        if re.match(time_pattern, part):
            # This is a time period header
            if current_section.strip():
                # Save previous section
                if len(current_section.strip()) > 100:
                    sections.append(Document(
                        page_content=current_section.strip(),
                        metadata={
                            "source": str(file_path),
                            "section_type": f"{doc_type}_time_period",
                            "section_number": section_count,
                            "content_type": "timeline"
                        }
                    ))
                    section_count += 1
            
            # Start new section
            current_section = part + "\n"
        else:
            # This is content for the current time period
            current_section += part + "\n"
    
    # Add the last section
    if current_section.strip() and len(current_section.strip()) > 100:
        sections.append(Document(
            page_content=current_section.strip(),
            metadata={
                "source": str(file_path),
                "section_type": f"{doc_type}_time_period",
                "section_number": section_count,
                "content_type": "timeline"
            }
        ))
    
    return sections

def _create_generic_sections(text: str, file_path: str) -> list:
    """Create generic sections for documents that don't fit specific patterns"""
    from langchain.schema import Document
    import re
    
    sections = []
    
    # Split by headers (lines starting with numbers, letters, or common headers)
    header_pattern = r'^(\d+\.\s*[^\n]+|[A-Z][^\n]*:|[A-Z][A-Z\s]+\n)'
    parts = re.split(header_pattern, text, flags=re.MULTILINE)
    
    current_section = ""
    section_count = 0
    
    for i, part in enumerate(parts):
        if re.match(header_pattern, part):
            # This is a header
            if current_section.strip():
                # Save previous section
                if len(current_section.strip()) > 200:  # Higher threshold for generic sections
                    sections.append(Document(
                        page_content=current_section.strip(),
                        metadata={
                            "source": str(file_path),
                            "section_type": "generic_section",
                            "section_number": section_count,
                            "content_type": "document_section"
                        }
                    ))
                    section_count += 1
            
            # Start new section
            current_section = part + "\n"
        else:
            # This is content for the current section
            current_section += part + "\n"
    
    # Add the last section
    if current_section.strip() and len(current_section.strip()) > 200:
        sections.append(Document(
            page_content=current_section.strip(),
            metadata={
                "source": str(file_path),
                "section_type": "generic_section",
                "section_number": section_count,
                "content_type": "document_section"
            }
        ))
    
    # If no sections created, create one large section
    if not sections and len(text.strip()) > 100:
        sections.append(Document(
            page_content=text.strip(),
            metadata={
                "source": str(file_path),
                "section_type": "full_document",
                "section_number": 0,
                "content_type": "complete_document"
            }
        ))
    
    return sections

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
