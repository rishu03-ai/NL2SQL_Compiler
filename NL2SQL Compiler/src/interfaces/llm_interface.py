"""
LLM Service Interface (Dependency Inversion Principle)

This abstract interface allows us to swap LLM providers (Groq, OpenAI, Gemini)
without changing the code that depends on LLM functionality.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Represents a single message in a conversation."""
    role: str  # "user", "assistant", or "system"
    content: str


class LLMResponse(BaseModel):
    """Standardized response from any LLM provider."""
    content: str
    model: str
    tokens_used: Optional[int] = None
    raw_response: Optional[Dict[str, Any]] = None


class ILLMService(ABC):
    """
    Abstract interface for LLM services.
    
    Any LLM provider (Groq, OpenAI, Gemini, etc.) must implement this interface.
    This follows the Dependency Inversion Principle - high-level modules depend
    on abstractions, not concrete implementations.
    """
    
    @abstractmethod
    async def generate(
        self, 
        messages: List[ChatMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            messages: List of conversation messages
            system_prompt: Optional system instruction
            temperature: Creativity parameter (0.0 to 1.0)
            
        Returns:
            LLMResponse with the generated content
        """
        pass
    
    @abstractmethod
    async def generate_sql(
        self,
        natural_language_query: str,
        schema_info: str,
        conversation_context: Optional[List[ChatMessage]] = None
    ) -> str:
        """
        Generate SQL from natural language query.
        
        Args:
            natural_language_query: The user's question in plain English
            schema_info: Database schema information
            conversation_context: Previous messages for context
            
        Returns:
            Generated SQL query string
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return the name of the current model being used."""
        pass
