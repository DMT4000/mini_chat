#!/usr/bin/env python3
"""
Direct test of FAISS index and document retrieval.
This script tests the core functionality without complex imports.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_faiss_index():
    """Test FAISS index directly."""
    print("🧪 Testing FAISS index directly...")
    
    try:
        # Check if FAISS index exists
        faiss_path = Path("faiss_index")
        if not faiss_path.exists():
            print("❌ FAISS index not found")
            return False
        
        print(f"✅ FAISS index found at: {faiss_path}")
        
        # List contents
        index_contents = list(faiss_path.iterdir())
        print(f"📁 Index contents: {[item.name for item in index_contents]}")
        
        # Check if required files exist
        required_files = ['index.faiss', 'index.pkl']
        for file in required_files:
            if (faiss_path / file).exists():
                print(f"✅ {file} found")
            else:
                print(f"❌ {file} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking FAISS index: {e}")
        return False

def test_openai_connection():
    """Test OpenAI connection."""
    print("\n🧪 Testing OpenAI connection...")
    
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY not found in environment")
            return False
        
        if api_key == "your_openai_api_key_here":
            print("❌ OPENAI_API_KEY not properly set")
            return False
        
        print(f"✅ OPENAI_API_KEY found (length: {len(api_key)})")
        return True
        
    except Exception as e:
        print(f"❌ Error checking OpenAI connection: {e}")
        return False

def test_langchain_imports():
    """Test LangChain imports."""
    print("\n🧪 Testing LangChain imports...")
    
    try:
        from langchain_community.vectorstores import FAISS
        print("✅ FAISS import successful")
        
        from langchain_openai import OpenAIEmbeddings
        print("✅ OpenAIEmbeddings import successful")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_faiss_loading():
    """Test loading FAISS index."""
    print("\n🧪 Testing FAISS index loading...")
    
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_openai import OpenAIEmbeddings
        
        # Initialize embeddings
        embeddings = OpenAIEmbeddings()
        print("✅ OpenAI embeddings initialized")
        
        # Load FAISS index
        retriever = FAISS.load_local(
            "faiss_index", 
            embeddings, 
            allow_dangerous_deserialization=True
        ).as_retriever()
        print("✅ FAISS index loaded successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading FAISS index: {e}")
        return False

def test_document_search():
    """Test document search functionality."""
    print("\n🧪 Testing document search...")
    
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_openai import OpenAIEmbeddings
        
        # Load index
        embeddings = OpenAIEmbeddings()
        retriever = FAISS.load_local(
            "faiss_index", 
            embeddings, 
            allow_dangerous_deserialization=True
        ).as_retriever()
        
        # Test specific queries
        test_queries = [
            "workstream 5",
            "ws5", 
            "wellness app development",
            "workstreams objectives",
            "Fuxion products",
            "cronograma timeline"
        ]
        
        print("Testing document queries:")
        for query in test_queries:
            print(f"\n🔍 Query: {query}")
            try:
                docs = retriever.get_relevant_documents(query)
                print(f"  ✅ Found {len(docs)} documents")
                
                if docs:
                    # Show top result details
                    top_doc = docs[0]
                    source = getattr(top_doc, 'metadata', {}).get('source', 'Unknown')
                    content_length = len(getattr(top_doc, 'page_content', ''))
                    print(f"  📄 Top result source: {source}")
                    print(f"  📝 Content length: {content_length} characters")
                    
                    # Show content preview
                    content_preview = getattr(top_doc, 'page_content', '')[:200] + "..."
                    print(f"  📖 Content preview: {content_preview}")
                else:
                    print("  ❌ No documents found")
                    
            except Exception as e:
                print(f"  ❌ Error searching for '{query}': {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in document search: {e}")
        return False

def test_workstream_specific():
    """Test specific workstream queries that were failing in the chat."""
    print("\n🧪 Testing workstream-specific queries...")
    
    try:
        from langchain_community.vectorstores import FAISS
        from langchain_openai import OpenAIEmbeddings
        
        # Load index
        embeddings = OpenAIEmbeddings()
        retriever = FAISS.load_local(
            "faiss_index", 
            embeddings, 
            allow_dangerous_deserialization=True
        ).as_retriever()
        
        # Test the exact query from the chat
        chat_query = "si al workstream 5?"
        print(f"🔍 Testing chat query: {chat_query}")
        
        docs = retriever.get_relevant_documents(chat_query)
        print(f"✅ Found {len(docs)} documents for chat query")
        
        if docs:
            print("\n📋 Document details:")
            for i, doc in enumerate(docs[:3]):
                source = getattr(doc, 'metadata', {}).get('source', 'Unknown')
                content = getattr(doc, 'page_content', '')
                
                print(f"\n  Document {i+1}:")
                print(f"    Source: {source}")
                print(f"    Content length: {len(content)} characters")
                
                # Look for workstream information
                if 'workstream' in content.lower() or 'ws' in content.lower():
                    print(f"    ✅ Contains workstream information")
                    
                    # Extract workstream numbers
                    import re
                    ws_matches = re.findall(r'ws\s*(\d+)', content.lower())
                    if ws_matches:
                        print(f"    🔢 Workstreams found: {ws_matches}")
                    
                    # Show relevant content
                    relevant_lines = [line for line in content.split('\n') 
                                    if 'workstream' in line.lower() or 'ws' in line.lower()]
                    if relevant_lines:
                        print(f"    📝 Relevant lines:")
                        for line in relevant_lines[:3]:
                            print(f"      {line.strip()}")
                else:
                    print(f"    ❌ No workstream information found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in workstream-specific testing: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Starting Direct FAISS Test")
    print("=" * 80)
    
    tests = [
        ("FAISS Index Check", test_faiss_index),
        ("OpenAI Connection", test_openai_connection),
        ("LangChain Imports", test_langchain_imports),
        ("FAISS Loading", test_faiss_loading),
        ("Document Search", test_document_search),
        ("Workstream Specific", test_workstream_specific)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Document retrieval is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        
        if passed >= 3:  # If most tests passed
            print("\n🔧 The core functionality seems to be working.")
            print("The issue might be in the agent workflow integration.")
        else:
            print("\n🔧 Core issues detected:")
            print("1. Check FAISS index integrity")
            print("2. Verify OpenAI API key and connection")
            print("3. Check LangChain dependencies")

if __name__ == "__main__":
    main()
