#!/usr/bin/env python3
"""Test script to check document retrieval from FAISS index"""

from src.chat import ChatPipeline

def test_retrieval():
    try:
        print("🔍 Initializing ChatPipeline...")
        chat = ChatPipeline()
        
        print("\n🔍 Testing document retrieval for 'Fuxion products'...")
        docs = chat._retrieve_documents('Fuxion products')
        print(f"✅ Retrieved {len(docs)} documents")
        
        if docs:
            print("\n📄 Document details:")
            for i, doc in enumerate(docs[:5]):  # Show first 5 docs
                source = doc.metadata.get('source', 'No source')
                content_preview = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                print(f"\n--- Document {i+1} ---")
                print(f"Source: {source}")
                print(f"Content preview: {content_preview}")
        else:
            print("❌ No documents retrieved")
            
        print("\n🔍 Testing document retrieval for 'products'...")
        docs2 = chat._retrieve_documents('products')
        print(f"✅ Retrieved {len(docs2)} documents")
        
        print("\n🔍 Testing document retrieval for 'alpha balance'...")
        docs3 = chat._retrieve_documents('alpha balance')
        print(f"✅ Retrieved {len(docs3)} documents")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_retrieval()
