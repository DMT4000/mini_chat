#!/usr/bin/env python3
"""
Test script to verify document retrieval and context engineering.
This script tests the core functionality without the full agent workflow.
"""

import sys
import os
from pathlib import Path

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_document_retrieval():
    """Test basic document retrieval functionality."""
    print("🧪 Testing document retrieval...")
    
    try:
        # Test FAISS index access
        from langchain_community.vectorstores import FAISS
        from langchain_openai import OpenAIEmbeddings
        
        print("✅ LangChain imports successful")
        
        # Check if FAISS index exists
        faiss_path = Path("faiss_index")
        if faiss_path.exists():
            print(f"✅ FAISS index found at: {faiss_path}")
            
            # List contents
            index_contents = list(faiss_path.iterdir())
            print(f"📁 Index contents: {[item.name for item in index_contents]}")
            
            # Try to load the index
            try:
                embeddings = OpenAIEmbeddings()
                print("✅ OpenAI embeddings initialized")
                
                retriever = FAISS.load_local(
                    "faiss_index", 
                    embeddings, 
                    allow_dangerous_deserialization=True
                ).as_retriever()
                print("✅ FAISS index loaded successfully")
                
                # Test a simple query
                test_query = "workstream wellness app development"
                print(f"🔍 Testing query: {test_query}")
                
                docs = retriever.get_relevant_documents(test_query)
                print(f"✅ Retrieved {len(docs)} documents")
                
                # Show document sources
                for i, doc in enumerate(docs[:3]):
                    source = getattr(doc, 'metadata', {}).get('source', 'Unknown')
                    content_preview = getattr(doc, 'page_content', '')[:200] + "..."
                    print(f"  {i+1}. Source: {source}")
                    print(f"     Preview: {content_preview}")
                    print()
                
                return True
                
            except Exception as e:
                print(f"❌ Error loading FAISS index: {e}")
                return False
        else:
            print(f"❌ FAISS index not found at: {faiss_path}")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_context_engineering():
    """Test context engineering functions."""
    print("\n🧪 Testing context engineering...")
    
    try:
        # Test the context engineering functions directly
        from agent.workflow_nodes import _create_wellness_summary, _create_cronograma_summary, _create_product_summary
        
        print("✅ Context engineering functions imported successfully")
        
        # Test with sample documents
        sample_wellness_docs = [
            "WS1. Economía de puntos - Implementar sistema de recompensas basado en actividad física",
            "WS2. Campañas y upsell por datos - Crear estrategias de marketing personalizadas",
            "WS3. Gamificación - Desarrollar elementos de juego para aumentar engagement"
        ]
        
        wellness_summary = _create_wellness_summary(sample_wellness_docs)
        print(f"✅ Wellness summary created: {wellness_summary[:100]}...")
        
        sample_cronograma_docs = [
            "Fase 1. Planificación - Semanas 1-4: Definir objetivos y alcance del proyecto",
            "Gate 1. Aprobación de diseño - Semana 4: Revisar y aprobar arquitectura técnica",
            "Fase 2. Desarrollo - Semanas 5-12: Implementar funcionalidades core"
        ]
        
        cronograma_summary = _create_cronograma_summary(sample_cronograma_docs)
        print(f"✅ Cronograma summary created: {cronograma_summary[:100]}...")
        
        sample_product_docs = [
            "**ALPHA BALANCE** (SKU: AB001) - Suplemento para balance hormonal",
            "**BEAUTY-IN** (SKU: BI002) - Nutricosmético para belleza interior",
            "**BERRY BALANCE** (SKU: BB003) - Antioxidante natural con bayas"
        ]
        
        product_summary = _create_product_summary(sample_product_docs)
        print(f"✅ Product summary created: {product_summary[:100]}...")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_capabilities_detection():
    """Test capabilities question detection."""
    print("\n🧪 Testing capabilities detection...")
    
    try:
        from agent.workflow_nodes import _is_capabilities_question
        
        print("✅ Capabilities detection function imported successfully")
        
        # Test capabilities questions
        capabilities_questions = [
            "What are your capabilities?",
            "What can you do?",
            "What documents can you access?",
            "How do you help?",
            "Tell me about your features"
        ]
        
        print("Capabilities questions detected:")
        for question in capabilities_questions:
            is_cap = _is_capabilities_question(question)
            status = "✅ YES" if is_cap else "❌ NO"
            print(f"  {status}: {question}")
        
        # Test non-capabilities questions
        non_cap_questions = [
            "Hello",
            "What is the weather like?",
            "My name is John",
            "I need help with weight loss"
        ]
        
        print("\nNon-capabilities questions detected:")
        for question in non_cap_questions:
            is_cap = _is_capabilities_question(question)
            status = "❌ YES" if is_cap else "✅ NO"
            print(f"  {status}: {question}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_document_search():
    """Test specific document search queries."""
    print("\n🧪 Testing specific document search...")
    
    try:
        # Test searching for specific workstream information
        from langchain_community.vectorstores import FAISS
        from langchain_openai import OpenAIEmbeddings
        
        faiss_path = Path("faiss_index")
        if not faiss_path.exists():
            print("❌ FAISS index not available for search testing")
            return False
        
        embeddings = OpenAIEmbeddings()
        retriever = FAISS.load_local(
            "faiss_index", 
            embeddings, 
            allow_dangerous_deserialization=True
        ).as_retriever()
        
        # Test specific queries related to the chat example
        test_queries = [
            "workstream 5",
            "ws5",
            "wellness app development plan",
            "workstreams objectives",
            "Fuxion products catalog",
            "cronograma timeline phases"
        ]
        
        print("Testing specific document queries:")
        for query in test_queries:
            print(f"\n🔍 Query: {query}")
            try:
                docs = retriever.get_relevant_documents(query)
                print(f"  ✅ Found {len(docs)} documents")
                
                # Show top result
                if docs:
                    top_doc = docs[0]
                    source = getattr(top_doc, 'metadata', {}).get('source', 'Unknown')
                    content_preview = getattr(top_doc, 'page_content', '')[:150] + "..."
                    print(f"  📄 Top result source: {source}")
                    print(f"  📝 Content preview: {content_preview}")
                else:
                    print("  ❌ No documents found")
                    
            except Exception as e:
                print(f"  ❌ Error searching for '{query}': {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in document search testing: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Starting Document Context Test")
    print("=" * 80)
    
    tests = [
        ("Document Retrieval", test_document_retrieval),
        ("Context Engineering", test_context_engineering),
        ("Capabilities Detection", test_capabilities_detection),
        ("Document Search", test_document_search)
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
        print("🎉 All tests passed! Document context is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        print("\n🔧 Next steps:")
        print("1. Check if FAISS index exists and is properly loaded")
        print("2. Verify document ingestion was successful")
        print("3. Check import paths and dependencies")
        print("4. Test with simpler queries to isolate issues")

if __name__ == "__main__":
    main()
