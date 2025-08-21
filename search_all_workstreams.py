#!/usr/bin/env python3
"""
Search for all workstreams in the documents to see what's actually available.
"""

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

def search_all_workstreams():
    """Search for all workstreams in the documents."""
    print("🔍 Searching for all workstreams in documents...")
    
    try:
        # Load FAISS index
        embeddings = OpenAIEmbeddings()
        retriever = FAISS.load_local(
            "faiss_index", 
            embeddings, 
            allow_dangerous_deserialization=True
        ).as_retriever()
        
        # Search for workstream-related content
        queries = [
            "workstream",
            "ws",
            "wellness app plan",
            "plan de trabajo",
            "objetivos",
            "objectives"
        ]
        
        all_workstreams = set()
        all_docs = set()
        
        for query in queries:
            print(f"\n🔍 Searching for: '{query}'")
            docs = retriever.get_relevant_documents(query)
            print(f"  ✅ Found {len(docs)} documents")
            
            for doc in docs:
                source = doc.metadata.get('source', 'Unknown')
                content = doc.page_content
                all_docs.add(source)
                
                # Extract workstream numbers
                ws_matches = re.findall(r'ws\s*(\d+)', content.lower())
                for ws_num in ws_matches:
                    all_workstreams.add(int(ws_num))
                
                # Also look for "Workstream X" format
                ws_text_matches = re.findall(r'workstream\s*(\d+)', content.lower())
                for ws_num in ws_text_matches:
                    all_workstreams.add(int(ws_num))
        
        print(f"\n{'='*80}")
        print("📊 WORKSTREAM ANALYSIS RESULTS")
        print("=" * 80)
        
        print(f"📁 Total unique documents found: {len(all_docs)}")
        print(f"🔢 Workstreams found: {sorted(all_workstreams)}")
        
        if all_workstreams:
            print(f"\n📋 Available workstreams:")
            for ws_num in sorted(all_workstreams):
                print(f"  WS{ws_num}")
            
            # Check for gaps
            expected_ws = set(range(1, max(all_workstreams) + 1))
            missing_ws = expected_ws - all_workstreams
            if missing_ws:
                print(f"\n⚠️ Missing workstreams: {sorted(missing_ws)}")
            else:
                print(f"\n✅ All workstreams from 1 to {max(all_workstreams)} are present")
        else:
            print("❌ No workstreams found in any documents")
        
        # Show document sources
        print(f"\n📄 Document sources:")
        for source in sorted(all_docs):
            print(f"  - {source}")
        
        # Now let's search specifically for workstream 5
        print(f"\n{'='*80}")
        print("🔍 SPECIFIC SEARCH FOR WORKSTREAM 5")
        print("=" * 80)
        
        ws5_queries = [
            "workstream 5",
            "ws5",
            "WS5",
            "Workstream 5"
        ]
        
        ws5_found = False
        for query in ws5_queries:
            print(f"\n🔍 Searching for: '{query}'")
            docs = retriever.get_relevant_documents(query)
            print(f"  ✅ Found {len(docs)} documents")
            
            for doc in docs:
                source = doc.metadata.get('source', 'Unknown')
                content = doc.page_content
                
                # Check if this document actually contains WS5
                if 'ws5' in content.lower() or 'workstream 5' in content.lower():
                    print(f"  🎯 WS5 found in: {source}")
                    print(f"  📝 Content preview: {content[:200]}...")
                    ws5_found = True
                else:
                    print(f"  ⚠️ Document found but no WS5 content: {source}")
        
        if not ws5_found:
            print(f"\n❌ WORKSTREAM 5 NOT FOUND in any documents!")
            print("This explains why the agent couldn't answer the question.")
        
    except Exception as e:
        print(f"❌ Error searching for workstreams: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    search_all_workstreams()
