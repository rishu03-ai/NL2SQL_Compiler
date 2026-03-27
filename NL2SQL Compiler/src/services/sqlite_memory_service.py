"""
SQLite Memory Store Implementation

Persistent storage for conversation history using SQLite.
Sessions and messages survive application restarts.
"""

import uuid
import json
import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Dict
from contextlib import contextmanager

from ..interfaces.memory_interface import (
    IMemoryStore,
    ConversationMessage,
    ConversationSession
)


class SqliteMemoryStore(IMemoryStore):
    """
    SQLite-based persistent conversation storage.
    
    Stores all conversations in a SQLite database.
    Data persists across application restarts.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize SQLite memory store.
        
        Args:
            db_path: Path to SQLite database file (defaults to ./chat_history.db)
        """
        self.db_path = db_path or os.getenv("MEMORY_DB_PATH", "./chat_history.db")
        self._connection: Optional[sqlite3.Connection] = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()
        
        # Create sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Create messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
        """)
        
        # Create index for faster message queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session 
            ON messages(session_id, timestamp)
        """)
        
        conn.commit()
        conn.close()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connection."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    async def create_session(self) -> ConversationSession:
        """Create a new conversation session."""
        session_id = str(uuid.uuid4())
        now = datetime.now()
        now_str = now.isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (session_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, None, now_str, now_str)
            )
            conn.commit()
        
        return ConversationSession(
            session_id=session_id,
            created_at=now,
            updated_at=now,
            messages=[],
            title=None
        )
    
    async def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Retrieve a conversation session by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Get session
            cursor.execute(
                "SELECT * FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Get messages
            messages = await self.get_messages(session_id)
            
            return ConversationSession(
                session_id=row["session_id"],
                title=row["title"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                messages=messages
            )
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> ConversationMessage:
        """Add a message to a conversation session."""
        
        message_id = str(uuid.uuid4())
        now = datetime.now()
        now_str = now.isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if session exists, create if not
            cursor.execute(
                "SELECT session_id FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO sessions (session_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                    (session_id, None, now_str, now_str)
                )
            
            # Insert message
            cursor.execute(
                """INSERT INTO messages (id, session_id, role, content, timestamp, metadata) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (message_id, session_id, role, content, now_str, metadata_json)
            )
            
            # Update session timestamp and title
            if role == "user":
                cursor.execute(
                    "SELECT title FROM sessions WHERE session_id = ?",
                    (session_id,)
                )
                session_row = cursor.fetchone()
                if session_row and not session_row["title"]:
                    # Set title from first user message
                    title = content[:50] + ("..." if len(content) > 50 else "")
                    cursor.execute(
                        "UPDATE sessions SET title = ?, updated_at = ? WHERE session_id = ?",
                        (title, now_str, session_id)
                    )
                else:
                    cursor.execute(
                        "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                        (now_str, session_id)
                    )
            else:
                cursor.execute(
                    "UPDATE sessions SET updated_at = ? WHERE session_id = ?",
                    (now_str, session_id)
                )
            
            conn.commit()
        
        return ConversationMessage(
            id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            timestamp=now,
            metadata=metadata
        )
    
    async def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[ConversationMessage]:
        """Get messages from a session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if limit:
                cursor.execute(
                    """SELECT * FROM messages 
                       WHERE session_id = ? 
                       ORDER BY timestamp DESC 
                       LIMIT ?""",
                    (session_id, limit)
                )
                rows = cursor.fetchall()
                rows = list(reversed(rows))  # Reverse to get chronological order
            else:
                cursor.execute(
                    """SELECT * FROM messages 
                       WHERE session_id = ? 
                       ORDER BY timestamp ASC""",
                    (session_id,)
                )
                rows = cursor.fetchall()
            
            messages = []
            for row in rows:
                metadata = json.loads(row["metadata"]) if row["metadata"] else None
                messages.append(ConversationMessage(
                    id=row["id"],
                    session_id=row["session_id"],
                    role=row["role"],
                    content=row["content"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    metadata=metadata
                ))
            
            return messages
    
    async def get_all_sessions(self) -> List[ConversationSession]:
        """Get all conversation sessions."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions ORDER BY updated_at DESC"
            )
            rows = cursor.fetchall()
        
        sessions = []
        for row in rows:
            # Get message count (not full messages for performance)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) as count FROM messages WHERE session_id = ?",
                    (row["session_id"],)
                )
                count_row = cursor.fetchone()
                message_count = count_row["count"] if count_row else 0
            
            sessions.append(ConversationSession(
                session_id=row["session_id"],
                title=row["title"],
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                messages=[]  # Don't load all messages here
            ))
        
        return sessions
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a conversation session."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if exists
            cursor.execute(
                "SELECT session_id FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            if not cursor.fetchone():
                return False
            
            # Delete messages first
            cursor.execute(
                "DELETE FROM messages WHERE session_id = ?",
                (session_id,)
            )
            
            # Delete session
            cursor.execute(
                "DELETE FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            
            conn.commit()
            return True
    
    async def clear_all(self) -> None:
        """Delete all sessions and messages."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages")
            cursor.execute("DELETE FROM sessions")
            conn.commit()
