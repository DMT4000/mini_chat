#!/usr/bin/env python3
"""Deep test of FAISS index to understand why Fuxion Products isn't being retrieved"""

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import os

def deep_index_test():
    print("🔍 Deep testing FAISS index...")
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Load the index
        print("📖 Loading FAISS index...")
        embeddings = OpenAIEmbeddings()
        vectorstore = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
        
        print(f"✅ Index loaded successfully")
        
        # Get all documents from the store
        print("\n📚 Examining document store...")
        if hasattr(vectorstore, 'docstore') and hasattr(vectorstore.docstore, '_dict'):
            docs = vectorstore.docstore._dict
            print(f"📄 Total documents in store: {len(docs)}")
            
            print("\n📋 All documents in index:")
            for doc_id, doc in docs.items():
                source = doc.metadata.get('source', 'Unknown')
                page = doc.metadata.get('page', 'No page')
                content_preview = doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content
                print(f"\n--- Document {doc_id} ---")
                print(f"Source: {source}")
                print(f"Page: {page}")
                print(f"Content length: {len(doc.page_content)} chars")
                print(f"Content preview: {content_preview}")
                
                # Check if this is the Fuxion Products file
                if 'Fuxion Products' in str(source):
                    print("🎯 FOUND FUXION PRODUCTS FILE!")
                    print(f"Full content: {doc.page_content}")
        
        # Test specific queries
        print("\n🔍 Testing specific queries...")
        test_queries = [
            "Fuxion Products",
            "ALPHA BALANCE", 
            "BEAUTY-IN",
            "BERRY BALANCE",
            "BIOPRO+ SPORT",
            "products",
            "supplements"
        ]
        
        for query in test_queries:
            print(f"\n--- Query: '{query}' ---")
            try:
                docs = vectorstore.similarity_search(query, k=5)
                print(f"Retrieved {len(docs)} documents")
                
                for i, doc in enumerate(docs):
                    source = doc.metadata.get('source', 'Unknown')
                    page = doc.metadata.get('page', 'No page')
                    score = getattr(doc, 'metadata', {}).get('score', 'No score')
                    preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                    print(f"  {i+1}. {source} (page {page}) - Score: {score}")
                    print(f"     Preview: {preview}")
                    
            except Exception as e:
                print(f"❌ Error with query '{query}': {e}")
        
        # Try to find Fuxion Products with different approaches
        print("\n🎯 Special search for Fuxion Products...")
        
        # Method 1: Direct similarity search
        print("\nMethod 1: Direct similarity search")
        try:
            docs = vectorstore.similarity_search("Fuxion Products", k=10)
            print(f"Direct search found {len(docs)} docs")
            for doc in docs:
                source = doc.metadata.get('source', 'Unknown')
                print(f"  - {source}")
        except Exception as e:
            print(f"❌ Direct search error: {e}")
        
        # Method 2: Search with product names
        print("\nMethod 2: Search with product names")
        try:
            docs = vectorstore.similarity_search("ALPHA BALANCE SKU 145879", k=5)
            print(f"Product search found {len(docs)} docs")
            for doc in docs:
                source = doc.metadata.get('source', 'Unknown')
                print(f"  - {doc.metadata.get('source', 'Unknown')}")
        except Exception as e:
            print(f"❌ Product search error: {e}")
        
        # Method 3: Check if document exists by examining all content
        print("\nMethod 3: Examining all document content for Fuxion references")
        if hasattr(vectorstore, 'docstore') and hasattr(vectorstore.docstore, '_dict'):
            docs = vectorstore.docstore._dict
            fuxion_found = False
            for doc_id, doc in docs.items():
                if 'Fuxion' in doc.page_content or 'ALPHA BALANCE' in doc.page_content:
                    source = doc.metadata.get('source', 'Unknown')
                    print(f"🎯 Found Fuxion content in: {source}")
                    fuxion_found = True
                    # Show the relevant part
                    content = doc.page_content
                    fuxion_index = content.find('Fuxion') if 'Fuxion' in content else content.find('ALPHA BALANCE')
                    if fuxion_index != -1:
                        start = max(0, fuxion_index - 50)
                        end = min(len(content), fuxion_index + 200)
                        print(f"Context: ...{content[start:end]}...")
            
            if not fuxion_found:
                print("❌ No Fuxion content found in any document!")
                
    except Exception as e:
        print(f"❌ Error in deep test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deep_index_test()
