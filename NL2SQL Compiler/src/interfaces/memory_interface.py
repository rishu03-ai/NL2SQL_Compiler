"""
Memory Store Interface (Dependency Inversion Principle)

This abstract interface handles conversation memory/history.
Can be implemented with in-memory storage, file-based, or database-backed storage.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class ConversationMessage(BaseModel):
    """A single message in the conversation history."""
    id: str
    session_id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: Optional[dict] = None  # For storing SQL queries, results, etc.


class ConversationSession(BaseModel):
    """A conversation session containing multiple messages."""
    session_id: str
    created_at: datetime
    updated_at: datetime
    messages: List[ConversationMessage] = []
    title: Optional[str] = None  # Auto-generated from first message


class IMemoryStore(ABC):
    """
    Abstract interface for conversation memory storage.
    
    Implementations can store messages in memory, files, or databases.
    This follows the Dependency Inversion Principle.
    """
    
    @abstractmethod
    async def create_session(self) -> ConversationSession:
        """
        Create a new conversation session.
        
        Returns:
            New ConversationSession object
        """
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """
        Retrieve a conversation session by ID.
        
        Args:
            session_id: The session identifier
            
        Returns:
            ConversationSession or None if not found
        """
        pass
    
    @abstractmethod
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> ConversationMessage:
        """
        Add a message to a conversation session.
        
        Args:
            session_id: The session to add to
            role: "user" or "assistant"
            content: The message content
            metadata: Optional additional data (SQL, results, etc.)
            
        Returns:
            The created ConversationMessage
        """
        pass
    
    @abstractmethod
    async def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        """
        Get messages from a session.
        
        Args:
            session_id: The session to get messages from
            limit: Optional limit on number of messages (most recent)
            
        Returns:
            List of ConversationMessage objects
        """
        pass
    
    @abstractmethod
    async def get_all_sessions(self) -> List[ConversationSession]:
        """
        Get all conversation sessions.
        
        Returns:
            List of all ConversationSession objects
        """
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a conversation session.
        
        Args:
            session_id: The session to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def clear_all(self) -> None:
        """Delete all sessions and messages."""
        pass
