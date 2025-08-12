
import os
import json
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from dotenv import load_dotenv
from .prompt_registry import PromptRegistry
from .memory.redis_memory_manager import RedisMemoryManager

class ChatPipeline:
    def __init__(self, memory_manager=None):
        load_dotenv()
        self.retriever = self._init_retriever()
        self.llm = self._init_llm()
        self.prompt_registry = PromptRegistry()
        self.memory_manager = memory_manager or RedisMemoryManager()

    def _init_retriever(self):
        print("🔍 Initializing FAISS index...")
        if os.path.exists("faiss_index"):
            try:
                embeddings = OpenAIEmbeddings()
                # Avoid unsafe deserialization by default. Enable only if explicitly allowed.
                allow_unsafe = os.getenv("ALLOW_FAISS_DESERIALIZATION", "false").lower() in {"1", "true", "yes"}
                retriever = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=allow_unsafe).as_retriever()
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
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
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
            
            # 4. Generate response using enhanced prompt
            prompt = self.prompt_registry.get(
                "qa_with_memory",
                user_facts=engineered_context["user_facts_str"],
                context=engineered_context["document_context"],
                question=question
            )
            
            # 5. Generate the answer
            response = self.llm.invoke(prompt)
            
            return {
                "answer": response.content, 
                "user_facts_used": user_facts,
                "documents_retrieved": len(retrieved_docs)
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
        """Retrieve relevant documents from FAISS vector store."""
        try:
            if self.retriever:
                return self.retriever.get_relevant_documents(question)
            return []
        except Exception as e:
            print(f"⚠️ Warning: Could not retrieve documents: {e}")
            return []

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
        print("Make sure Redis is running and properly configured.")
