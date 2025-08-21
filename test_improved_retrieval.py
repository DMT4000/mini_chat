#!/usr/bin/env python3
"""Test script to verify improved document retrieval prioritizes Fuxion Products"""

from src.chat import ChatPipeline

def test_improved_retrieval():
    try:
        print("🔍 Testing improved ChatPipeline...")
        chat = ChatPipeline()
        
        # Test queries that should now prioritize Fuxion Products
        test_queries = [
            "Fuxion products",
            "What products do you have?",
            "Show me your product catalog",
            "Tell me about your supplements",
            "What products are available?",
            "Product recommendations",
            "Available products"
        ]
        
        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"🔍 Testing query: '{query}'")
            print(f"{'='*60}")
            
            # Get documents using the improved retrieval
            docs = chat._retrieve_documents(query)
            print(f"✅ Retrieved {len(docs)} documents")
            
            if docs:
                print("\n📄 Retrieved documents (in priority order):")
                for i, doc in enumerate(docs):
                    source = doc.metadata.get('source', 'Unknown')
                    page = doc.metadata.get('page', 'No page')
                    priority_score = doc.metadata.get('priority_score', 'No score')
                    content_preview = doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content
                    
                    print(f"\n--- Document {i+1} ---")
                    print(f"Source: {source}")
                    print(f"Page: {page}")
                    print(f"Priority Score: {priority_score}")
                    print(f"Content preview: {content_preview}")
                    
                    # Highlight if this is the Fuxion Products file
                    if 'Fuxion Products' in source:
                        print("🎯 FUXION PRODUCTS FILE FOUND!")
            else:
                print("❌ No documents retrieved")
        
        # Test the ask method to see the full pipeline
        print(f"\n{'='*60}")
        print("🔍 Testing full chat pipeline with product query...")
        print(f"{'='*60}")
        
        response = chat.ask("What Fuxion products do you have?", "test_user")
        print(f"🤖 Chat response: {response['answer'][:300]}...")
        print(f"📊 Documents used: {response.get('documents_retrieved', 'Unknown')}")
        print(f"🔍 Query type: {response.get('query_type', 'Unknown')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_improved_retrieval()
