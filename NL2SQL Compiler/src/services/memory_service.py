"""
In-Memory Store Implementation

Concrete implementation of IMemoryStore using in-memory storage.
For production, this can be replaced with a database-backed implementation.
"""

import uuid
from datetime import datetime
from typing import List, Optional, Dict

from ..interfaces.memory_interface import (
    IMemoryStore, 
    ConversationMessage, 
    ConversationSession
)


class InMemoryStore(IMemoryStore):
    """
    In-Memory conversation storage implementation.
    
    Stores all conversations in memory. Data is lost on restart.
    Good for development and testing. For production, use a
    persistent implementation (database-backed).
    """
    
    def __init__(self):
        """Initialize empty storage."""
        self._sessions: Dict[str, ConversationSession] = {}
        self._messages: Dict[str, List[ConversationMessage]] = {}
    
    async def create_session(self) -> ConversationSession:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())
        now = datetime.now()
        
        session = ConversationSession(
            session_id=session_id,
            created_at=now,
            updated_at=now,
            messages=[]
        )
        
        self._sessions[session_id] = session
        self._messages[session_id] = []
        
        return session
    
    async def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Retrieve a conversation session by ID."""
        session = self._sessions.get(session_id)
        
        if session:
            # Include messages
            session.messages = self._messages.get(session_id, [])
        
        return session
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> ConversationMessage:
        """Add a message to a conversation session."""
        
        # Create session if it doesn't exist
        if session_id not in self._sessions:
            session = await self.create_session()
            session.session_id = session_id
            self._sessions[session_id] = session
            self._messages[session_id] = []
        
        message = ConversationMessage(
            id=str(uuid.uuid4()),
            session_id=session_id,
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata
        )
        
        self._messages[session_id].append(message)
        
        # Update session timestamp
        self._sessions[session_id].updated_at = datetime.now()
        
        # Set title from first user message
        if role == "user" and not self._sessions[session_id].title:
            # Use first 50 chars of first message as title
            self._sessions[session_id].title = content[:50] + ("..." if len(content) > 50 else "")
        
        return message
    
    async def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        """Get messages from a session."""
        messages = self._messages.get(session_id, [])
        
        if limit:
            return messages[-limit:]  # Return most recent
        
        return messages
    
    async def get_all_sessions(self) -> List[ConversationSession]:
        """Get all conversation sessions."""
        sessions = list(self._sessions.values())
        
        # Attach messages and sort by updated_at
        for session in sessions:
            session.messages = self._messages.get(session.session_id, [])
        
        return sorted(sessions, key=lambda s: s.updated_at, reverse=True)
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a conversation session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            del self._messages[session_id]
            return True
        return False
    
    async def clear_all(self) -> None:
        """Delete all sessions and messages."""
        self._sessions.clear()
        self._messages.clear()
