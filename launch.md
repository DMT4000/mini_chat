
# How to Launch the Mini Chat Application

This document provides the steps to set up the necessary services and run the Mini Chat application.

## Prerequisites

- Python 3.8+
- An OpenAI API key
- Docker and Docker Compose (Optional, only required if running Redis locally)

## Step 1: Set Up Your Environment

Before launching the application, ensure your environment is configured correctly.

1.  **Create a `.env` file** in the root of the project by copying the `.env.template` file.

2.  **Add your OpenAI API Key** to the `.env` file:
    ```
    OPENAI_API_KEY=your_openai_api_key_here
    ```

3.  **Add your Redis Cloud Credentials** to the `.env` file. You can find these in your Redis Cloud account dashboard.
    ```
    # Redis Configuration (Cloud)
    REDIS_HOST="your-redis-host.redns.redis-cloud.com"
    REDIS_PORT="your-redis-port"
    REDIS_PASSWORD="your-redis-password"
    ```

## Step 2: Install Dependencies

Install the required Python packages using pip:

```shell
pip install -r requirements.txt
```

## Step 3: Ingest Your Documents

The first time you run the application, you need to process your source documents and create a searchable vector index.

Run the following command from the project root:

```shell
python src/ingest.py
```

This will read the files in the `/docs` directory and create a `faiss_index` folder. You only need to run this again if you add or change the documents.

## Step 4: Launch the Application

To start the web server, run the following command from the project root:

```shell
python -m uvicorn src.api:app --reload --port 8000
```

The server will start, and you will see output similar to this in your terminal:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx]
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
✅ Environment variables loaded.
✅ Successfully connected to Redis instance from Memory Manager.
INFO:     Application startup complete.
```

## Step 5: Access the Chat Interface

Open your web browser and navigate to the following URL:

[http://127.0.0.1:8000](http://127.0.0.1:8000)

You can now interact with your AI assistant. Remember to set a `user_id` in the interface to take advantage of the persistent memory feature.

---

## Troubleshooting

### Connection Error to `localhost:6379`

If you encounter an error message in the UI like `Error: Internal server error: Redis connection failed... connecting to localhost:6379`, it means the application is not correctly loading your cloud credentials from the `.env` file and is falling back to the default local address.

**Solution:**
Ensure that your `src/api.py` file includes the `startup_event` that loads the environment variables when the application starts. This was the fix applied to resolve this issue. If the error persists, check that your `.env` file is in the project's root directory and is formatted correctly.
