#!/usr/bin/env python3
"""
Examine document content for workstream 5 to understand what's being retrieved.
"""

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def examine_workstream_docs():
    """Examine documents related to workstream 5."""
    print("🔍 Examining workstream 5 documents...")
    
    try:
        # Load FAISS index
        embeddings = OpenAIEmbeddings()
        retriever = FAISS.load_local(
            "faiss_index", 
            embeddings, 
            allow_dangerous_deserialization=True
        ).as_retriever()
        
        # Search for workstream 5
        query = "workstream 5 ws5"
        docs = retriever.get_relevant_documents(query)
        
        print(f"✅ Found {len(docs)} documents for query: '{query}'")
        print("=" * 80)
        
        for i, doc in enumerate(docs):
            source = doc.metadata.get('source', 'Unknown')
            content = doc.page_content
            
            print(f"\n📄 Document {i+1}: {source}")
            print(f"📝 Content length: {len(content)} characters")
            print("-" * 60)
            print(content)
            print("=" * 80)
            
            # Look for workstream information
            if 'workstream' in content.lower() or 'ws' in content.lower():
                print("✅ Contains workstream information")
                
                # Extract workstream numbers
                import re
                ws_matches = re.findall(r'ws\s*(\d+)', content.lower())
                if ws_matches:
                    print(f"🔢 Workstreams found: {ws_matches}")
                
                # Show relevant lines
                relevant_lines = [line for line in content.split('\n') 
                                if 'workstream' in line.lower() or 'ws' in line.lower()]
                if relevant_lines:
                    print("📝 Relevant lines:")
                    for line in relevant_lines:
                        print(f"  {line.strip()}")
            else:
                print("❌ No workstream information found")
            
            print()
        
    except Exception as e:
        print(f"❌ Error examining documents: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    examine_workstream_docs()
