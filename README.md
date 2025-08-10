
# Mini Chat

This project is a chat application that uses a local FAISS vector store to answer questions about documents in the `docs` directory.

## Project Structure

```
mini_chat/
├── .env
├── .gitignore
├── cool-chatbot/
│   ├── .git/
│   └── arduino
├── docs/
│   ├── project_info.txt
│   └── sample.txt
├── faiss_index/
│   ├── index.faiss
│   └── index.pkl
├── README.md
├── setup_env.py
└── src/
    ├── api.py
    ├── chat.py
    ├── ingest.py
    ├── prompts/
    │   └── qa.yaml
    ├── prompt_registry.py
    ├── __init__.py
    └── __pycache__/
```

- **`.env`**: This file stores environment variables, including the OpenAI API key.
- **`cool-chatbot/`**: This directory contains a Git repository and an Arduino project.
- **`docs/`**: This directory contains the text files that the chat application will use to answer questions.
- **`faiss_index/`**: This directory contains the FAISS index, which is a vector store that allows for efficient similarity search.
- **`setup_env.py`**: This script creates the `.env` file and checks if the OpenAI API key is set.
- **`src/`**: This directory contains the source code for the chat application.

## How it works

The chat application has two main components:

- **Ingestion**: The `ingest.py` script reads all the text files in the `docs` directory, creates a FAISS index from them, and saves the index to the `faiss_index` directory. This is done by using OpenAI's `text-embedding-3-small` model to create embeddings for each document.
- **Chat**: The `chat.py` script uses the FAISS index to answer questions. When a user asks a question, the script first retrieves the most relevant documents from the index. Then, it uses the `gpt-4o-mini` model to generate an answer based on the retrieved documents.

The `api.py` script creates a FastAPI server that exposes a `/chat` endpoint for handling user queries and a `/` endpoint for serving the chat interface.

## How to use

1. **Set up the environment**: Run the `setup_env.py` script to create the `.env` file and check if the OpenAI API key is set.

2. **Ingest the documents**: Run the `ingest.py` script to create the FAISS index.

3. **Start the chat server**: Run the `api.py` script to start the chat server.

4. **Open the chat interface**: Open a web browser and go to `http://localhost:8000` to open the chat interface.

## Tool Usage

- **`langchain`**: This project uses the `langchain` library to create the FAISS index and to interact with the OpenAI API.
- **`fastapi`**: This project uses the `fastapi` library to create the chat server.
- **`uvicorn`**: This project uses the `uvicorn` library to run the chat server.
- **`faiss`**: This project uses the `faiss` library to create the FAISS index.
- **`openai`**: This project uses the `openai` library to interact with the OpenAI API.
- **`dotenv`**: This project uses the `dotenv` library to load environment variables from the `.env` file.
- **`langgraph`**: This project uses the `langgraph` library to create the chat graph.

The user can upgrade the agent to be more potent by:

- **Using a different language model**: The `chat.py` script uses the `gpt-4o-mini` model by default. The user can change this to a different model by modifying the `llm` variable in the `chat.py` script.
- **Using a different vector store**: The `ingest.py` script uses the FAISS vector store by default. The user can change this to a different vector store by modifying the `build_index` function in the `ingest.py` script.
- **Using a different prompt**: The `chat.py` script uses the `qa` prompt by default. The user can change this to a different prompt by modifying the `ask` function in the `chat.py` script.
- **Adding more documents**: The user can add more documents to the `docs` directory to improve the chat application's knowledge base.
- **Improving the chat interface**: The user can improve the chat interface by modifying the `chat_interface` function in the `api.py` script.
- **Adding more features**: The user can add more features to the chat application, such as the ability to save chat history, by modifying the source code.
- **Improving the Arduino project**: The user can improve the Arduino project in the `cool-chatbot/` directory to add more features to the chat application.

To get started, please follow the instructions in the "How to use" section.
