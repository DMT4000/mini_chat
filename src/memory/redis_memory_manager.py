
import os
import redis
import json
from typing import Dict, Any
from dotenv import load_dotenv

class RedisMemoryManager:
    def __init__(self):
        """Initialize Redis connection with proper error handling."""
        # Load environment variables from .env file
        load_dotenv()
        
        redis_host = os.getenv("REDIS_HOST")
        redis_port = os.getenv("REDIS_PORT")
        redis_password = os.getenv("REDIS_PASSWORD")
        
        if not all([redis_host, redis_port]):
            raise ValueError("Missing required Redis connection details (REDIS_HOST, REDIS_PORT) in .env file.")
            
        try:
            # Create Redis client with proper configuration
            self.client = redis.Redis(
                host=redis_host,
                port=int(redis_port),
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            self.client.ping()
            print("✅ Successfully connected to Redis instance from Memory Manager.")
            
        except redis.exceptions.AuthenticationError as e:
            error_msg = f"Redis authentication failed. Please check your REDIS_PASSWORD: {str(e)}"
            print(f"❌ {error_msg}")
            raise ConnectionError(error_msg)
            
        except redis.exceptions.ConnectionError as e:
            error_msg = f"Redis connection failed. Please check Redis server is running and connection details are correct: {str(e)}"
            print(f"❌ {error_msg}")
            raise ConnectionError(error_msg)
            
        except ValueError as e:
            error_msg = f"Invalid Redis configuration: {str(e)}"
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error connecting to Redis: {str(e)}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg)

    def get_user_memory(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieves long-term memory for a user with proper error handling.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Dictionary containing user's memory facts, empty dict if no memory exists
            
        Raises:
            ValueError: If user_id is invalid
            ConnectionError: If Redis operation fails
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
            
        key = f"user:{user_id}:long_term"
        
        try:
            raw_data = self.client.get(key)
            if raw_data:
                return json.loads(raw_data)
            return {}
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to deserialize memory data for user {user_id}: {str(e)}"
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)
            
        except redis.exceptions.ConnectionError as e:
            error_msg = f"Redis connection error while retrieving memory for user {user_id}: {str(e)}"
            print(f"❌ {error_msg}")
            raise ConnectionError(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error retrieving memory for user {user_id}: {str(e)}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg)

    def save_user_memory(self, user_id: str, facts: Dict[str, Any]) -> None:
        """
        Saves/overwrites the long-term memory for a user with proper error handling.
        
        Args:
            user_id: Unique identifier for the user
            facts: Dictionary of facts to store
            
        Raises:
            ValueError: If user_id or facts are invalid
            ConnectionError: If Redis operation fails
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
            
        if not isinstance(facts, dict):
            raise ValueError("facts must be a dictionary")
            
        key = f"user:{user_id}:long_term"
        
        try:
            serialized_data = json.dumps(facts)
            self.client.set(key, serialized_data)
            print(f"Memory saved for user {user_id}.")
            
        except (TypeError, ValueError) as e:
            error_msg = f"Failed to serialize memory data for user {user_id}: {str(e)}"
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)
            
        except redis.exceptions.ConnectionError as e:
            error_msg = f"Redis connection error while saving memory for user {user_id}: {str(e)}"
            print(f"❌ {error_msg}")
            raise ConnectionError(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error saving memory for user {user_id}: {str(e)}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg)

    def update_user_memory(self, user_id: str, new_facts: Dict[str, Any]) -> None:
        """
        Updates the long-term memory for a user with new facts, merging with existing memory.
        
        Args:
            user_id: Unique identifier for the user
            new_facts: Dictionary of new facts to merge with existing memory
            
        Raises:
            ValueError: If user_id or new_facts are invalid
            ConnectionError: If Redis operation fails
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
            
        if not isinstance(new_facts, dict):
            raise ValueError("new_facts must be a dictionary")
            
        try:
            # Get existing memory
            existing_memory = self.get_user_memory(user_id)
            
            # Validate memory schema and size before merging
            merged_memory = self._merge_memory(existing_memory, new_facts)
            self._validate_memory_size(merged_memory, user_id)
            
            # Save merged memory
            self.save_user_memory(user_id, merged_memory)
            print(f"Memory updated for user {user_id}.")
            
        except (ValueError, ConnectionError, RuntimeError):
            # Re-raise known exceptions
            raise
            
        except Exception as e:
            error_msg = f"Unexpected error updating memory for user {user_id}: {str(e)}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg)

    def _merge_memory(self, existing: Dict[str, Any], new_facts: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge new facts with existing memory, handling nested dictionaries properly.
        
        Args:
            existing: Existing memory dictionary
            new_facts: New facts to merge
            
        Returns:
            Merged memory dictionary
        """
        merged = existing.copy()
        
        for key, value in new_facts.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                merged[key] = self._merge_memory(merged[key], value)
            else:
                # Overwrite or add new key-value pairs
                merged[key] = value
                
        return merged

    def _validate_memory_size(self, memory: Dict[str, Any], user_id: str) -> None:
        """
        Validate memory size and perform cleanup if necessary.
        
        Args:
            memory: Memory dictionary to validate
            user_id: User identifier for logging
            
        Raises:
            ValueError: If memory exceeds size limits after cleanup
        """
        # Convert to JSON to check serialized size
        try:
            serialized = json.dumps(memory)
            size_bytes = len(serialized.encode('utf-8'))
            
            # Set memory limit to 1MB per user
            MAX_MEMORY_SIZE = 1024 * 1024  # 1MB
            
            if size_bytes > MAX_MEMORY_SIZE:
                print(f"⚠️ Memory size ({size_bytes} bytes) exceeds limit for user {user_id}. Performing cleanup...")
                
                # Simple cleanup strategy: keep only the most recent entries
                # This is a basic implementation - could be enhanced with more sophisticated strategies
                cleaned_memory = self._cleanup_memory(memory, MAX_MEMORY_SIZE)
                
                # Validate cleaned memory size
                cleaned_serialized = json.dumps(cleaned_memory)
                cleaned_size = len(cleaned_serialized.encode('utf-8'))
                
                if cleaned_size > MAX_MEMORY_SIZE:
                    raise ValueError(f"Memory size ({cleaned_size} bytes) still exceeds limit after cleanup for user {user_id}")
                
                # Update the memory reference
                memory.clear()
                memory.update(cleaned_memory)
                print(f"✅ Memory cleaned up for user {user_id}. New size: {cleaned_size} bytes")
                
        except (TypeError, ValueError) as e:
            if "exceeds limit" in str(e):
                raise
            error_msg = f"Failed to validate memory size for user {user_id}: {str(e)}"
            raise ValueError(error_msg)

    def _cleanup_memory(self, memory: Dict[str, Any], max_size: int) -> Dict[str, Any]:
        """
        Clean up memory by removing older or less important entries.
        
        Args:
            memory: Memory dictionary to clean up
            max_size: Maximum allowed size in bytes
            
        Returns:
            Cleaned memory dictionary
        """
        # Simple cleanup strategy: keep essential keys and truncate large values
        essential_keys = ['name', 'preferences', 'context', 'recent_topics']
        cleaned = {}
        
        # First, preserve essential information
        for key in essential_keys:
            if key in memory:
                cleaned[key] = memory[key]
        
        # Check if we're under the limit with just essential keys
        serialized = json.dumps(cleaned)
        current_size = len(serialized.encode('utf-8'))
        
        if current_size >= max_size:
            # If still too large, truncate string values
            for key, value in cleaned.items():
                if isinstance(value, str) and len(value) > 1000:
                    cleaned[key] = value[:1000] + "... [truncated]"
        else:
            # Add other keys if we have space
            remaining_space = max_size - current_size
            for key, value in memory.items():
                if key not in essential_keys:
                    value_size = len(json.dumps({key: value}).encode('utf-8'))
                    if value_size < remaining_space:
                        cleaned[key] = value
                        remaining_space -= value_size
                    else:
                        break
        
        return cleaned
