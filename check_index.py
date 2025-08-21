#!/usr/bin/env python3
"""Script to examine FAISS index contents"""

import pickle
import os

def check_index():
    print("🔍 Checking FAISS index contents...")
    
    # List index files
    print("\n📁 Index files:")
    for f in os.listdir('faiss_index'):
        print(f"  {f}")
    
    # Load and examine index.pkl
    try:
        print("\n📖 Loading index.pkl...")
        with open('faiss_index/index.pkl', 'rb') as f:
            data = pickle.load(f)
        
        print(f"✅ Index type: {type(data)}")
        print(f"📊 Index attributes: {[attr for attr in dir(data) if not attr.startswith('_')]}")
        
        # Check if it has documents
        if hasattr(data, 'docstore'):
            print(f"\n📚 Document store type: {type(data.docstore)}")
            if hasattr(data.docstore, '_dict'):
                docs = data.docstore._dict
                print(f"📄 Number of documents in store: {len(docs)}")
                print("\n📋 Document sources:")
                for doc_id, doc in docs.items():
                    if hasattr(doc, 'metadata') and doc.metadata:
                        source = doc.metadata.get('source', 'Unknown')
                        print(f"  - {source}")
                    else:
                        print(f"  - Document {doc_id}: No metadata")
        
        # Check if it has embeddings
        if hasattr(data, 'index'):
            print(f"\n🔢 FAISS index type: {type(data.index)}")
            if hasattr(data.index, 'ntotal'):
                print(f"📊 Total vectors in index: {data.index.ntotal}")
                
    except Exception as e:
        print(f"❌ Error examining index: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_index()
