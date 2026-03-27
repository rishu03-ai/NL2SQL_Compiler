"""
Database Adapter Interface (Dependency Inversion Principle)

This abstract interface allows us to connect to any database (SQLite, MySQL, PostgreSQL)
without changing the agent's core logic.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class TableInfo(BaseModel):
    """Information about a database table."""
    name: str
    columns: List[Dict[str, Any]]  # [{"name": "id", "type": "INTEGER", ...}, ...]
    row_count: Optional[int] = None


class QueryResult(BaseModel):
    """Result of executing a SQL query."""
    success: bool
    columns: List[str] = []
    rows: List[List[Any]] = []
    row_count: int = 0
    error_message: Optional[str] = None
    query_executed: str = ""


class IDatabaseAdapter(ABC):
    """
    Abstract interface for database adapters.
    
    Any database (SQLite, MySQL, PostgreSQL, etc.) must implement this interface.
    This follows the Dependency Inversion Principle.
    """
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the database.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close the database connection."""
        pass
    
    @abstractmethod
    async def execute_query(self, query: str) -> QueryResult:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query string to execute
            
        Returns:
            QueryResult with data or error information
        """
        pass
    
    @abstractmethod
    async def get_schema(self) -> List[TableInfo]:
        """
        Get the database schema (all tables and their columns).
        
        Returns:
            List of TableInfo objects describing all tables
        """
        pass
    
    @abstractmethod
    async def get_table_info(self, table_name: str) -> Optional[TableInfo]:
        """
        Get detailed information about a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            TableInfo object or None if table doesn't exist
        """
        pass
    
    @abstractmethod
    def get_schema_as_string(self) -> str:
        """
        Get the database schema as a formatted string for LLM context.
        
        Returns:
            Human-readable schema description
        """
        pass
    
    @abstractmethod
    def is_read_only_query(self, query: str) -> bool:
        """
        Check if a query is read-only (SELECT only).
        
        Args:
            query: SQL query to check
            
        Returns:
            True if query is read-only, False otherwise
        """
        pass
