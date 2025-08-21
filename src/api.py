from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from .agent.agent import Agent, create_agent
from typing import Optional
import json
import re
import os

# Feature flag for experimental changes
EXPERIMENTAL = os.getenv("EXPERIMENTAL") == "1"

# Initialize the agent lazily
agent = None

def get_agent():
    """Get or initialize the agent."""
    global agent
    if agent is None:
        if EXPERIMENTAL:
            agent = create_experimental_agent()
        else:
            agent = create_stable_agent()
    return agent

def create_stable_agent():
    """Create the stable, production-ready agent."""
    print("🟢 Using STABLE agent path")
    return create_agent(enable_debug_logging=True)

def create_experimental_agent():
    """Create the experimental agent with new features."""
    print("🔴 Using EXPERIMENTAL agent path")
    # For now, this is the same as stable, but can be modified for new features
    return create_agent(enable_debug_logging=True)

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    """Load environment variables on application startup."""
    from dotenv import load_dotenv
    load_dotenv()
    # Avoid unicode emojis in console output on Windows
    print("Environment variables loaded.")
    # Initialize the agent after loading env vars
    get_agent()

@app.get("/health")
def health_check():
    """Health check endpoint for smoke testing."""
    return {
        "status": "healthy",
        "experimental": EXPERIMENTAL,
        "timestamp": "2025-08-20T00:00:00Z"
    }

