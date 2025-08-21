"""
Local file-based memory manager for storing user memory without external dependencies.

This module provides the same interface as RedisMemoryManager but stores data locally
in JSON files, making it perfect for development and testing without Redis.
"""

import json
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LocalMemoryManager:
    """
    Local file-based memory manager that stores user memory in JSON files.
    
    This class provides the same interface as RedisMemoryManager but stores
    data locally, making it perfect for development and testing.
    """
    
    def __init__(self, memory_dir: str = "user_memory"):
        """
        Initialize the local memory manager.
        
        Args:
            memory_dir: Directory to store memory files (relative to project root)
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        
        # Create a metadata file to track all users
        self.metadata_file = self.memory_dir / "users_metadata.json"
        self._ensure_metadata_file()
        
        logger.info(f"Local memory manager initialized. Memory directory: {self.memory_dir.absolute()}")
    
    def _ensure_metadata_file(self):
        """Ensure the users metadata file exists."""
        if not self.metadata_file.exists():
            with open(self.metadata_file, 'w') as f:
                json.dump({}, f)
    
    def _get_user_memory_file(self, user_id: str) -> Path:
        """Get the memory file path for a specific user."""
        # Sanitize user_id to create a safe filename
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in ('-', '_')).rstrip()
        return self.memory_dir / f"user_{safe_user_id}_memory.json"
    
    def _load_users_metadata(self) -> Dict[str, Any]:
        """Load the users metadata file."""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            return {}
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load users metadata: {e}")
            return {}
    
    def _save_users_metadata(self, metadata: Dict[str, Any]):
        """Save the users metadata file."""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        except IOError as e:
            logger.error(f"Could not save users metadata: {e}")
    
    def get_user_memory(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieves long-term memory for a user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            Dictionary containing user's memory facts, empty dict if no memory exists
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        
        memory_file = self._get_user_memory_file(user_id)
        
        try:
            if memory_file.exists():
                with open(memory_file, 'r') as f:
                    user_memory = json.load(f)
                    logger.info(f"Memory loaded for user {user_id}")
                    return user_memory
            else:
                logger.info(f"No memory file found for user {user_id}")
                return {}
                
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading memory for user {user_id}: {e}")
            return {}
    
    def save_user_memory(self, user_id: str, facts: Dict[str, Any]) -> None:
        """
        Saves/overwrites the long-term memory for a user.
        
        Args:
            user_id: Unique identifier for the user
            facts: Dictionary of facts to store
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
            
        if not isinstance(facts, dict):
            raise ValueError("facts must be a dictionary")
        
        memory_file = self._get_user_memory_file(user_id)
        
        try:
            # Add metadata
            memory_data = {
                "user_id": user_id,
                "facts": facts,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "version": "1.0"
            }
            
            # Save memory file
            with open(memory_file, 'w') as f:
                json.dump(memory_data, f, indent=2)
            
            # Update users metadata
            metadata = self._load_users_metadata()
            metadata[user_id] = {
                "memory_file": str(memory_file),
                "created_at": memory_data["created_at"],
                "updated_at": memory_data["updated_at"],
                "fact_count": len(facts)
            }
            self._save_users_metadata(metadata)
            
            logger.info(f"Memory saved for user {user_id}")
            
        except IOError as e:
            error_msg = f"Failed to save memory for user {user_id}: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def update_user_memory(self, user_id: str, new_facts: Dict[str, Any]) -> None:
        """
        Updates the long-term memory for a user by merging new facts.
        
        Args:
            user_id: Unique identifier for the user
            new_facts: Dictionary of new facts to merge
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
            
        if not isinstance(new_facts, dict):
            raise ValueError("new_facts must be a dictionary")
        
        # Get existing memory
        existing_memory = self.get_user_memory(user_id)
        
        # Merge new facts with existing ones
        if existing_memory:
            # If we have existing memory, merge the facts
            if "facts" in existing_memory:
                existing_facts = existing_memory["facts"]
            else:
                # Handle legacy format where facts were stored directly
                existing_facts = existing_memory
            
            # Deep merge the facts
            merged_facts = self._deep_merge_dicts(existing_facts, new_facts)
        else:
            # No existing memory, use new facts as-is
            merged_facts = new_facts
        
        # Save the merged memory
        self.save_user_memory(user_id, merged_facts)
        logger.info(f"Memory updated for user {user_id}")
    
    def _deep_merge_dicts(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries, with dict2 taking precedence for conflicts.
        
        Args:
            dict1: First dictionary
            dict2: Second dictionary (takes precedence)
            
        Returns:
            Merged dictionary
        """
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._deep_merge_dicts(result[key], value)
            else:
                # Overwrite or add the value
                result[key] = value
        
        return result
    
    def delete_user_memory(self, user_id: str) -> bool:
        """
        Deletes all memory for a user.
        
        Args:
            user_id: Unique identifier for the user
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        
        memory_file = self._get_user_memory_file(user_id)
        
        try:
            # Remove memory file
            if memory_file.exists():
                memory_file.unlink()
            
            # Update metadata
            metadata = self._load_users_metadata()
            if user_id in metadata:
                del metadata[user_id]
                self._save_users_metadata(metadata)
            
            logger.info(f"Memory deleted for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting memory for user {user_id}: {e}")
            return False
    
    def list_users(self) -> List[str]:
        """
        List all users who have memory stored.
        
        Returns:
            List of user IDs
        """
        metadata = self._load_users_metadata()
        return list(metadata.keys())
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about stored memory.
        
        Returns:
            Dictionary with memory statistics
        """
        metadata = self._load_users_metadata()
        
        total_users = len(metadata)
        total_facts = sum(user_data.get("fact_count", 0) for user_data in metadata.values())
        
        return {
            "total_users": total_users,
            "total_facts": total_facts,
            "memory_directory": str(self.memory_dir.absolute()),
            "users": list(metadata.keys())
        }
    
    def cleanup_old_memory(self, days_old: int = 30) -> int:
        """
        Clean up memory files older than specified days.
        
        Args:
            days_old: Remove files older than this many days
            
        Returns:
            Number of files removed
        """
        from datetime import timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        removed_count = 0
        
        metadata = self._load_users_metadata()
        users_to_remove = []
        
        for user_id, user_data in metadata.items():
            try:
                last_updated = datetime.fromisoformat(user_data["updated_at"])
                if last_updated < cutoff_date:
                    users_to_remove.append(user_id)
            except (ValueError, KeyError):
                # Skip users with invalid dates
                continue
        
        # Remove old users
        for user_id in users_to_remove:
            if self.delete_user_memory(user_id):
                removed_count += 1
        
        logger.info(f"Cleaned up {removed_count} old memory files")
        return removed_count
