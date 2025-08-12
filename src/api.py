from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from .agent.agent import Agent, create_agent
from typing import Optional
import re

# Initialize the agent lazily
agent = None

def get_agent():
    """Get or initialize the agent."""
    global agent
    if agent is None:
        agent = create_agent(enable_debug_logging=True)
    return agent

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Load environment variables on application startup."""
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded.")
    # Initialize the agent after loading env vars
    get_agent()

def validate_user_id(user_id: str) -> str:
    """Validate user_id format and return cleaned version."""
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="user_id cannot be empty")
    
    # Clean the user_id - remove extra whitespace and ensure reasonable length
    cleaned_user_id = user_id.strip()
    
    if len(cleaned_user_id) > 100:
        raise HTTPException(status_code=400, detail="user_id must be 100 characters or less")
    
    # Ensure user_id contains only safe characters (alphanumeric, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9_-]+$', cleaned_user_id):
        raise HTTPException(status_code=400, detail="user_id can only contain letters, numbers, hyphens, and underscores")
    
    return cleaned_user_id

@app.post("/chat")
def chat(body: dict, user_id: str = Query(..., description="Unique identifier for the user")):
    try:
        # Validate required fields
        if "q" not in body or not body["q"]:
            raise HTTPException(status_code=400, detail="Question 'q' is required and cannot be empty")
        
        # Validate and clean user_id
        validated_user_id = validate_user_id(user_id)
        
        print(f"🔍 Received question from user {validated_user_id}: {body['q']}")
        
        # Use the Agent with user_id
        agent_instance = get_agent()
        result = agent_instance.run(validated_user_id, body["q"])
        
        # Transform agent response to maintain backward compatibility
        response = {
            "answer": result["answer"],
            "user_id": result["user_id"],
            "question": result["question"],
            "extracted_facts": result["extracted_facts"],
            "execution_time": result["execution_time"],
            "conversation_turn": result["conversation_turn"]
        }
        
        print(f"✅ Response generated successfully for user {validated_user_id}")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        # Handle agent validation errors
        print(f"❌ Validation error in chat endpoint: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Handle agent runtime errors
        print(f"❌ Runtime error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/memory/{user_id}")
def get_user_memory(user_id: str):
    """Retrieve user memory from Redis."""
    try:
        # Validate user_id
        validated_user_id = validate_user_id(user_id)
        
        print(f"🔍 Retrieving memory for user: {validated_user_id}")
        
        # Get user memory from Redis using memory manager directly
        from .memory.redis_memory_manager import RedisMemoryManager
        memory_manager = RedisMemoryManager()
        user_memory = memory_manager.get_user_memory(validated_user_id)
        
        if user_memory is None:
            # Return empty memory structure if no memory exists
            user_memory = {}
        
        print(f"✅ Memory retrieved successfully for user {validated_user_id}")
        return {
            "user_id": validated_user_id,
            "memory": user_memory,
            "status": "success"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Error retrieving memory for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user memory: {str(e)}")

@app.post("/memory/{user_id}")
def update_user_memory(user_id: str, memory_data: dict):  # nosec B106: FastAPI handles path params safely
    """Update user memory in Redis."""
    try:
        # Validate user_id
        validated_user_id = validate_user_id(user_id)
        
        # Validate memory_data
        if not isinstance(memory_data, dict):
            raise HTTPException(status_code=400, detail="Memory data must be a JSON object")
        
        # Check if memory_data is empty
        if not memory_data:
            raise HTTPException(status_code=400, detail="Memory data cannot be empty")
        
        print(f"🔍 Updating memory for user: {validated_user_id}")
        
        # Update user memory in Redis using memory manager directly
        from .memory.redis_memory_manager import RedisMemoryManager
        memory_manager = RedisMemoryManager()
        memory_manager.update_user_memory(validated_user_id, memory_data)
        
        print(f"✅ Memory updated successfully for user {validated_user_id}")
        return {
            "user_id": validated_user_id,
            "updated_facts": memory_data,
            "status": "success",
            "message": "User memory updated successfully"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Error updating memory for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update user memory: {str(e)}")

@app.get("/conversation/{user_id}")
def get_conversation_history(user_id: str, limit: Optional[int] = Query(None, description="Limit number of messages returned")):
    """Retrieve conversation history for a user."""
    try:
        # Validate user_id
        validated_user_id = validate_user_id(user_id)
        
        # Validate limit parameter
        if limit is not None and limit <= 0:
            raise HTTPException(status_code=400, detail="Limit must be a positive integer")
        
        print(f"🔍 Retrieving conversation history for user: {validated_user_id}")
        
        # Get conversation history from agent
        agent_instance = get_agent()
        conversation_history = agent_instance.get_conversation_history(validated_user_id, limit)
        
        print(f"✅ Retrieved {len(conversation_history)} messages for user {validated_user_id}")
        return {
            "user_id": validated_user_id,
            "conversation_history": conversation_history,
            "message_count": len(conversation_history),
            "status": "success"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Error retrieving conversation history for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve conversation history: {str(e)}")

@app.delete("/conversation/{user_id}")
def clear_conversation_history(user_id: str):
    """Clear conversation history for a user."""
    try:
        # Validate user_id
        validated_user_id = validate_user_id(user_id)
        
        print(f"🔍 Clearing conversation history for user: {validated_user_id}")
        
        # Clear conversation history from agent
        agent_instance = get_agent()
        agent_instance.clear_conversation_history(validated_user_id)
        
        print(f"✅ Conversation history cleared for user {validated_user_id}")
        return {
            "user_id": validated_user_id,
            "status": "success",
            "message": "Conversation history cleared successfully"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Error clearing conversation history for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear conversation history: {str(e)}")

@app.get("/session/{user_id}")
def get_session_info(user_id: str):
    """Get session information for a user."""
    try:
        # Validate user_id
        validated_user_id = validate_user_id(user_id)
        
        print(f"🔍 Retrieving session info for user: {validated_user_id}")
        
        # Get session info from agent
        agent_instance = get_agent()
        session_info = agent_instance.get_session_info(validated_user_id)
        
        print(f"✅ Session info retrieved for user {validated_user_id}")
        return {
            **session_info,
            "status": "success"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"❌ Error retrieving session info for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session info: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def chat_interface():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Mini Chat - Test Interface</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .chat-container {
                background: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                display: grid;
                grid-template-columns: 1fr 300px;
                gap: 20px;
            }
            .main-chat {
                min-width: 0;
            }
            .sidebar {
                background: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
                border: 1px solid #dee2e6;
            }
            .chat-header {
                text-align: center;
                margin-bottom: 20px;
                color: #333;
            }
            .user-info {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 20px;
            }
            .user-info h3 {
                margin: 0 0 10px 0;
                color: #495057;
            }
            .user-input-container {
                display: flex;
                gap: 10px;
                align-items: center;
                margin-bottom: 10px;
            }
            #user-id-input {
                flex: 1;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 3px;
                font-size: 14px;
            }
            #set-user-button {
                padding: 8px 15px;
                background: #28a745;
                color: white;
                border: none;
                border-radius: 3px;
                cursor: pointer;
                font-size: 14px;
            }
            #set-user-button:hover {
                background: #218838;
            }
            .current-user {
                font-size: 14px;
                color: #6c757d;
            }
            .chat-messages {
                height: 400px;
                overflow-y: auto;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                margin-bottom: 20px;
                background: #fafafa;
            }
            .message {
                margin-bottom: 15px;
                padding: 10px;
                border-radius: 5px;
            }
            .user-message {
                background: #007bff;
                color: white;
                margin-left: 20%;
            }
            .bot-message {
                background: #e9ecef;
                color: #333;
                margin-right: 20%;
            }
            .input-container {
                display: flex;
                gap: 10px;
            }
            #question-input {
                flex: 1;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
            }
            #send-button {
                padding: 10px 20px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
            }
            #send-button:hover {
                background: #0056b3;
            }
            #send-button:disabled {
                background: #6c757d;
                cursor: not-allowed;
            }
            .loading {
                text-align: center;
                color: #666;
                font-style: italic;
            }
            .disabled-overlay {
                position: relative;
            }
            .disabled-overlay::after {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(255, 255, 255, 0.7);
                z-index: 1;
            }
            .sidebar h4 {
                margin: 0 0 10px 0;
                color: #495057;
                font-size: 14px;
                font-weight: bold;
            }
            .facts-container, .history-container {
                margin-bottom: 20px;
            }
            .facts-list, .history-list {
                max-height: 150px;
                overflow-y: auto;
                font-size: 12px;
                line-height: 1.4;
            }
            .fact-item {
                background: #e9ecef;
                padding: 5px 8px;
                margin: 3px 0;
                border-radius: 3px;
                border-left: 3px solid #007bff;
            }
            .history-item {
                background: #fff;
                padding: 5px 8px;
                margin: 3px 0;
                border-radius: 3px;
                border-left: 3px solid #28a745;
            }
            .clear-button {
                background: #dc3545;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                cursor: pointer;
                font-size: 12px;
                margin-top: 10px;
            }
            .clear-button:hover {
                background: #c82333;
            }
            .refresh-button {
                background: #17a2b8;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                cursor: pointer;
                font-size: 12px;
                margin-left: 5px;
            }
            .refresh-button:hover {
                background: #138496;
            }
            @media (max-width: 1024px) {
                .chat-container {
                    grid-template-columns: 1fr;
                }
                .sidebar {
                    order: -1;
                }
            }
        </style>
    </head>
    <body>
        <div class="chat-container">
            <div class="main-chat">
                <div class="chat-header">
                    <h1>🤖 AI Co-founder Chat Interface</h1>
                    <p>Ask questions about your documents with persistent memory!</p>
                </div>
                
                <div class="user-info">
                    <h3>👤 User Identification</h3>
                    <div class="user-input-container">
                        <input type="text" id="user-id-input" placeholder="Enter your user ID (e.g., john_doe)" />
                        <button id="set-user-button" onclick="setUserId()">Set User</button>
                    </div>
                    <div class="current-user" id="current-user-display">
                        No user set - please enter a user ID to start chatting
                    </div>
                </div>
                
                <div class="chat-messages" id="chat-messages">
                    <div class="message bot-message">
                        👋 Hello! Please set your user ID above, then I'll be ready to answer questions about your documents with persistent memory!
                    </div>
                </div>
                
                <div class="input-container" id="chat-input-container">
                    <input type="text" id="question-input" placeholder="Type your question here..." disabled />
                    <button id="send-button" onclick="sendQuestion()" disabled>Send</button>
                </div>
            </div>
            
            <div class="sidebar">
                <div class="facts-container">
                    <h4>🧠 Extracted Facts</h4>
                    <div class="facts-list" id="facts-list">
                        <div style="color: #6c757d; font-style: italic;">No facts extracted yet</div>
                    </div>
                    <button class="refresh-button" onclick="refreshMemory()">Refresh</button>
                </div>
                
                <div class="history-container">
                    <h4>💬 Conversation History</h4>
                    <div class="history-list" id="history-list">
                        <div style="color: #6c757d; font-style: italic;">No conversation history</div>
                    </div>
                    <button class="refresh-button" onclick="refreshHistory()">Refresh</button>
                    <button class="clear-button" onclick="clearHistory()">Clear History</button>
                </div>
            </div>
        </div>

        <script>
            const questionInput = document.getElementById('question-input');
            const sendButton = document.getElementById('send-button');
            const chatMessages = document.getElementById('chat-messages');
            const userIdInput = document.getElementById('user-id-input');
            const setUserButton = document.getElementById('set-user-button');
            const currentUserDisplay = document.getElementById('current-user-display');
            const chatInputContainer = document.getElementById('chat-input-container');
            const factsList = document.getElementById('facts-list');
            const historyList = document.getElementById('history-list');
            
            let currentUserId = null;

            // Load saved user ID from localStorage on page load
            window.addEventListener('load', function() {
                const savedUserId = localStorage.getItem('mini_chat_user_id');
                if (savedUserId) {
                    userIdInput.value = savedUserId;
                    setUserId();
                }
            });

            // Add event listeners
            questionInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter' && !sendButton.disabled) {
                    sendQuestion();
                }
            });

            userIdInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    setUserId();
                }
            });

            function setUserId() {
                const userId = userIdInput.value.trim();
                
                if (!userId) {
                    alert('Please enter a valid user ID');
                    return;
                }

                // Validate user ID format (basic client-side validation)
                if (!/^[a-zA-Z0-9_-]+$/.test(userId)) {
                    alert('User ID can only contain letters, numbers, hyphens, and underscores');
                    return;
                }

                if (userId.length > 100) {
                    alert('User ID must be 100 characters or less');
                    return;
                }

                // Set current user
                currentUserId = userId;
                
                // Save to localStorage for session persistence
                localStorage.setItem('mini_chat_user_id', userId);
                
                // Update UI
                currentUserDisplay.textContent = `Current user: ${userId}`;
                questionInput.disabled = false;
                sendButton.disabled = false;
                questionInput.placeholder = 'Type your question here...';
                
                // Clear chat and add welcome message
                chatMessages.innerHTML = '';
                addMessage(`👋 Hello ${userId}! I'm ready to answer questions about your documents. I'll remember our conversation and learn about you over time.`, 'bot');
                
                // Load user memory and conversation history
                refreshMemory();
                refreshHistory();
                
                // Focus on question input
                questionInput.focus();
            }

            async function sendQuestion() {
                if (!currentUserId) {
                    alert('Please set your user ID first');
                    return;
                }

                const question = questionInput.value.trim();
                if (!question) return;

                // Disable input while processing
                questionInput.disabled = true;
                sendButton.disabled = true;
                sendButton.textContent = 'Sending...';

                // Add user message
                addMessage(question, 'user');

                // Add loading message
                const loadingId = addMessage('Thinking...', 'bot', true);

                try {
                    const response = await fetch(`/chat?user_id=${encodeURIComponent(currentUserId)}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ q: question })
                    });

                    if (!response.ok) {
                        const errorData = await response.json();
                        throw new Error(errorData.detail || `HTTP ${response.status}`);
                    }

                    const data = await response.json();
                    
                    // Remove loading message
                    removeMessage(loadingId);
                    
                    // Add bot response
                    const answer = data.answer || 'No response received';
                    addMessage(answer, 'bot');

                    // Show additional info if available
                    if (data.extracted_facts && Object.keys(data.extracted_facts).length > 0) {
                        console.log('New facts extracted:', data.extracted_facts);
                        // Refresh the facts display
                        setTimeout(refreshMemory, 500);
                    }
                    
                    // Refresh conversation history
                    setTimeout(refreshHistory, 500);

                } catch (error) {
                    // Remove loading message
                    removeMessage(loadingId);
                    addMessage('❌ Error: ' + error.message, 'bot');
                }

                // Re-enable input
                questionInput.disabled = false;
                sendButton.disabled = false;
                sendButton.textContent = 'Send';
                questionInput.value = '';
                questionInput.focus();
            }

            function addMessage(text, sender, isTemporary = false) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${sender}-message`;
                messageDiv.textContent = text;
                
                if (isTemporary) {
                    messageDiv.id = 'loading-message';
                }
                
                chatMessages.appendChild(messageDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
                
                return isTemporary ? 'loading-message' : null;
            }

            function removeMessage(messageId) {
                const message = document.getElementById(messageId);
                if (message) {
                    message.remove();
                }
            }

            async function refreshMemory() {
                if (!currentUserId) return;
                
                try {
                    const response = await fetch(`/memory/${encodeURIComponent(currentUserId)}`);
                    if (response.ok) {
                        const data = await response.json();
                        displayFacts(data.memory);
                    } else {
                        console.error('Failed to fetch memory:', response.status);
                    }
                } catch (error) {
                    console.error('Error fetching memory:', error);
                }
            }

            function displayFacts(memory) {
                const factsList = document.getElementById('facts-list');
                
                if (!memory || Object.keys(memory).length === 0) {
                    factsList.innerHTML = '<div style="color: #6c757d; font-style: italic;">No facts stored yet</div>';
                    return;
                }
                
                let factsHtml = '';
                for (const [key, value] of Object.entries(memory)) {
                    if (typeof value === 'object' && value !== null) {
                        // Handle nested objects
                        for (const [subKey, subValue] of Object.entries(value)) {
                            factsHtml += `<div class="fact-item"><strong>${key}.${subKey}:</strong> ${subValue}</div>`;
                        }
                    } else {
                        factsHtml += `<div class="fact-item"><strong>${key}:</strong> ${value}</div>`;
                    }
                }
                
                factsList.innerHTML = factsHtml;
            }

            async function refreshHistory() {
                if (!currentUserId) return;
                
                try {
                    const response = await fetch(`/conversation/${encodeURIComponent(currentUserId)}?limit=10`);
                    if (response.ok) {
                        const data = await response.json();
                        displayHistory(data.conversation_history);
                    } else {
                        console.error('Failed to fetch conversation history:', response.status);
                    }
                } catch (error) {
                    console.error('Error fetching conversation history:', error);
                }
            }

            function displayHistory(history) {
                const historyList = document.getElementById('history-list');
                
                if (!history || history.length === 0) {
                    historyList.innerHTML = '<div style="color: #6c757d; font-style: italic;">No conversation history</div>';
                    return;
                }
                
                let historyHtml = '';
                // Show only the last few messages to avoid clutter
                const recentHistory = history.slice(-6);
                
                for (const message of recentHistory) {
                    const role = message.role === 'user' ? '👤' : '🤖';
                    const content = message.content.length > 50 ? 
                        message.content.substring(0, 50) + '...' : 
                        message.content;
                    
                    historyHtml += `<div class="history-item">${role} ${content}</div>`;
                }
                
                historyList.innerHTML = historyHtml;
            }

            async function clearHistory() {
                if (!currentUserId) {
                    alert('Please set a user ID first');
                    return;
                }
                
                if (!confirm('Are you sure you want to clear your conversation history?')) {
                    return;
                }
                
                try {
                    const response = await fetch(`/conversation/${encodeURIComponent(currentUserId)}`, {
                        method: 'DELETE'
                    });
                    
                    if (response.ok) {
                        // Clear the chat messages display
                        chatMessages.innerHTML = '';
                        addMessage(`🗑️ Conversation history cleared for ${currentUserId}`, 'bot');
                        
                        // Refresh the history display
                        refreshHistory();
                    } else {
                        alert('Failed to clear conversation history');
                    }
                } catch (error) {
                    console.error('Error clearing history:', error);
                    alert('Error clearing conversation history');
                }
            }
        </script>
    </body>
    </html>
    """
