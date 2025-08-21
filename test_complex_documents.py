#!/usr/bin/env python3
"""Test script to verify improved document processing for complex documents"""

from src.chat import ChatPipeline

def test_complex_document_retrieval():
    try:
        print("🔍 Testing improved complex document processing...")
        chat = ChatPipeline()
        
        # Test queries for the cronograma document
        cronograma_queries = [
            "Tell me about the project timeline",
            "What are the phases of the project?",
            "Show me the cronograma",
            "What gates are in the project?",
            "Tell me about the project schedule"
        ]
        
        print(f"\n{'='*60}")
        print("📅 TESTING CRONOGRAMA DOCUMENT")
        print(f"{'='*60}")
        
        for query in cronograma_queries:
            print(f"\n🔍 Query: '{query}'")
            
            # Get documents using the improved retrieval
            docs = chat._retrieve_documents(query)
            print(f"✅ Retrieved {len(docs)} documents")
            
            if docs:
                # Check if cronograma document is retrieved
                cronograma_found = False
                for doc in docs:
                    source = doc.metadata.get('source', '')
                    if 'cronograma' in source.lower():
                        cronograma_found = True
                        print(f"🎯 Cronograma document found!")
                        print(f"📄 Content preview: {doc.page_content[:300]}...")
                        print(f"📊 Document length: {len(doc.page_content)} characters")
                        break
                
                if not cronograma_found:
                    print("⚠️ Cronograma document not found in results")
            else:
                print("❌ No documents retrieved")
        
        # Test queries for the wellness app plan document
        wellness_queries = [
            "Tell me about the wellness app plan",
            "What are the workstreams?",
            "Show me the wellness app development plan",
            "What are the objectives of the wellness app?",
            "Tell me about the wellness app workstreams"
        ]
        
        print(f"\n{'='*60}")
        print("📱 TESTING WELLNESS APP PLAN DOCUMENT")
        print(f"{'='*60}")
        
        for query in wellness_queries:
            print(f"\n🔍 Query: '{query}'")
            
            # Get documents using the improved retrieval
            docs = chat._retrieve_documents(query)
            print(f"✅ Retrieved {len(docs)} documents")
            
            if docs:
                # Check if wellness app plan document is retrieved
                wellness_found = False
                for doc in docs:
                    source = doc.metadata.get('source', '')
                    if 'wellness' in source.lower() or 'plan de trabajo' in source.lower():
                        wellness_found = True
                        print(f"🎯 Wellness app plan document found!")
                        print(f"📄 Content preview: {doc.page_content[:300]}...")
                        print(f"📊 Document length: {len(doc.page_content)} characters")
                        break
                
                if not wellness_found:
                    print("⚠️ Wellness app plan document not found in results")
            else:
                print("❌ No documents retrieved")
        
        # Test the full chat pipeline with complex document queries
        print(f"\n{'='*60}")
        print("🤖 TESTING FULL CHAT PIPELINE")
        print(f"{'='*60}")
        
        test_queries = [
            "What is the project timeline for the wellness app?",
            "Tell me about the workstreams and phases",
            "What are the key milestones in the cronograma?"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Testing: '{query}'")
            try:
                response = chat.ask(query, "test_user")
                answer = response.get('answer', '')
                
                print(f"🤖 Response length: {len(answer)} characters")
                print(f"📄 Response preview: {answer[:200]}...")
                
                # Check for key terms that should be in the response
                key_terms = ['fase', 'gate', 'workstream', 'ws', 'objetivo', 'entregables', 'tareas']
                found_terms = [term for term in key_terms if term.lower() in answer.lower()]
                
                if found_terms:
                    print(f"✅ Found key terms: {', '.join(found_terms)}")
                else:
                    print("⚠️ No key terms found in response")
                    
            except Exception as e:
                print(f"❌ Error in chat pipeline: {e}")
        
        print(f"\n{'='*60}")
        print("🎯 Testing complete! Check above for document retrieval quality.")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_complex_document_retrieval()
