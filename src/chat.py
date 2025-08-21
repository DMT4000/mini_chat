
import os
import json
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from .agent.config import MODEL_NAME
from dotenv import load_dotenv
from .prompt_registry import PromptRegistry
from .memory.local_memory_manager import LocalMemoryManager

class ChatPipeline:
    def __init__(self, memory_manager=None):
        load_dotenv()
        self.retriever = self._init_retriever()
        self.llm = self._init_llm()
        self.prompt_registry = PromptRegistry()
        self.memory_manager = memory_manager or LocalMemoryManager()

    def _init_retriever(self):
        print("🔍 Initializing FAISS index...")
        if os.path.exists("faiss_index"):
            try:
                embeddings = OpenAIEmbeddings()
                retriever = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True).as_retriever()
                print("✅ FAISS index loaded successfully.")
                return retriever
            except Exception as e:
                print(f"❌ Error loading FAISS index: {e}")
                return None
        else:
            print("❌ FAISS index directory not found.")
            return None

    def _init_llm(self):
        print("🔍 Initializing Language Model...")
        try:
            llm = ChatOpenAI(model=MODEL_NAME)
            print("✅ Language Model initialized successfully.")
            return llm
        except Exception as e:
            print(f"❌ Error initializing LLM: {e}")
            return None

    def ask(self, question: str, user_id: str):
        """Main method to process a question with user context and document retrieval."""
        if not self.retriever:
            return {"answer": "❌ No FAISS index found. Please run the ingest script first."}
        if not self.llm:
            return {"answer": "❌ Could not initialize LLM. Please check your OpenAI API key."}

        try:
            # 1. Retrieve user context (memory)
            user_facts = self._retrieve_user_context(user_id)
            
            # 2. Retrieve relevant documents
            retrieved_docs = self._retrieve_documents(question)
            
            # 3. Engineer the context by combining user facts with documents
            engineered_context = self._engineer_context(user_facts, retrieved_docs)
            
            # 4. Determine if this is a product-related query
            is_product_query = self._is_product_query(question)
            
            # 5. Select appropriate prompt based on query type
            if is_product_query:
                prompt = self.prompt_registry.get(
                    "product_recommendation",
                    user_facts=engineered_context["user_facts_str"],
                    context=engineered_context["document_context"],
                    question=question
                )
            else:
                prompt = self.prompt_registry.get(
                    "qa_with_memory",
                    user_facts=engineered_context["user_facts_str"],
                    context=engineered_context["document_context"],
                    question=question,
                    conversation="No recent conversation context available."
                )
            
            # 6. Generate the answer
            response = self.llm.invoke(prompt)
            
            return {
                "answer": response.content, 
                "user_facts_used": user_facts,
                "documents_retrieved": len(retrieved_docs),
                "query_type": "product_recommendation" if is_product_query else "general_qa"
            }
            
        except Exception as e:
            print(f"❌ Error in chat pipeline: {e}")
            return {"answer": f"❌ An error occurred while processing your question: {str(e)}"}

    def _retrieve_user_context(self, user_id: str) -> dict:
        """Retrieve user memory from Redis."""
        try:
            user_facts = self.memory_manager.get_user_memory(user_id)
            return user_facts if user_facts else {}
        except Exception as e:
            print(f"⚠️ Warning: Could not retrieve user memory: {e}")
            return {}

    def _retrieve_documents(self, question: str) -> list:
        """Retrieve relevant documents from FAISS vector store with improved prioritization."""
        try:
            if not self.retriever:
                return []
            
            # Check if this is a product-related query
            is_product_query = self._is_product_query(question)
            
            # Check if this is a project/planning query
            is_project_query = any(keyword in question.lower() for keyword in 
                ['timeline', 'schedule', 'cronograma', 'plan', 'workstream', 'ws', 'fase', 'gate', 
                 'milestone', 'deliverable', 'project', 'development', 'implementation', 'roadmap', 'phase'])
            
            if is_product_query:
                # For product queries, use product prioritization
                print(f"🔍 Product query detected: '{question}' - Using product prioritization...")
                
                # Stage 1: Get more documents initially to have a larger pool
                initial_docs = self.retriever.get_relevant_documents(question, k=10)
                
                # Stage 2: Re-rank and prioritize Fuxion Products and product-related content
                prioritized_docs = self._prioritize_product_documents(initial_docs, question)
                
                # Return top 5 prioritized documents
                return prioritized_docs[:5]
                
            elif is_project_query:
                # For project/planning queries, use complex document prioritization
                print(f"🔍 Project/planning query detected: '{question}' - Using complex document prioritization...")
                
                # Stage 1: Get more documents initially to have a larger pool
                initial_docs = self.retriever.get_relevant_documents(question, k=10)
                
                # Stage 2: Re-rank and prioritize complex documents (cronograma, wellness app plan)
                prioritized_docs = self._prioritize_complex_documents(initial_docs, question)
                
                # Return top 5 prioritized documents
                return prioritized_docs[:5]
                
            else:
                # For general queries, use standard retrieval
                print(f"🔍 General query detected: '{question}' - Using standard retrieval...")
                return self.retriever.get_relevant_documents(question, k=4)
                
        except Exception as e:
            print(f"⚠️ Warning: Could not retrieve documents: {e}")
            return []

    def _prioritize_product_documents(self, docs: list, question: str) -> list:
        """Prioritize Fuxion Products and other product-related documents for better relevance."""
        if not docs:
            return []
        
        # Define priority scores for different document types
        prioritized_docs = []
        
        for doc in docs:
            score = 0
            source = doc.metadata.get('source', '').lower()
            content = doc.page_content.lower()
            question_lower = question.lower()
            
            # High priority: Fuxion Products document
            if 'fuxion products' in source:
                score += 100
            
            # High priority: Documents containing product information
            if any(keyword in content for keyword in ['sku', 'product', 'supplement', 'vitamin', 'protein']):
                score += 50
            
            # Medium priority: Documents mentioning Fuxion
            if 'fuxion' in content:
                score += 30
            
            # Medium priority: Documents with product names
            product_names = [
                'alpha balance', 'beauty-in', 'berry balance', 'biopro', 'café', 
                'chocolate fit', 'flora liv', 'passion', 'prunex', 'thermo',
                'vita xtra', 'gano', 'golden flx', 'liquid fiber', 'no stress',
                'nutraday', 'protein', 'rexet', 'vera', 'vitaenergia', 'xpeed',
                'xtra mile', 'youth elixir'
            ]
            
            for product_name in product_names:
                if product_name in content:
                    score += 25
                    break
            
            # Lower priority: General wellness/health documents
            if any(keyword in content for keyword in ['wellness', 'health', 'fitness', 'app']):
                score += 10
            
            # Query relevance bonus
            if any(word in content for word in question_lower.split()):
                score += 5
            
            # Store the score in metadata for debugging
            doc.metadata['priority_score'] = score
            prioritized_docs.append((doc, score))
        
        # Sort by priority score (highest first)
        prioritized_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Return just the documents (without scores)
        result_docs = [doc for doc, score in prioritized_docs]
        
        # Debug logging
        print(f"📊 Document prioritization for '{question}':")
        for i, (doc, score) in enumerate(prioritized_docs[:5]):
            source = doc.metadata.get('source', 'Unknown')
            print(f"  {i+1}. {source} (score: {score})")
        
        return result_docs

    def _prioritize_complex_documents(self, docs: list, question: str) -> list:
        """Prioritize complex documents (cronograma, wellness app plan) for project/planning queries."""
        if not docs:
            return []
        
        # Define priority scores for different document types
        prioritized_docs = []
        
        for doc in docs:
            score = 0
            source = doc.metadata.get('source', '').lower()
            content = doc.page_content.lower()
            question_lower = question.lower()
            
            # High priority: Cronograma document for timeline/schedule queries
            if 'cronograma' in source and any(keyword in question_lower for keyword in 
                ['timeline', 'schedule', 'cronograma', 'fase', 'gate', 'milestone']):
                score += 150
            
            # High priority: Wellness app plan for project/planning queries
            elif ('wellness' in source or 'plan de trabajo' in source) and any(keyword in question_lower for keyword in 
                ['workstream', 'ws', 'plan', 'project', 'development', 'objective', 'objetivo']):
                score += 150
            
            # Medium priority: Documents containing project/planning information
            if any(keyword in content for keyword in ['workstream', 'ws', 'fase', 'gate', 'milestone', 'deliverable', 'objetivo', 'entregables']):
                score += 80
            
            # Medium priority: Documents mentioning timeline/schedule
            if any(keyword in content for keyword in ['timeline', 'schedule', 'cronograma', 'roadmap', 'phase']):
                score += 60
            
            # Medium priority: Documents with project structure
            if any(keyword in content for keyword in ['workstream', 'ws', 'objective', 'scope', 'tasks']):
                score += 50
            
            # Lower priority: General documents
            if any(keyword in content for keyword in ['wellness', 'health', 'fitness', 'app']):
                score += 20
            
            # Query relevance bonus
            if any(word in content for word in question_lower.split()):
                score += 10
            
            # Store the score in metadata for debugging
            doc.metadata['priority_score'] = score
            prioritized_docs.append((doc, score))
        
        # Sort by priority score (highest first)
        prioritized_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Return just the documents (without scores)
        result_docs = [doc for doc, score in prioritized_docs]
        
        # Debug logging
        print(f"📊 Complex document prioritization for '{question}':")
        for i, (doc, score) in enumerate(prioritized_docs[:5]):
            source = doc.metadata.get('source', 'Unknown')
            print(f"  {i+1}. {source} (score: {score})")
        
        return result_docs

    def _engineer_context(self, user_facts: dict, docs: list) -> dict:
        """Combine user facts with document context for prompt engineering."""
        # Format user facts for prompt
        if user_facts:
            facts_items = []
            for key, value in user_facts.items():
                if isinstance(value, dict):
                    # Handle nested dictionaries (like preferences)
                    for sub_key, sub_value in value.items():
                        facts_items.append(f"- {key}.{sub_key}: {sub_value}")
                else:
                    facts_items.append(f"- {key}: {value}")
            user_facts_str = "\n".join(facts_items)
        else:
            user_facts_str = "No background information available for this user."
        
        # Format document context
        if docs:
            document_context = "\n\n".join([doc.page_content for doc in docs])
        else:
            document_context = "No relevant documents found."
        
        return {
            "user_facts_str": user_facts_str,
            "document_context": document_context
        }

    def _is_product_query(self, question: str) -> bool:
        """Detect if the question is related to product recommendations or Fuxion products."""
        question_lower = question.lower()
        
        # Product-related keywords (expanded)
        product_keywords = [
            'product', 'products', 'recommend', 'recommendation', 'suggestion', 'help with', 'looking for',
            'need', 'want', 'trying to', 'goal', 'fitness', 'health', 'wellness',
            'weight', 'muscle', 'energy', 'immune', 'detox', 'cleanse', 'sleep',
            'stress', 'digestive', 'joint', 'beauty', 'anti-aging', 'sport',
            'workout', 'exercise', 'diet', 'nutrition', 'supplement', 'vitamins',
            'what is', 'tell me about', 'information about', 'details about',
            'how to', 'best', 'top', 'popular', 'available', 'offer', 'catalog'
        ]
        
        # Fuxion-specific keywords (expanded)
        fuxion_keywords = [
            'fuxion', 'alpha balance', 'beauty-in', 'berry balance', 'biopro',
            'café', 'chocolate fit', 'flora liv', 'passion', 'prunex', 'thermo',
            'vita xtra', 'gano', 'golden flx', 'liquid fiber', 'no stress',
            'nutraday', 'protein', 'rexet', 'vera', 'vitaenergia', 'xpeed',
            'xtra mile', 'youth elixir', 'ganomax', 'cappuccino', 'chocolate',
            'flavor', 'stick', 'drink', 'shake', 'tea', 'coffee', 'latte'
        ]
        
        # Project/planning keywords that should NOT be treated as product queries
        project_keywords = [
            'timeline', 'schedule', 'cronograma', 'plan', 'workstream', 'ws', 'fase', 'gate',
            'milestone', 'deliverable', 'project', 'development', 'implementation',
            'roadmap', 'phase', 'objective', 'objetivo', 'entregables', 'tareas'
        ]
        
        # Check if question contains project/planning keywords (these are NOT product queries)
        has_project_keywords = any(keyword in question_lower for keyword in project_keywords)
        if has_project_keywords:
            return False  # This is a project/planning query, not a product query
        
        # Check if question contains product-related keywords
        has_product_keywords = any(keyword in question_lower for keyword in product_keywords)
        has_fuxion_keywords = any(keyword in question_lower for keyword in fuxion_keywords)
        
        # Additional checks for common product question patterns
        product_patterns = [
            'what products', 'which products', 'show me products',
            'product list', 'product catalog', 'product range',
            'available products', 'product options', 'product selection'
        ]
        
        has_product_patterns = any(pattern in question_lower for pattern in product_patterns)
        
        return has_product_keywords or has_fuxion_keywords or has_product_patterns

# Example of how to use the new class
if __name__ == "__main__":
    try:
        chat_pipeline = ChatPipeline()
        user_id = "local_test_user"
        print(f"Chatting with user: {user_id}")
        
        # Example of saving some initial facts
        chat_pipeline.memory_manager.save_user_memory(user_id, {"business_type": "e-commerce", "state": "California"})

        while True:
            user_input = input("👤 ")
            if user_input.lower() in ["exit", "quit"]:
                break
            response = chat_pipeline.ask(user_input, user_id)
            print("🤖", response['answer'])
    except Exception as e:
        print(f"❌ Error initializing chat pipeline: {e}")
        print("Local memory manager is now being used.")