@app.get("/app.js")
def serve_app_js():
    js = '''(function(){
  function byId(id){return document.getElementById(id);} 
  var chatMessages=byId('chat-messages');
  var questionInput=byId('question-input');
  var sendButton=byId('send-button');
  var userIdInput=byId('user-id-input');
  var currentUserDisplay=byId('current-user-display');
  var chatListEl=byId('chat-list');
  var memBeforeEl=byId('mem-before');

  var currentUserId=null;
  var currentChatId=null;

  function lsGet(key, fallback){ try { return JSON.parse(localStorage.getItem(key)||''); } catch(e){ return fallback; } }
  function lsSet(key, value){ localStorage.setItem(key, JSON.stringify(value)); }
  function chatsKey(uid){ return 'mini_chat_conversations_'+uid; }
  function messagesKey(cid){ return 'mini_chat_messages_'+cid; }

  function renderMessages(messages){
    chatMessages.innerHTML='';
    if(!messages || !messages.length){
      var empty=document.createElement('div');
      empty.className='mx-auto max-w-2xl text-center text-sm muted';
      empty.textContent='Ask your first question to begin.';
      chatMessages.appendChild(empty);
      return;
    }
    for(var i=0;i<messages.length;i++){
      var m=messages[i];
      var row=document.createElement('div');
      row.className='flex ' + (m.role==='user'?'justify-end':'justify-start');
      var bubble=document.createElement('div');
      bubble.className='max-w-[80%] rounded-lg px-4 py-3 text-sm leading-relaxed ' + (m.role==='user' ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900' : 'bg-zinc-100 dark:bg-zinc-800');
      
      if(m.role==='assistant'){
        // Structure assistant messages with better formatting
        var content = m.content;
        
        // Split by double newlines to identify paragraphs
        var paragraphs = content.split('\\n\\n');
        if(paragraphs.length > 1){
          bubble.innerHTML = '';
          for(var p=0; p<paragraphs.length; p++){
            if(paragraphs[p].trim()){
              var pEl = document.createElement('div');
              pEl.className = 'mb-2 last:mb-0';
              pEl.textContent = paragraphs[p].trim();
              bubble.appendChild(pEl);
            }
          }
        } else {
          // Single paragraph or no clear structure
          bubble.textContent = content;
        }
      } else {
        bubble.textContent = m.content;
      }
      
      row.appendChild(bubble);
      chatMessages.appendChild(row);
    }
    chatMessages.scrollTop=chatMessages.scrollHeight;
  }

  function renderChatList(chats){
    chatListEl.innerHTML='';
    if(!chats || !chats.length){
      var div=document.createElement('div');
      div.className='text-xs muted px-1';
      div.textContent='No chats yet';
      chatListEl.appendChild(div);
      return;
    }
    chats.sort(function(a,b){ return b.createdAt - a.createdAt; });
    for(var i=0;i<chats.length;i++){
      (function(chat){
        var btn=document.createElement('button');
        btn.className='w-full text-left btn btn-ghost h-9 px-2';
        btn.innerHTML='<div class="truncate">'+chat.title+'</div>';
        btn.onclick=function(){ selectChat(chat.id); };
        chatListEl.appendChild(btn);
      })(chats[i]);
    }
  }

  function selectChat(chatId){
    currentChatId=chatId;
    var msgs=lsGet(messagesKey(chatId), []);
    renderMessages(msgs);
  }

  function appendMessage(role, content){
    var key=messagesKey(currentChatId);
    var msgs=lsGet(key, []);
    msgs.push({ role: role, content: content, t: Date.now() });
    lsSet(key, msgs);
    renderMessages(msgs);
  }

  function xhr(method, url, body, cb){
    var x=new XMLHttpRequest();
    x.open(method, url, true);
    if(body){ x.setRequestHeader('Content-Type','application/json'); }
    x.onreadystatechange=function(){ if(x.readyState===4){ cb(x); } };
    x.send(body?JSON.stringify(body):null);
  }

  window.setUserId=function(){
    var userId=(userIdInput.value||'').trim();
    if(!userId){ alert('Please enter a valid user ID'); return; }
    if(!/^[a-zA-Z0-9_-]+$/.test(userId)){ alert('Only letters, numbers, hyphens, underscores'); return; }
    if(userId.length>100){ alert('Max 100 chars'); return; }
    currentUserId=userId;
    localStorage.setItem('mini_chat_user_id', userId);
    currentUserDisplay.textContent='Current user: '+userId;
    questionInput.disabled=false; sendButton.disabled=false; questionInput.placeholder='Type your question...';
    if(!currentChatId){ window.createNewChat(); } else { var chats=lsGet(chatsKey(currentUserId), []); renderChatList(chats); selectChat(currentChatId); }
    window.refreshMemory(); questionInput.focus();
  };

  window.createNewChat=function(){
    if(!currentUserId){ alert('Set a user first'); return; }
    var id=currentUserId + '_' + Date.now();
    var chats=lsGet(chatsKey(currentUserId), []);
    chats.push({ id: id, title: 'New chat', createdAt: Date.now() });
    lsSet(chatsKey(currentUserId), chats);
    lsSet(messagesKey(id), []);
    renderChatList(chats);
    selectChat(id);
  };

  window.sendQuestion=function(){
    if(!currentUserId){ alert('Set your user ID first'); return; }
    if(!currentChatId){ window.createNewChat(); }
    var q=(questionInput.value||'').trim(); if(!q){ return; }
    questionInput.disabled=true; sendButton.disabled=true; sendButton.textContent='Sending...';
    appendMessage('user', q);
    xhr('POST','/chat?user_id='+encodeURIComponent(currentUserId), { q: q }, function(resp){
      var text='';
      try { var data=JSON.parse(resp.responseText||'{}'); text=data.answer || ('HTTP '+resp.status); }
      catch(e){ text='Error'; }
      appendMessage('assistant', text);
      questionInput.disabled=false; sendButton.disabled=false; sendButton.textContent='Send'; questionInput.value=''; questionInput.focus();
    });
  };

  window.clearHistory=function(silent){
    if(!currentUserId){ if(!silent) alert('Set a user first'); return; }
    xhr('DELETE','/conversation/'+encodeURIComponent(currentUserId), null, function(){
      if(currentChatId){ lsSet(messagesKey(currentChatId), []); renderMessages([]); }
    });
  };

  window.refreshMemory=function(){
    if(!currentUserId) return;
    xhr('GET','/memory/'+encodeURIComponent(currentUserId), null, function(resp){
      try{ var obj=JSON.parse(resp.responseText||'{}'); memBeforeEl.textContent=JSON.stringify(obj.memory||{}, null, 2); }catch(e){}
    });
  };

  window.addEventListener('load', function(){
    try{ var saved=localStorage.getItem('mini_chat_user_id'); if(saved){ userIdInput.value=saved; window.setUserId(); } }catch(e){}
  });
})();'''
    return Response(js, media_type='application/javascript')

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
        
        print(f"Received question from user {validated_user_id}: {body['q']}")
        
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
        
        print(f"Response generated successfully for user {validated_user_id}")
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        # Handle agent validation errors
        print(f"Validation error in chat endpoint: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Handle agent runtime errors
        print(f"Runtime error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/memory/{user_id}")
def get_user_memory(user_id: str):
    """Retrieve user memory from Redis."""
    try:
        # Validate user_id
        validated_user_id = validate_user_id(user_id)
        
        print(f"Retrieving memory for user: {validated_user_id}")
        
        # Get user memory from Redis using memory manager directly
        from .memory.redis_memory_manager import RedisMemoryManager
        memory_manager = RedisMemoryManager()
        user_memory = memory_manager.get_user_memory(validated_user_id)
        
        if user_memory is None:
            # Return empty memory structure if no memory exists
            user_memory = {}
        
        print(f"Memory retrieved successfully for user {validated_user_id}")
        return {
            "user_id": validated_user_id,
            "memory": user_memory,
            "status": "success"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"Error retrieving memory for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user memory: {str(e)}")

@app.post("/memory/{user_id}")
def update_user_memory(user_id: str, memory_data: dict):
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
        
        print(f"Updating memory for user: {validated_user_id}")
        
        # Update user memory using local memory manager directly
        from .memory.local_memory_manager import LocalMemoryManager
        memory_manager = LocalMemoryManager()
        memory_manager.update_user_memory(validated_user_id, memory_data)
        
        print(f"Memory updated successfully for user {validated_user_id}")
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
        print(f"Error updating memory for user {user_id}: {e}")
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
        
        print(f"Retrieving conversation history for user: {validated_user_id}")
        
        # Get conversation history from agent
        agent_instance = get_agent()
        conversation_history = agent_instance.get_conversation_history(validated_user_id, limit)
        
        print(f"Retrieved {len(conversation_history)} messages for user {validated_user_id}")
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
        print(f"Error retrieving conversation history for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve conversation history: {str(e)}")

@app.delete("/conversation/{user_id}")
def clear_conversation_history(user_id: str):
    """Clear conversation history for a user."""
    try:
        # Validate user_id
        validated_user_id = validate_user_id(user_id)
        
        print(f"Clearing conversation history for user: {validated_user_id}")
        
        # Clear conversation history from agent
        agent_instance = get_agent()
        agent_instance.clear_conversation_history(validated_user_id)
        
        print(f"Conversation history cleared for user {validated_user_id}")
        return {
            "user_id": validated_user_id,
            "status": "success",
            "message": "Conversation history cleared successfully"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"Error clearing conversation history for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear conversation history: {str(e)}")

@app.get("/session/{user_id}")
def get_session_info(user_id: str):
    """Get session information for a user."""
    try:
        # Validate user_id
        validated_user_id = validate_user_id(user_id)
        
        print(f"Retrieving session info for user: {validated_user_id}")
        
        # Get session info from agent
        agent_instance = get_agent()
        session_info = agent_instance.get_session_info(validated_user_id)
        
        print(f"Session info retrieved for user {validated_user_id}")
        return {
            **session_info,
            "status": "success"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        print(f"Error retrieving session info for user {user_id}: {e}")

@app.get("/conversation/{user_id}/code", response_class=PlainTextResponse)
def get_conversation_history_code(user_id: str, limit: Optional[int] = Query(None, description="Limit number of messages returned")):
    """Return conversation history as a JSON code block (markdown)."""
    try:
        validated_user_id = validate_user_id(user_id)
        if limit is not None and limit <= 0:
            raise HTTPException(status_code=400, detail="Limit must be a positive integer")

        agent_instance = get_agent()
        conversation_history = agent_instance.get_conversation_history(validated_user_id, limit)

        payload = {
            "user_id": validated_user_id,
            "messages": conversation_history,
            "message_count": len(conversation_history)
        }
        json_str = json.dumps(payload, indent=2, ensure_ascii=False)
        code_block = f"```json\n{json_str}\n```"
        return code_block
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating conversation code for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate conversation code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session info: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def chat_interface():
    return """
    <!DOCTYPE html>
    <html lang=\"en\">
    <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <title>Mini Chat — Clean Chat UI</title>
        <script src=\"https://cdn.tailwindcss.com\"></script>
        <style>
          /* Minimal shadcn-like tokens (uses Tailwind utilities under the hood) */
          .card { @apply rounded-lg border bg-white dark:bg-zinc-900 dark:border-zinc-800; }
          .muted { @apply text-zinc-500 dark:text-zinc-400; }
          .btn { @apply inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-400 disabled:pointer-events-none disabled:opacity-50; }
          .btn-primary { @apply bg-zinc-900 text-white hover:bg-zinc-800 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200; }
          .btn-ghost { @apply hover:bg-zinc-100 dark:hover:bg-zinc-800; }
          .input { @apply flex h-10 w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-zinc-500 focus:border-zinc-500 dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-100 dark:focus:ring-zinc-400 dark:focus:border-zinc-400 text-zinc-900 dark:text-zinc-100 placeholder-zinc-500 dark:placeholder-zinc-400; }
          .badge { @apply inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium; }
          .scrollbar-thin { scrollbar-width: thin; }
          
          /* Enhanced message styling */
          .chat-message-content {
            line-height: 1.6;
            word-wrap: break-word;
          }
          
          .chat-message-content ul, .chat-message-content ol {
            margin: 0.5rem 0;
            padding-left: 1.5rem;
          }
          
          .chat-message-content li {
            margin: 0.25rem 0;
          }
          
          .chat-message-content strong {
            font-weight: 600;
            color: inherit;
          }
          
          .chat-message-content .product-name {
            font-weight: 600;
            color: #1f2937;
            background: #f3f4f6;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            display: inline-block;
            margin: 0.25rem 0;
          }
          
          .dark .chat-message-content .product-name {
            color: #e5e7eb;
            background: #374151;
          }
          
          .chat-message-content .italic {
            font-style: italic;
            color: #6b7280;
          }
          
          .dark .chat-message-content .italic {
            color: #9ca3af;
          }
        </style>
    </head>
      <body class=\"h-screen w-screen bg-zinc-50 text-zinc-900 dark:bg-zinc-950 dark:text-zinc-50\">
        <div class=\"h-full w-full grid grid-cols-[280px_minmax(0,1fr)_360px] gap-4 p-4\">
          <!-- Left: sidebar -->
          <aside class=\"card p-3 flex flex-col pointer-events-auto\">
            <div class=\"flex items-center gap-2 px-2 py-2\">
              <div class=\"text-lg font-semibold\">Mini Chat</div>
              <span class=\"badge border-zinc-200 dark:border-zinc-800 muted\">memory UI</span>
                </div>
            <div class=\"mt-2 flex items-center gap-2\">
              <input id=\"user-id-input\" list=\"user-suggestions\" class=\"input\" placeholder=\"Select or type a user (e.g. dmt_test1)\" />
              <datalist id=\"user-suggestions\"></datalist>
              <button id=\"set-user-button\" type=\"button\" class=\"btn btn-primary h-10 px-3\" onclick=\"setUserId()\">Set</button>
            </div>
            <div id=\"user-error\" class=\"text-[11px] text-red-500 px-1 hidden\"></div>
            <div id=\"current-user-display\" class=\"mt-1 text-xs muted px-1\">No user set</div>
            <div class=\"mt-3\">
              <button id=\"new-chat-button\" type=\"button\" class=\"btn btn-ghost w-full h-9\" onclick=\"createNewChat()\">+ New chat</button>
                    </div>
            <div class=\"mt-2 text-xs font-medium px-1 uppercase muted\">Chats</div>
            <div id=\"chat-list\" class=\"mt-1 flex-1 overflow-y-auto scrollbar-thin space-y-1 pr-1\"></div>
          </aside>

          <!-- Middle: chat -->
          <main class=\"card p-0 flex flex-col min-h-0 pointer-events-auto\">
            <header class=\"flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 px-4 py-2\">
              <div>
                <div id=\"chat-title\" class=\"text-sm font-medium\">Welcome</div>
                <div class=\"text-xs muted\">Ask questions about your documents. Memory persists per user.</div>
                    </div>
              <div class=\"flex items-center gap-2\">
                <button class=\"btn btn-ghost h-8 px-2 text-xs\" onclick=\"clearHistory()\">Clear</button>
                <button class=\"btn btn-ghost h-8 px-2 text-xs\" onclick=\"refreshMemory()\">Refresh Memory</button>
                    </div>
            </header>

            <section id=\"chat-messages\" class=\"flex-1 min-h-0 overflow-y-auto p-4 space-y-3 bg-gradient-to-b from-transparent to-zinc-50 dark:to-zinc-950 scrollbar-thin\">
              <div class=\"mx-auto max-w-2xl text-center text-sm muted\">Set your user ID to start chatting.</div>
            </section>

            <footer class=\"sticky bottom-0 border-t border-zinc-100 dark:border-zinc-800 p-3 bg-white/90 dark:bg-zinc-900/90 backdrop-blur\">
              <div class=\"mx-auto max-w-2xl flex gap-2\">
                <input id=\"question-input\" class=\"input bg-white dark:bg-zinc-800 border-zinc-300 dark:border-zinc-600 focus:border-zinc-500 dark:focus:border-zinc-400 focus:ring-zinc-500 dark:focus:ring-zinc-400 text-zinc-900 dark:text-zinc-100 placeholder-zinc-500 dark:placeholder-zinc-400\" placeholder=\"Type your question...\" disabled />
                <button id=\"send-button\" class=\"btn btn-primary h-10 px-4\" onclick=\"sendQuestion()\" disabled>Send</button>
                </div>
            </footer>
          </main>

          <!-- Right: Memory Inspector -->
          <aside class=\"card p-3 flex flex-col min-h-0 pointer-events-auto\">
            <div class=\"text-sm font-medium\">Memory Inspector</div>
            <div class=\"text-xs muted\">Curate what matters for this turn.</div>

            <!-- Tabs -->
            <div class=\"mt-3 border-b border-zinc-100 dark:border-zinc-800\">
              <div class=\"flex gap-1 text-xs\">
                <button class=\"tab btn btn-ghost h-8 px-2 data-[active=true]:bg-zinc-100 dark:data-[active=true]:bg-zinc-800\" data-tab=\"overview\">Overview</button>
                <button class=\"tab btn btn-ghost h-8 px-2\" data-tab=\"selected\">Selected</button>
                <button class=\"tab btn btn-ghost h-8 px-2\" data-tab=\"changes\">Changes</button>
                <button class=\"tab btn btn-ghost h-8 px-2\" data-tab=\"all\">All</button>
                <button class=\"tab btn btn-ghost h-8 px-2 ml-auto\" data-tab=\"timeline\">Timeline</button>
                    </div>
                </div>
                
            <div class=\"mt-2 flex-1 min-h-0 overflow-hidden\">
              <div id=\"tab-overview\" class=\"h-full overflow-auto scrollbar-thin space-y-2\">
                <div id=\"kpi-overview\" class=\"text-xs flex flex-wrap gap-2\"></div>
                <div class=\"text-xs font-medium\">Top Context Picks</div>
                <div id=\"top-picks\" class=\"text-xs space-y-1\"></div>
                <div class=\"text-xs font-medium mt-2\">Gaps & Suggestions</div>
                <ul id=\"gap-suggestions\" class=\"text-xs list-disc ml-4\"></ul>
                </div>

              <div id=\"tab-selected\" class=\"hidden h-full overflow-auto scrollbar-thin\">
                <div class=\"text-xs flex items-center justify-between mb-2\">
                  <div id=\"token-budget\" class=\"muted\"></div>
                  <div class=\"flex gap-2\">
                    <button id=\"btn-select-all\" class=\"btn btn-ghost h-7 px-2\">Select all</button>
                    <button id=\"btn-unselect-all\" class=\"btn btn-ghost h-7 px-2\">Unselect all</button>
                  </div>
                </div>
                <table class=\"w-full text-xs\">
                  <thead class=\"sticky top-0 bg-white dark:bg-zinc-900\">
                    <tr class=\"text-left border-b border-zinc-100 dark:border-zinc-800\">
                      <th class=\"py-1 pr-2\">Include</th>
                      <th class=\"py-1 pr-2\">Fact</th>
                      <th class=\"py-1 pr-2\">Value</th>
                      <th class=\"py-1 pr-2\">Conf.</th>
                      <th class=\"py-1 pr-2\">Recency</th>
                      <th class=\"py-1\">Usage</th>
                    </tr>
                  </thead>
                  <tbody id=\"selected-table\"></tbody>
                </table>
            </div>
            
              <div id=\"tab-changes\" class=\"hidden h-full overflow-auto scrollbar-thin\">
                <div id=\"changes-summary\" class=\"text-xs flex gap-2 mb-2\"></div>
                <div id=\"changes-detail\" class=\"text-xs space-y-2\"></div>
                <div class=\"mt-3\">
                  <div class=\"text-xs font-medium mb-1\">Extracted Facts (this turn)</div>
                  <div id=\"mem-facts\" class=\"text-xs space-y-1\"></div>
                    </div>
                </div>
                
              <div id=\"tab-all\" class=\"hidden h-full overflow-auto scrollbar-thin\">
                <div id=\"mem-before\" class=\"text-xs space-y-1\">No data</div>
                    </div>

              <div id=\"tab-timeline\" class=\"hidden h-full overflow-auto scrollbar-thin\">
                <div id=\"timeline\" class=\"text-xs space-y-2\"></div>
                </div>
            </div>
          </aside>
        </div>

        <script>
          /*
          // Global error surface to help debugging in the UI (also see F12 console)
          window.addEventListener('error', (e)=>{
            try {
              let bar = document.getElementById('ui-error');
              if (!bar) {
                bar = document.createElement('div');
                bar.id = 'ui-error';
                bar.className = 'fixed top-2 left-1/2 -translate-x-1/2 max-w-[90vw] z-50 bg-red-600 text-white text-xs px-3 py-1 rounded';
                document.body.appendChild(bar);
              }
              var msg = (e && e.message) ? e.message : 'unknown';
              bar.textContent = 'UI error: ' + msg;
            } catch {}
          });
          console.log('UI: script loaded');
          const chatMessages = document.getElementById('chat-messages');
            const questionInput = document.getElementById('question-input');
            const sendButton = document.getElementById('send-button');
            const userIdInput = document.getElementById('user-id-input');
            const userError = document.getElementById('user-error');
            const userSuggestions = document.getElementById('user-suggestions');
            const currentUserDisplay = document.getElementById('current-user-display');
          const chatTitle = document.getElementById('chat-title');
          const chatListEl = document.getElementById('chat-list');
          const memBeforeEl = document.getElementById('mem-before');
          const memFactsEl = document.getElementById('mem-facts');
          const tabs = Array.from(document.querySelectorAll('.tab'));
          const tabViews = {
            overview: document.getElementById('tab-overview'),
            selected: document.getElementById('tab-selected'),
            changes: document.getElementById('tab-changes'),
            all: document.getElementById('tab-all'),
            timeline: document.getElementById('tab-timeline')
          };
          const kpiOverviewEl = document.getElementById('kpi-overview');
          const topPicksEl = document.getElementById('top-picks');
          const gapSuggestionsEl = document.getElementById('gap-suggestions');
          const tokenBudgetEl = document.getElementById('token-budget');
          const selectedTableBody = document.getElementById('selected-table');
          const changesSummaryEl = document.getElementById('changes-summary');
          const changesDetailEl = document.getElementById('changes-detail');
          const timelineEl = document.getElementById('timeline');
          console.log('UI: DOM refs ready');
            
            let currentUserId = null;
          let currentChatId = null;

          // Utilities
          const ls = {
            get(key, fallback) {
              try {
                const raw = localStorage.getItem(key);
                return raw !== null ? JSON.parse(raw) : fallback;
              } catch {
                return fallback;
              }
            },
            set(key, value) { localStorage.setItem(key, JSON.stringify(value)); }
          };

          function chatsKey(userId) { return `mini_chat_conversations_${userId}`; }
          function messagesKey(chatId) { return `mini_chat_messages_${chatId}`; }
          function usersKey() { return 'mini_chat_users'; }

          function formatJSON(obj) { try { return JSON.stringify(obj, null, 2); } catch { return String(obj); } }
          function titleize(s) {
            const txt = (s||'').replaceAll('_',' ');
            return txt.split(' ').map(w => w ? (w[0].toUpperCase() + w.slice(1)) : w).join(' ');
          }
          function ago(ms){ const d=(Date.now()-ms)/1000; if(d<60) return Math.floor(d)+'s'; if(d<3600) return Math.floor(d/60)+'m'; if(d<86400) return Math.floor(d/3600)+'h'; return Math.floor(d/86400)+'d'; }
          function renderFactsHTML(obj) {
            if (!obj || Object.keys(obj).length === 0) return '<div class="muted">No facts</div>';
            let html = '';
            const keys = Object.keys(obj).sort();
            for (const k of keys) {
              const v = obj[k];
              if (v && typeof v === 'object' && !Array.isArray(v)) {
                html += `<div><div class="font-medium">${titleize(k)}</div>`;
                html += '<ul class="ml-4 list-disc">';
                for (const sk of Object.keys(v)) {
                  html += `<li><span class="muted">${titleize(sk)}:</span> ${escapeHtml(String(v[sk]))}</li>`;
                }
                html += '</ul></div>';
              } else if (Array.isArray(v)) {
                html += `<div><span class="font-medium">${titleize(k)}:</span> <span class="muted">${v.length} item(s)</span><div class="mt-1 flex flex-wrap gap-1">${v.map(x=>`<span class="badge border-zinc-200 dark:border-zinc-800">${escapeHtml(String(x))}</span>`).join('')}</div></div>`;
              } else {
                html += `<div><span class="muted">${titleize(k)}:</span> ${escapeHtml(String(v))}</div>`;
              }
            }
            return html;
          }
          function renderFactsList(obj) {
            if (!obj || Object.keys(obj).length === 0) return '<div class="muted">No extracted facts</div>';
            let html = '<ul class="list-disc ml-4">';
            for (const [k,v] of Object.entries(obj)) {
              html += `<li><span class="font-medium">${titleize(k)}:</span> ${escapeHtml(String(v))}</li>`;
            }
            html += '</ul>';
            return html;
          }
          function renderDiffHTML(after, diff) {
            const counts = {
              total: Object.keys(after||{}).length,
              added: Object.keys(diff.added||{}).length,
              changed: Object.keys(diff.changed||{}).length,
              removed: Object.keys(diff.removed||{}).length,
            };
            let html = `<div class="flex gap-2 text-xs">`+
              `<span class="badge border-zinc-200 dark:border-zinc-800">Total ${counts.total}</span>`+
              `<span class="badge border-zinc-200 dark:border-zinc-800">+${counts.added}</span>`+
              `<span class="badge border-zinc-200 dark:border-zinc-800">~${counts.changed}</span>`+
              `<span class="badge border-zinc-200 dark:border-zinc-800">-${counts.removed}</span>`+
            `</div>`;
            if (counts.added) {
              html += '<div class="mt-2"><div class="font-medium">Added</div><ul class="ml-4 list-disc">';
              for (const [k,v] of Object.entries(diff.added)) html += `<li>${titleize(k)} = ${escapeHtml(String(v))}</li>`;
              html += '</ul></div>';
            }
            if (counts.changed) {
              html += '<div class="mt-2"><div class="font-medium">Changed</div><ul class="ml-4 list-disc">';
              for (const [k,obj] of Object.entries(diff.changed)) html += `<li>${titleize(k)}: <span class="muted">${escapeHtml(String(obj.before))}</span> → ${escapeHtml(String(obj.after))}</li>`;
              html += '</ul></div>';
            }
            if (counts.removed) {
              html += '<div class="mt-2"><div class="font-medium">Removed</div><ul class="ml-4 list-disc">';
              for (const [k,v] of Object.entries(diff.removed)) html += `<li>${titleize(k)} (was ${escapeHtml(String(v))})</li>`;
              html += '</ul></div>';
            }
            return html;
          }
          function escapeHtml(str){ const d=document.createElement('div'); d.textContent=String(str); return d.innerHTML; }

          // Tabs behavior
          function setActiveTab(name){
            for (const btn of tabs){ const active = btn.dataset.tab === name; btn.setAttribute('data-active', active ? 'true' : 'false'); }
            for (const [key,el] of Object.entries(tabViews)){ if(!el) continue; el.classList.toggle('hidden', key!==name); }
            localStorage.setItem('mini_chat_active_tab', name);
          }
          tabs.forEach(b=>b.addEventListener('click', ()=> setActiveTab(b.dataset.tab)));

          function diffObjects(before, after) {
            try {
              const added = {}; const changed = {}; const removed = {};
              const b = before || {}; const a = after || {};
              for (const k of Object.keys(a)) {
                if (!(k in b)) added[k] = a[k];
                else if (JSON.stringify(a[k]) !== JSON.stringify(b[k])) changed[k] = { before: b[k], after: a[k] };
              }
              for (const k of Object.keys(b)) { if (!(k in a)) removed[k] = b[k]; }
              return { added, changed, removed };
            } catch { return {}; }
          }

          // Initial load
          window.addEventListener('load', () => {
            console.log('UI: window load');
            const savedUserId = localStorage.getItem('mini_chat_user_id');
            if (savedUserId) { userIdInput.value = savedUserId; setUserId(); }
            setActiveTab(localStorage.getItem('mini_chat_active_tab')||'overview');
            // Populate suggestions
            try {
              const users = JSON.parse(localStorage.getItem(usersKey()) || '[]');
              userSuggestions.innerHTML = users.map(u=>`<option value="${u}"></option>`).join('');
            } catch {}
          });

          // Chat management
          function loadChats() {
            if (!currentUserId) return;
            const chats = ls.get(chatsKey(currentUserId), []);
            chatListEl.innerHTML = '';
            if (chats.length === 0) {
              const empty = document.createElement('div');
              empty.className = 'text-xs muted px-1';
              empty.textContent = 'No chats yet';
              chatListEl.appendChild(empty);
                    return;
                }
            for (const chat of chats.sort((a,b) => b.createdAt - a.createdAt)) {
              const btn = document.createElement('button');
              btn.className = 'w-full text-left btn btn-ghost h-9 px-2';
              btn.innerHTML = `<div class=\"truncate\">${chat.title}</div>`;
              btn.onclick = () => selectChat(chat.id);
              chatListEl.appendChild(btn);
            }
          }

          function selectChat(chatId) {
            currentChatId = chatId;
            const msgs = ls.get(messagesKey(chatId), []);
            renderMessages(msgs);
            const chats = ls.get(chatsKey(currentUserId), []);
            const meta = chats.find(c => c.id === chatId);
            chatTitle.textContent = (meta && meta.title) ? meta.title : 'Chat';
          }

          function createNewChat() {
            console.log('UI: createNewChat called');
            if (!currentUserId) { alert('Set a user first'); return; }
            // Start a fresh conversation on server
            clearHistory(true);
            const id = `${currentUserId}_${Date.now()}`;
            const chats = ls.get(chatsKey(currentUserId), []);
            chats.push({ id, title: 'New chat', createdAt: Date.now() });
            ls.set(chatsKey(currentUserId), chats);
            ls.set(messagesKey(id), []);
            selectChat(id);
            loadChats();
          }

          function updateCurrentChatTitleFromFirstUserMessage(text) {
            try {
              const chats = ls.get(chatsKey(currentUserId), []);
              const idx = chats.findIndex(c => c.id === currentChatId);
              if (idx >= 0 && (chats[idx].title === 'New chat' || chats[idx].title === 'Welcome')) {
                chats[idx].title = text.slice(0, 40) + (text.length > 40 ? '…' : '');
                ls.set(chatsKey(currentUserId), chats);
                loadChats();
              }
            } catch {}
          }

          // User/session
          function setUserId() {
            console.log('UI: setUserId called');
            const userId = (userIdInput.value || '').trim();
            userError.classList.add('hidden');
            if (!userId) { userError.textContent = 'Please enter a valid user ID'; userError.classList.remove('hidden'); return; }
            if (!/^[a-zA-Z0-9_-]+$/.test(userId)) { userError.textContent = 'Only letters, numbers, hyphens, underscores'; userError.classList.remove('hidden'); return; }
            if (userId.length > 100) { userError.textContent = 'Max 100 chars'; userError.classList.remove('hidden'); return; }
            currentUserId = userId;
                localStorage.setItem('mini_chat_user_id', userId);
                currentUserDisplay.textContent = `Current user: ${userId}`;
            questionInput.disabled = false; sendButton.disabled = false; questionInput.placeholder = 'Type your question...';
            if (!currentChatId) createNewChat(); else { loadChats(); selectChat(currentChatId); }
                refreshMemory();
                questionInput.focus();
            // Remember user in suggestions
            try {
              const users = JSON.parse(localStorage.getItem(usersKey()) || '[]');
              if (!users.includes(userId)) { users.unshift(userId); localStorage.setItem(usersKey(), JSON.stringify(users.slice(0,20))); }
              userSuggestions.innerHTML = users.map(u=>`<option value="${u}"></option>`).join('');
            } catch {}
            }

          // Quick apply on Enter or blur
          userIdInput.addEventListener('keydown', (e)=>{ if (e.key === 'Enter') setUserId(); });
          userIdInput.addEventListener('blur', ()=>{ if (!currentUserId) setUserId(); });
          userIdInput.addEventListener('change', ()=>{ if (userIdInput.value && userIdInput.value !== currentUserId) setUserId(); });

          // Expose functions globally to avoid any scoping issues
          window.setUserId = setUserId;
          window.createNewChat = createNewChat;
          window.clearHistory = clearHistory;
          window.refreshMemory = refreshMemory;
          window.sendQuestion = sendQuestion;
          console.log('UI: globals exported');

          // Chat flow
          if (questionInput) {
            questionInput.addEventListener('keypress', (e) => { if (e.key === 'Enter' && !sendButton.disabled) sendQuestion(); });
          }

          function renderMessages(messages) {
            chatMessages.innerHTML = '';
            if (!messages || messages.length === 0) {
              const empty = document.createElement('div');
              empty.className = 'mx-auto max-w-2xl text-center text-sm muted';
              empty.textContent = 'Ask your first question to begin.';
              chatMessages.appendChild(empty);
              return;
            }
            for (const m of messages) {
              const row = document.createElement('div');
              row.className = `flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`;
              const bubble = document.createElement('div');
              bubble.className = `max-w-[80%] rounded-lg px-4 py-3 text-sm ${m.role === 'user' ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900' : 'bg-zinc-100 dark:bg-zinc-800'}`;
              
              if (m.role === 'assistant') {
                // Parse and format structured content for assistant messages
                bubble.innerHTML = formatStructuredMessage(m.content);
                bubble.classList.add('chat-message-content');
              } else {
                bubble.textContent = m.content;
              }
              
              row.appendChild(bubble);
              chatMessages.appendChild(row);
            }
            chatMessages.scrollTop = chatMessages.scrollHeight;
          }

          function formatStructuredMessage(content) {
            if (!content) return '';
            
            // Split content into lines and process each line
            const lines = content.split('\n');
            let html = '';
            let inList = false;
            let listType = '';
            
            for (let i = 0; i < lines.length; i++) {
              const line = lines[i].trim();
              if (!line) {
                // Empty line - close any open lists and add spacing
                if (inList) {
                  html += `</${listType}>`;
                  inList = false;
                }
                html += '<div class="mb-3"></div>';
                continue;
              }
              
              // Check for headers (## or ###)
              if (line.startsWith('## ')) {
                if (inList) {
                  html += `</${listType}>`;
                  inList = false;
                }
                html += `<div class="font-semibold text-base mb-3 text-zinc-800 dark:text-zinc-200 border-b border-zinc-200 dark:border-zinc-700 pb-1">${escapeHtml(line.substring(3))}</div>`;
                continue;
              }
              
              if (line.startsWith('### ')) {
                if (inList) {
                  html += `</${listType}>`;
                  inList = false;
                }
                html += `<div class="font-medium text-sm mb-2 text-zinc-700 dark:text-zinc-300">${escapeHtml(line.substring(4))}</div>`;
                continue;
              }
              
              // Check for numbered lists (1. 2. etc.)
              if (/^[0-9]+\\.\\s/.test(line)) {
                if (!inList || listType !== 'ol') {
                  if (inList) html += `</${listType}>`;
                  html += '<ol class="list-decimal ml-4 mb-3 space-y-1">';
                  inList = true;
                  listType = 'ol';
                }
                html += `<li class="text-sm leading-relaxed">${escapeHtml(line.replace(/^[0-9]+\\.\\s/, ''))}</li>`;
                continue;
              }
              
              // Check for bullet points (- or *)
              if (line.startsWith('- ') || line.startsWith('* ')) {
                if (!inList || listType !== 'ul') {
                  if (inList) html += `</${listType}>`;
                  html += '<ul class="list-disc ml-4 mb-3 space-y-1">';
                  inList = true;
                  listType = 'ul';
                }
                html += `<li class="text-sm leading-relaxed">${escapeHtml(line.substring(2))}</li>`;
                continue;
              }
              
              // Check for bold text (**text**)
              if (line.includes('**') && line.split('**').length > 2) {
                const formattedLine = line.replace(/\\*\\*(.*?)\\*\\*/g, '<strong>$1</strong>');
                if (inList) {
                  html += `</${listType}>`;
                  inList = false;
                }
                html += `<div class="mb-2 text-sm leading-relaxed"><strong>${escapeHtml(line.replace(/\\*\\*(.*?)\\*\\*/g, '$1'))}</strong></div>`;
                continue;
              }
              
              // Check for product recommendations with SKU format
              if (line.includes('SKU:') || line.includes('SKU :')) {
                if (inList) {
                  html += `</${listType}>`;
                  inList = false;
                }
                // Highlight SKU information
                const formattedLine = line.replace(/(SKU:?\\s*[0-9]+)/g, '<span class="font-mono text-xs bg-zinc-200 dark:bg-zinc-700 px-1 py-0.5 rounded">$1</span>');
                html += `<div class="mb-2 text-sm leading-relaxed">${escapeHtml(formattedLine)}</div>`;
                continue;
              }
              
              // Check for key phrases in brackets [phrase]
              if (line.includes('[') && line.includes(']')) {
                if (inList) {
                  html += `</${listType}>`;
                  inList = false;
                }
                const formattedLine = line.replace(/\\[(.*?)\\]/g, '<span class="font-medium text-zinc-600 dark:text-zinc-400">[$1]</span>');
                html += `<div class="mb-2 text-sm leading-relaxed">${escapeHtml(formattedLine)}</div>`;
                continue;
              }
              
              // Check for product names (all caps words)
              if (/^[A-Z\\s&]+$/.test(line) && line.length > 3 && line.length < 50) {
                if (inList) {
                  html += `</${listType}>`;
                  inList = false;
                }
                html += `<div class="mb-2 text-sm product-name">${escapeHtml(line)}</div>`;
                continue;
              }
              
              // Check for emphasis (italic text with _text_)
              if (line.includes('_') && line.split('_').length > 2) {
                if (inList) {
                  html += `</${listType}>`;
                  inList = false;
                }
                html += `<div class="mb-2 text-sm leading-relaxed italic">${escapeHtml(line.replace(/_(.*?)_/g, '$1'))}</div>`;
                continue;
              }
              
              // Regular text line
              if (inList) {
                html += `</${listType}>`;
                inList = false;
              }
              html += `<div class="mb-2 text-sm leading-relaxed">${escapeHtml(line)}</div>`;
            }
            
            // Close any remaining open list
            if (inList) {
              html += `</${listType}>`;
            }
            
            return html;
          }

          function appendMessage(role, content) {
            const key = messagesKey(currentChatId);
            const msgs = ls.get(key, []);
            msgs.push({ role, content, t: Date.now() });
            ls.set(key, msgs);
            renderMessages(msgs);
          }

          async function sendQuestion() {
            if (!currentUserId) { alert('Set your user ID first'); return; }
            if (!currentChatId) createNewChat();
            const q = (questionInput.value || '').trim();
            if (!q) return;
            questionInput.disabled = true; sendButton.disabled = true; sendButton.textContent = 'Sending…';
            appendMessage('user', q);
            updateCurrentChatTitleFromFirstUserMessage(q);

            // Memory before
            let memBefore = {};
            try { const r = await fetch(`/memory/${encodeURIComponent(currentUserId)}`); if (r.ok) memBefore = (await r.json()).memory || {}; } catch {}
            memBeforeEl.innerHTML = renderFactsHTML(memBefore);
            updateOverview(memBefore);

            // Temporary assistant bubble
            const loadingId = 'loading-' + Date.now();
            const loadingRow = document.createElement('div');
            loadingRow.id = loadingId; loadingRow.className = 'flex justify-start';
            const loadingBubble = document.createElement('div');
            loadingBubble.className = 'max-w-[80%] rounded-lg px-3 py-2 text-sm bg-zinc-100 dark:bg-zinc-800 italic muted';
            loadingBubble.textContent = 'Thinking…';
            loadingRow.appendChild(loadingBubble); chatMessages.appendChild(loadingRow); chatMessages.scrollTop = chatMessages.scrollHeight;

            try {
              const resp = await fetch(`/chat?user_id=${encodeURIComponent(currentUserId)}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ q }) });
              if (!resp.ok) { const err = await resp.json(); throw new Error(err.detail || `HTTP ${resp.status}`); }
              const data = await resp.json();
              var el = document.getElementById(loadingId); if (el) el.remove();
              appendMessage('assistant', data.answer || 'No response');

              // Show extracted facts and after memory (with diff)
              memFactsEl.innerHTML = renderFactsList(data.extracted_facts || {});
              let memAfter = {};
              try { const r2 = await fetch(`/memory/${encodeURIComponent(currentUserId)}`); if (r2.ok) memAfter = (await r2.json()).memory || {}; } catch {}
              const d = diffObjects(memBefore, memAfter);
              updateSelected(memAfter);
              updateChanges(d);
              appendTimelineEvent({ type:'turn', at: Date.now(), added: Object.keys(d.added||{}).length, changed: Object.keys(d.changed||{}).length, removed: Object.keys(d.removed||{}).length });
            } catch (e) {
              var el2 = document.getElementById(loadingId); if (el2) el2.remove();
              appendMessage('assistant', '❌ ' + (e.message || 'Error'));
            } finally {
              questionInput.disabled = false; sendButton.disabled = false; sendButton.textContent = 'Send'; questionInput.value = ''; questionInput.focus();
            }
          }

          async function refreshHistory() {
            // Keep right pane history minimal; main chat uses local messages for speed
          }

            async function refreshMemory() {
                if (!currentUserId) return;
            try {
              const r = await fetch(`/memory/${encodeURIComponent(currentUserId)}`);
              if (r.ok) {
                const m = (await r.json()).memory || {};
                memBeforeEl.textContent = formatJSON(m);
              }
            } catch {}
          }

          async function clearHistory(silent=false) {
            if (!currentUserId) { if (!silent) alert('Set a user first'); return; }
            try {
              await fetch(`/conversation/${encodeURIComponent(currentUserId)}`, { method: 'DELETE' });
            } catch {}
            // Reset current chat messages locally
            if (currentChatId) ls.set(messagesKey(currentChatId), []);
            renderMessages([]);
            }

          // ---------- Inspector renderers ----------
          function scoreFact(f){
            const confidence = Number((f && f.confidence) != null ? f.confidence : 0.8);
            const hasLast = f && f.last_updated;
            const recency = hasLast ? Math.max(0, 1 - ((Date.now()-new Date(f.last_updated).getTime())/(1000*60*60*24*30))) : 0.5;
            const usage = Math.min(1, ((f && f.usage_count) != null ? f.usage_count : 0)/10);
            return 0.5*confidence + 0.3*recency + 0.2*usage;
          }

          function normalizeMemory(raw){
            // Wrap primitive values into rich fact objects
            const result = {};
            for (const [k,v] of Object.entries(raw||{})){
              if (v && typeof v === 'object' && !Array.isArray(v)){
                result[k] = v;
                    } else {
                result[k] = { value: v, confidence: 0.9, last_updated: new Date().toISOString(), usage_count: 0, include: true };
              }
            }
            return result;
          }

          function estimateTokens(selected){
            const text = Object.entries(selected).map(([k,v])=> `${k}: ${typeof v==='object' && 'value' in v ? v.value : v}`).join('\n');
            // rough: 1 token ≈ 4 chars
            const tokens = Math.ceil((text.length||0)/4);
            return { tokens, budget: 1200 };
          }

          function updateOverview(memory){
            const rich = normalizeMemory(memory);
            const entries = Object.entries(rich).map(([k,f])=>({ key:k, fact:f, score: scoreFact(f) })).sort((a,b)=>b.score-a.score);
            const top = entries.slice(0,5);
            kpiOverviewEl.innerHTML = ''+
              `<span class=\"badge border-zinc-200 dark:border-zinc-800\">Facts ${entries.length}</span>`+
              `<span class=\"badge border-zinc-200 dark:border-zinc-800\">Top ${top.length}</span>`;
            topPicksEl.innerHTML = top.map(e=>{
              const val = (e && e.fact && (e.fact.value !== undefined && e.fact.value !== null)) ? e.fact.value : (e && e.fact) ? e.fact : '';
              return `<div><span class=\"font-medium\">${titleize(e.key)}:</span> ${escapeHtml(String(val))} <span class=\"muted\">(score ${e.score.toFixed(2)})</span></div>`;
            }).join('');
            const gaps = [];
            if (!('target_market' in rich)) gaps.push('No target market specified');
            if (!('kpi' in rich)) gaps.push('No primary KPI set');
            if (!('timeline' in rich) && !('implementation_timeline' in rich)) gaps.push('No timeline identified');
            gapSuggestionsEl.innerHTML = gaps.length? gaps.map(g=>`<li>${escapeHtml(g)}</li>`).join('') : '<li class="muted">No obvious gaps</li>';
          }

          function updateSelected(memory){
            const rich = normalizeMemory(memory);
            const entries = Object.entries(rich).map(([k,f])=>({ key:k, fact:f, score: scoreFact(f) })).sort((a,b)=>b.score-a.score);
            const topPerCategory = entries; // simple for now
            selectedTableBody.innerHTML = topPerCategory.map(e=>{
              const f = e.fact;
              const include = f.include !== false;
              const recency = f.last_updated ? ago(new Date(f.last_updated).getTime()) : '—';
              return `<tr class=\"border-b border-zinc-100 dark:border-zinc-800\">`
                + `<td class=\"py-1\"><input type=\"checkbox\" ${include?'checked':''} data-key=\"${e.key}\" class=\"sel-toggle\"></td>`
                + `<td class=\"py-1 pr-2\">${titleize(e.key)}</td>`
                + `<td class=\"py-1 pr-2\">${escapeHtml(String((f.value!==undefined&&f.value!==null)?f.value:f))}</td>`
                + `<td class=\"py-1 pr-2\">${((((f.confidence!==undefined&&f.confidence!==null)?f.confidence:0.8)*100)|0)}%</td>`
                + `<td class=\"py-1 pr-2\">${recency}</td>`
                + `<td class=\"py-1\">${(f.usage_count!==undefined&&f.usage_count!==null)?f.usage_count:0}</td>`
                + `</tr>`;
            }).join('');

            // Token budget
            const toSend = Object.fromEntries(entries.filter(e=> (e.fact.include!==false)).map(e=>[e.key, e.fact]));
            const {tokens, budget} = estimateTokens(toSend);
            tokenBudgetEl.textContent = `Using ~${tokens} tokens of ${budget} budget`;

            // Wire toggles (local only for now)
            selectedTableBody.querySelectorAll('.sel-toggle').forEach(cb=>{
              cb.addEventListener('change', ()=>{
                const key = cb.dataset.key; if (rich[key]) rich[key].include = cb.checked;
                const {tokens, budget} = estimateTokens(Object.fromEntries(Object.entries(rich).filter(([k,f])=>f.include!==false)));
                tokenBudgetEl.textContent = `Using ~${tokens} tokens of ${budget} budget`;
              });
            });
          }

          function updateChanges(diff){
            const counts = {
              added: Object.keys(diff.added||{}).length,
              changed: Object.keys(diff.changed||{}).length,
              removed: Object.keys(diff.removed||{}).length
            };
            changesSummaryEl.innerHTML = ''+
              `<span class=\"badge border-zinc-200 dark:border-zinc-800\">+ ${counts.added}</span>`+
              `<span class=\"badge border-zinc-200 dark:border-zinc-800\">~ ${counts.changed}</span>`+
              `<span class=\"badge border-zinc-200 dark:border-zinc-800\">- ${counts.removed}</span>`;
            let html = '';
            if (counts.added){ html += '<div><div class=\"font-medium\">Added</div><ul class=\"ml-4 list-disc\">' + Object.entries(diff.added||{}).map(([k,v])=>`<li>${titleize(k)} = ${escapeHtml(String(v))}</li>`).join('') + '</ul></div>'; }
            if (counts.changed){ html += '<div><div class=\"font-medium\">Changed</div><ul class=\"ml-4 list-disc\">' + Object.entries(diff.changed||{}).map(([k,v])=>`<li>${titleize(k)}: <span class=\"muted\">${escapeHtml(String(v.before))}</span> → ${escapeHtml(String(v.after))}</li>`).join('') + '</ul></div>'; }
            if (counts.removed){ html += '<div><div class=\"font-medium\">Removed</div><ul class=\"ml-4 list-disc\">' + Object.entries(diff.removed||{}).map(([k,v])=>`<li>${titleize(k)} (was ${escapeHtml(String(v))})</li>`).join('') + '</ul></div>'; }
            changesDetailEl.innerHTML = html || '<div class="muted">No changes this turn</div>';
          }

          function appendTimelineEvent(evt){
            const row = document.createElement('div');
            row.innerHTML = `<div><span class=\"font-medium\">Turn</span> · +${evt.added} ~${evt.changed} -${evt.removed} <span class=\"muted\">${ago(evt.at)}</span></div>`;
            timelineEl.prepend(row);
            }
          */
        </script>
        <script src="/app.js"></script>
    </body>
    </html>
    """
