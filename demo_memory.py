#!/usr/bin/env python3
"""
Interactive demo of the memory system.

This script allows you to interactively test how the AI remembers
user information across conversations.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.chat import ChatPipeline

def demo_memory_system():
    """Interactive demo of the memory system."""
    print("🧠 AI Memory System Demo")
    print("=" * 50)
    print("This demo shows how the AI can remember information about you!")
    print("Try telling it things like:")
    print("  - 'My name is John'")
    print("  - 'I like pizza'")
    print("  - 'I work as a developer'")
    print("  - 'Remember that I prefer detailed answers'")
    print("\nThen ask it to recall what it knows about you!")
    print("Type 'exit' to quit, 'help' for commands, 'memory' to see your stored info")
    print("=" * 50)
    
    # Initialize chat pipeline
    try:
        chat_pipeline = ChatPipeline()
        print("✅ Chat pipeline initialized successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize chat pipeline: {e}")
        return
    
    # Get user ID
    user_id = input("\n👤 Enter your user ID (or press Enter for 'demo_user'): ").strip()
    if not user_id:
        user_id = "demo_user"
    
    print(f"👋 Hello! I'll remember everything you tell me as user '{user_id}'")
    
    # Main conversation loop
    conversation_count = 0
    while True:
        try:
            # Get user input
            user_input = input(f"\n👤 [{conversation_count + 1}] ").strip()
            
            if not user_input:
                continue
            
            # Handle special commands
            if user_input.lower() == 'exit':
                print("👋 Goodbye! I'll remember everything you told me for next time.")
                break
            elif user_input.lower() == 'help':
                print_help()
                continue
            elif user_input.lower() == 'memory':
                show_user_memory(chat_pipeline, user_id)
                continue
            elif user_input.lower() == 'clear':
                clear_user_memory(chat_pipeline, user_id)
                continue
            
            # Process the question/statement
            print("🤖 Processing...")
            response = chat_pipeline.ask(user_input, user_id)
            
            # Display response
            print(f"\n🤖 [{conversation_count + 1}] {response['answer']}")
            
            # Show what memory was used
            if response.get('user_facts_used'):
                print(f"💭 Using stored memory: {len(response['user_facts_used'])} facts")
            
            conversation_count += 1
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! Your memory is saved.")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Please try again or type 'help' for assistance.")

def print_help():
    """Print help information."""
    print("\n📖 Available Commands:")
    print("  help     - Show this help message")
    print("  memory   - Show what I remember about you")
    print("  clear    - Clear your stored memory")
    print("  exit     - Exit the demo")
    print("\n💡 Memory Tips:")
    print("  - Tell me facts about yourself: 'My name is Alice'")
    print("  - Share preferences: 'I prefer short answers'")
    print("  - Ask me to remember: 'Remember that I love coffee'")
    print("  - Test my memory: 'What do you know about me?'")

def show_user_memory(chat_pipeline, user_id):
    """Show the user's stored memory."""
    try:
        memory = chat_pipeline.memory_manager.get_user_memory(user_id)
        if memory and "facts" in memory:
            facts = memory["facts"]
            print(f"\n💾 Your stored memory ({len(facts)} facts):")
            for key, value in facts.items():
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for sub_key, sub_value in value.items():
                        print(f"    {sub_key}: {sub_value}")
                else:
                    print(f"  {key}: {value}")
        else:
            print("\n💭 I don't have any stored memory about you yet.")
            print("Try telling me something about yourself!")
    except Exception as e:
        print(f"❌ Error retrieving memory: {e}")

def clear_user_memory(chat_pipeline, user_id):
    """Clear the user's stored memory."""
    try:
        confirm = input(f"🗑️ Are you sure you want to clear all memory for user '{user_id}'? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            chat_pipeline.memory_manager.delete_user_memory(user_id)
            print("✅ Memory cleared successfully!")
        else:
            print("❌ Memory clear cancelled.")
    except Exception as e:
        print(f"❌ Error clearing memory: {e}")

def main():
    """Main entry point."""
    try:
        demo_memory_system()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
