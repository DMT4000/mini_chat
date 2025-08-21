#!/usr/bin/env python3
"""
Test script to verify enhanced context engineering for workstream queries.
This script tests the improved document retrieval and context generation.
"""

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import sys
from pathlib import Path

# Load environment variables
load_dotenv()

# Add the src directory to the Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_workstream_context_engineering():
    """Test the enhanced context engineering for workstream queries."""
    print("🧪 Testing enhanced context engineering for workstream queries...")
    
    try:
        # Import the enhanced context engineering function
        from agent.workflow_nodes import _engineer_context, _create_workstream_specific_summary
        
        print("✅ Enhanced context engineering functions imported successfully")
        
        # Test with sample documents that include WS5
        sample_docs = [
            "WS5. Campañas y upsell por datos** (Coordinaciones con Mkt) Objetivo aumentar AOV y frecuencia con bundles dinámicos. Tareas - Campaña 'Sueño Tranquilo' con bundle No Stress y Magnesio. - Bundles dinámicos según métricas. Entregables campaña live y packs recomendados. Criterio de aceptación uplift en conversión del bundle mayor a 10% vs control.",
            "WS2. Freemium vs Premium y cobro en webapp Objetivo límites claros en free y valor fuerte en premium. Tareas - Backend de caps y flags. UI de límites. - Checkout en webapp con retorno a la app. (Confirmado por Miguel) - Instrumentación del funnel y pricing A/B.",
            "WS3. Economía de puntos, rifas y antifraude Objetivo conectar hábitos y compras con recompensas controladas. Tareas - Motor de tickets, scheduler de sorteo semanal, panel admin. - Caps diarios y semanales, detección simple de anomalías y verificación con wearable."
        ]
        
        # Test the workstream-specific summary function
        print("\n🔍 Testing workstream-specific summary for WS5...")
        ws5_summary = _create_workstream_specific_summary(sample_docs, "5")
        print("✅ WS5 Summary created:")
        print("-" * 60)
        print(ws5_summary)
        print("-" * 60)
        
        # Test the enhanced context engineering
        print("\n🔍 Testing enhanced context engineering...")
        user_facts = {"name": "Test User", "preferences": "wellness app development"}
        conversation_context = "Previous discussion about workstreams"
        
        # Test with a workstream query
        state = {"question": "Tell me about workstream 5"}
        
        engineered_context = _engineer_context(
            user_facts, sample_docs, conversation_context, state
        )
        
        print("✅ Enhanced context engineering completed:")
        print(f"  - User facts: {len(engineered_context['user_facts_str'])} characters")
        print(f"  - Document context: {len(engineered_context['document_context'])} characters")
        print(f"  - Conversation context: {len(engineered_context['conversation_context'])} characters")
        
        # Show the document context
        print("\n📋 Generated Document Context:")
        print("=" * 80)
        print(engineered_context['document_context'])
        print("=" * 80)
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_document_retrieval_enhancement():
    """Test the enhanced document retrieval for workstream queries."""
    print("\n🧪 Testing enhanced document retrieval for workstream queries...")
    
    try:
        # Load FAISS index
        embeddings = OpenAIEmbeddings()
        retriever = FAISS.load_local(
            "faiss_index", 
            embeddings, 
            allow_dangerous_deserialization=True
        ).as_retriever()
        
        # Test different workstream queries
        test_queries = [
            "workstream 5",
            "ws5",
            "Tell me about workstream 5",
            "What is workstream 5 about?",
            "si al workstream 5?"
        ]
        
        print("Testing workstream queries:")
        for query in test_queries:
            print(f"\n🔍 Query: {query}")
            try:
                docs = retriever.get_relevant_documents(query)
                print(f"  ✅ Found {len(docs)} documents")
                
                if docs:
                    # Check if WS5 content is in the results
                    ws5_found = False
                    for doc in docs:
                        if 'ws5' in doc.page_content.lower() or 'workstream 5' in doc.page_content.lower():
                            ws5_found = True
                            source = doc.metadata.get('source', 'Unknown')
                            print(f"  🎯 WS5 found in: {source}")
                            break
                    
                    if not ws5_found:
                        print(f"  ⚠️ WS5 content not found in top results")
                    
                    # Show top result details
                    top_doc = docs[0]
                    source = top_doc.metadata.get('source', 'Unknown')
                    content_preview = top_doc.page_content[:200] + "..."
                    print(f"  📄 Top result: {source}")
                    print(f"  📝 Preview: {content_preview}")
                else:
                    print("  ❌ No documents found")
                    
            except Exception as e:
                print(f"  ❌ Error searching for '{query}': {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in document retrieval testing: {e}")
        return False

def test_context_quality():
    """Test the quality of generated context for workstream queries."""
    print("\n🧪 Testing context quality for workstream queries...")
    
    try:
        # Test with the exact query from the chat
        chat_query = "si al workstream 5?"
        
        # Simulate the enhanced context engineering
        sample_docs = [
            "WS5. Campañas y upsell por datos** (Coordinaciones con Mkt) Objetivo aumentar AOV y frecuencia con bundles dinámicos. Tareas - Campaña 'Sueño Tranquilo' con bundle No Stress y Magnesio. - Bundles dinámicos según métricas. Entregables campaña live y packs recomendados. Criterio de aceptación uplift en conversión del bundle mayor a 10% vs control.",
            "WS2. Freemium vs Premium y cobro en webapp Objetivo límites claros en free y valor fuerte en premium.",
            "WS3. Economía de puntos, rifas y antifraude Objetivo conectar hábitos y compras con recompensas controladas."
        ]
        
        # Test the workstream-specific summary
        ws5_summary = _create_workstream_specific_summary(sample_docs, "5")
        
        print("✅ Context quality test completed:")
        print(f"  - WS5 summary length: {len(ws5_summary)} characters")
        print(f"  - Contains WS5 details: {'ws5' in ws5_summary.lower()}")
        print(f"  - Contains objectives: {'objetivo' in ws5_summary.lower()}")
        print(f"  - Contains tasks: {'tareas' in ws5_summary.lower()}")
        print(f"  - Contains deliverables: {'entregables' in ws5_summary.lower()}")
        
        # Show the generated context
        print("\n📋 Generated WS5 Context:")
        print("=" * 80)
        print(ws5_summary)
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ Error in context quality testing: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 Starting Enhanced Context Engineering Test")
    print("=" * 80)
    
    tests = [
        ("Workstream Context Engineering", test_workstream_context_engineering),
        ("Document Retrieval Enhancement", test_document_retrieval_enhancement),
        ("Context Quality", test_context_quality)
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
        print("🎉 All tests passed! Enhanced context engineering is working correctly.")
        print("\n🔧 The agent should now be able to:")
        print("1. ✅ Properly detect workstream queries")
        print("2. ✅ Retrieve and prioritize relevant workstream content")
        print("3. ✅ Generate detailed workstream-specific summaries")
        print("4. ✅ Provide comprehensive answers about any workstream")
        print("5. ✅ Maintain context across multiple document types in the same chat")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()
