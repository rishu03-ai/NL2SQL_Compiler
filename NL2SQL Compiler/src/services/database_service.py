"""
SQLite Database Adapter Implementation

Concrete implementation of IDatabaseAdapter for SQLite.
Can be extended or replaced with MySQL, PostgreSQL, etc.
"""

import os
import re
import sqlite3
from typing import List, Optional
from contextlib import contextmanager

from ..interfaces.database_interface import IDatabaseAdapter, TableInfo, QueryResult


class SQLiteDatabaseAdapter(IDatabaseAdapter):
    """
    SQLite Database Adapter implementation.
    
    Provides read-only access to SQLite databases.
    Implements IDatabaseAdapter for pluggability.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize SQLite adapter.
        
        Args:
            db_path: Path to SQLite database file (defaults to DB_PATH env var)
        """
        self.db_path = db_path or os.getenv("DB_PATH", "./sample.db")
        self._connection: Optional[sqlite3.Connection] = None
        self._schema_cache: Optional[List[TableInfo]] = None
    
    @contextmanager
    def _get_cursor(self):
        """Context manager for database cursor."""
        if not self._connection:
            raise RuntimeError("Database not connected. Call connect() first.")
        cursor = self._connection.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    
    async def connect(self) -> bool:
        """Establish connection to SQLite database."""
        try:
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row
            
            # Load schema into cache
            await self.get_schema()
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            self._schema_cache = None
    
    async def execute_query(self, query: str) -> QueryResult:
        """Execute a SQL query and return results."""
        
        # Safety check: only allow read operations
        if not self.is_read_only_query(query):
            return QueryResult(
                success=False,
                error_message="Only SELECT queries are allowed. Write operations are blocked for safety.",
                query_executed=query
            )
        
        try:
            with self._get_cursor() as cursor:
                cursor.execute(query)
                
                # Get column names
                columns = [description[0] for description in cursor.description] if cursor.description else []
                
                # Fetch all rows
                rows = cursor.fetchall()
                
                # Convert Row objects to lists
                rows_as_lists = [list(row) for row in rows]
                
                return QueryResult(
                    success=True,
                    columns=columns,
                    rows=rows_as_lists,
                    row_count=len(rows_as_lists),
                    query_executed=query
                )
        
        except Exception as e:
            return QueryResult(
                success=False,
                error_message=str(e),
                query_executed=query
            )
    
    async def get_schema(self) -> List[TableInfo]:
        """Get the database schema (all tables and columns)."""
        
        if self._schema_cache:
            return self._schema_cache
        
        tables = []
        
        try:
            with self._get_cursor() as cursor:
                # Get all table names
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                table_names = [row[0] for row in cursor.fetchall()]
                
                for table_name in table_names:
                    # Get column info
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = []
                    for col in cursor.fetchall():
                        columns.append({
                            "name": col[1],
                            "type": col[2],
                            "nullable": not col[3],
                            "primary_key": bool(col[5])
                        })
                    
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    
                    tables.append(TableInfo(
                        name=table_name,
                        columns=columns,
                        row_count=row_count
                    ))
            
            self._schema_cache = tables
            return tables
        
        except Exception as e:
            print(f"Schema fetch error: {e}")
            return []
    
    async def get_table_info(self, table_name: str) -> Optional[TableInfo]:
        """Get information about a specific table."""
        schema = await self.get_schema()
        for table in schema:
            if table.name.lower() == table_name.lower():
                return table
        return None
    
    def get_schema_as_string(self) -> str:
        """Get schema as formatted string for LLM context."""
        if not self._schema_cache:
            return "Schema not loaded. Please connect to database first."
        
        lines = ["DATABASE SCHEMA:", "=" * 50]
        
        for table in self._schema_cache:
            lines.append(f"\nTable: {table.name} ({table.row_count} rows)")
            lines.append("-" * 40)
            
            for col in table.columns:
                pk_marker = " [PRIMARY KEY]" if col.get("primary_key") else ""
                null_marker = " (nullable)" if col.get("nullable") else " (not null)"
                lines.append(f"  - {col['name']}: {col['type']}{pk_marker}{null_marker}")
        
        return "\n".join(lines)
    
    def is_read_only_query(self, query: str) -> bool:
        """Check if query is read-only (SELECT only)."""
        # Normalize query
        normalized = query.strip().upper()
        
        # Remove comments
        normalized = re.sub(r'--.*$', '', normalized, flags=re.MULTILINE)
        normalized = re.sub(r'/\*.*?\*/', '', normalized, flags=re.DOTALL)
        normalized = normalized.strip()
        
        # Check for dangerous keywords
        dangerous_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'TRUNCATE', 'REPLACE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE'
        ]
        
        # Query must start with SELECT, WITH (for CTEs), or EXPLAIN
        safe_starts = ['SELECT', 'WITH', 'EXPLAIN', 'PRAGMA']
        
        if not any(normalized.startswith(start) for start in safe_starts):
            return False
        
        # Check for dangerous keywords anywhere (except in string literals)
        # This is a simplified check - production should be more robust
        for keyword in dangerous_keywords:
            if re.search(rf'\b{keyword}\b', normalized):
                return False
        
        return True
