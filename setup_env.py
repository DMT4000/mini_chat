#!/usr/bin/env python3
"""
Setup script to configure environment variables for the mini_chat application.
"""

import os
from pathlib import Path

def create_env_file():
    """Create a .env file with the required environment variables."""
    env_content = """# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Server Configuration
PORT=8000
HOST=127.0.0.1
"""
    
    env_path = Path(".env")
    if env_path.exists():
        print("✅ .env file already exists")
        return
    
    try:
        with open(env_path, "w") as f:
            f.write(env_content)
        print("✅ Created .env file")
        print("📝 Please edit .env file and add your OpenAI API key")
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")

def check_api_key():
    """Check if OpenAI API key is set."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key != "your_openai_api_key_here":
        print("✅ OpenAI API key is set")
        return True
    else:
        print("❌ OpenAI API key not set")
        print("Please set your OpenAI API key in the .env file")
        return False

if __name__ == "__main__":
    print("🔧 Setting up environment variables...")
    create_env_file()
    check_api_key()
    print("\n📋 Next steps:")
    print("1. Edit .env file and add your OpenAI API key")
    print("2. Run: python src/ingest.py")
    print("3. Run: python -m uvicorn src.api:app --reload --port 8000") 