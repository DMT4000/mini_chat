#!/usr/bin/env python3
"""
Get the complete WS5 content from the wellness app plan document.
"""

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_ws5_content():
    """Get the complete WS5 content."""
    print("🔍 Getting complete WS5 content...")
    
    try:
        # Load FAISS index
        embeddings = OpenAIEmbeddings()
        retriever = FAISS.load_local(
            "faiss_index", 
            embeddings, 
            allow_dangerous_deserialization=True
        ).as_retriever()
        
        # Search specifically for WS5
        query = "WS5 Campañas y upsell por datos"
        docs = retriever.get_relevant_documents(query)
        
        print(f"✅ Found {len(docs)} documents for WS5 query")
        print("=" * 80)
        
        for i, doc in enumerate(docs):
            source = doc.metadata.get('source', 'Unknown')
            content = doc.page_content
            
            print(f"\n📄 Document {i+1}: {source}")
            print(f"📝 Content length: {len(content)} characters")
            print("-" * 60)
            print(content)
            print("=" * 80)
            
            # Check if this contains WS5
            if 'ws5' in content.lower() or 'workstream 5' in content.lower():
                print("✅ This document contains WS5 information!")
                
                # Extract the WS5 section
                lines = content.split('\n')
                ws5_lines = []
                in_ws5_section = False
                
                for line in lines:
                    if 'ws5' in line.lower() or 'workstream 5' in line.lower():
                        in_ws5_section = True
                        ws5_lines.append(line)
                    elif in_ws5_section and line.strip():
                        # Continue collecting lines until we hit another workstream or empty line
                        if line.strip().startswith('WS') and any(str(i) in line for i in range(1, 10)):
                            break
                        ws5_lines.append(line)
                    elif in_ws5_section and not line.strip():
                        # Empty line, continue collecting
                        ws5_lines.append(line)
                
                if ws5_lines:
                    print("\n🎯 WS5 Section Content:")
                    print("-" * 40)
                    for line in ws5_lines:
                        print(line)
                    print("-" * 40)
            else:
                print("❌ This document does not contain WS5 information")
        
    except Exception as e:
        print(f"❌ Error getting WS5 content: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    get_ws5_content()
