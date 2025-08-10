"""
Memory management module for AI Co-founder Evolution.

This module provides persistent memory capabilities using Redis
for storing and retrieving user-specific context and facts.
"""

from .redis_memory_manager import RedisMemoryManager

__all__ = ['RedisMemoryManager']