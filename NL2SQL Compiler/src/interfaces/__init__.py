# Interfaces module - Abstract base classes for SOLID compliance
# These define contracts that concrete implementations must follow

from .llm_interface import ILLMService
from .database_interface import IDatabaseAdapter
from .agent_interface import IAgent
from .memory_interface import IMemoryStore

__all__ = [
    "ILLMService",
    "IDatabaseAdapter", 
    "IAgent",
    "IMemoryStore"
]
