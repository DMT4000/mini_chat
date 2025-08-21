#!/usr/bin/env python3
"""Script to examine FAISS index contents using proper FAISS loading"""

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os

def check_index():
    print("🔍 Checking FAISS index contents...")
    
    try:
        # Load the index properly
        print("📖 Loading FAISS index...")
        embeddings = OpenAIEmbeddings()
        vectorstore = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
        
        print(f"✅ Index loaded successfully")
        print(f"📊 Index type: {type(vectorstore)}")
        
        # Check document store
        if hasattr(vectorstore, 'docstore'):
            print(f"\n📚 Document store type: {type(vectorstore.docstore)}")
            if hasattr(vectorstore.docstore, '_dict'):
                docs = vectorstore.docstore._dict
                print(f"📄 Number of documents in store: {len(docs)}")
                print("\n📋 Document sources:")
                for doc_id, doc in docs.items():
                    if hasattr(doc, 'metadata') and doc.metadata:
                        source = doc.metadata.get('source', 'Unknown')
                        page = doc.metadata.get('page', 'No page')
                        print(f"  - {source} (page {page})")
                    else:
                        print(f"  - Document {doc_id}: No metadata")
        
        # Check FAISS index
        if hasattr(vectorstore, 'index'):
            print(f"\n🔢 FAISS index type: {type(vectorstore.index)}")
            if hasattr(vectorstore.index, 'ntotal'):
                print(f"📊 Total vectors in index: {vectorstore.index.ntotal}")
        
        # Try to retrieve some documents
        print("\n🔍 Testing retrieval...")
        test_queries = ["Fuxion", "products", "alpha balance", "beauty"]
        for query in test_queries:
            docs = vectorstore.similarity_search(query, k=2)
            print(f"\nQuery '{query}': {len(docs)} documents")
            for i, doc in enumerate(docs):
                source = doc.metadata.get('source', 'Unknown')
                page = doc.metadata.get('page', 'No page')
                preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                print(f"  {i+1}. {source} (page {page}): {preview}")
                
    except Exception as e:
        print(f"❌ Error examining index: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_index()
