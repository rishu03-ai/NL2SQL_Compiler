"""
MySQL Database Adapter Implementation

Concrete implementation of IDatabaseAdapter for MySQL.
Uses aiomysql for async MySQL connections.
"""

import os
import re
from typing import List, Optional

from ..interfaces.database_interface import IDatabaseAdapter, TableInfo, QueryResult


class MySQLAdapter(IDatabaseAdapter):
    """
    MySQL Database Adapter implementation.
    
    Provides read-only access to MySQL databases.
    Implements IDatabaseAdapter for pluggability.
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize MySQL adapter.
        
        Falls back to environment variables if params not provided.
        """
        self.host = host or os.getenv("DB_HOST", "localhost")
        self.port = port or int(os.getenv("DB_PORT", "3306"))
        self.database = database or os.getenv("DB_NAME", "mysql")
        self.user = user or os.getenv("DB_USER", "root")
        self.password = password or os.getenv("DB_PASSWORD", "")
        
        self._pool = None
        self._schema_cache: Optional[List[TableInfo]] = None
    
    async def connect(self) -> bool:
        """Establish connection to MySQL database."""
        try:
            import aiomysql
            
            self._pool = await aiomysql.create_pool(
                host=self.host,
                port=self.port,
                db=self.database,
                user=self.user,
                password=self.password,
                minsize=1,
                maxsize=5,
                autocommit=True
            )
            
            # Load schema into cache
            await self.get_schema()
            return True
        except ImportError:
            print("❌ aiomysql not installed. Run: pip install aiomysql")
            return False
        except Exception as e:
            print(f"MySQL connection error: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close the database connection pool."""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            self._schema_cache = None
    
    async def execute_query(self, query: str) -> QueryResult:
        """Execute a SQL query and return results."""
        
        if not self.is_read_only_query(query):
            return QueryResult(
                success=False,
                error_message="Only SELECT queries are allowed. Write operations are blocked for safety.",
                query_executed=query
            )
        
        try:
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(query)
                    
                    if cursor.description is None:
                        return QueryResult(
                            success=True,
                            columns=[],
                            rows=[],
                            row_count=0,
                            query_executed=query
                        )
                    
                    columns = [desc[0] for desc in cursor.description]
                    rows = await cursor.fetchall()
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
            async with self._pool.acquire() as conn:
                async with conn.cursor() as cursor:
                    # Get all tables
                    await cursor.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = %s 
                        AND table_type = 'BASE TABLE'
                        ORDER BY table_name
                    """, (self.database,))
                    table_rows = await cursor.fetchall()
                    
                    for (table_name,) in table_rows:
                        # Get column info
                        await cursor.execute("""
                            SELECT 
                                column_name,
                                data_type,
                                is_nullable,
                                column_key
                            FROM information_schema.columns
                            WHERE table_schema = %s AND table_name = %s
                            ORDER BY ordinal_position
                        """, (self.database, table_name))
                        col_rows = await cursor.fetchall()
                        
                        columns = []
                        for col in col_rows:
                            columns.append({
                                "name": col[0],
                                "type": col[1].upper(),
                                "nullable": col[2] == 'YES',
                                "primary_key": col[3] == 'PRI'
                            })
                        
                        # Get row count
                        await cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                        count_row = await cursor.fetchone()
                        row_count = count_row[0] if count_row else 0
                        
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
        
        lines = ["DATABASE SCHEMA (MySQL):", "=" * 50]
        
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
        normalized = query.strip().upper()
        
        normalized = re.sub(r'--.*$', '', normalized, flags=re.MULTILINE)
        normalized = re.sub(r'/\*.*?\*/', '', normalized, flags=re.DOTALL)
        normalized = normalized.strip()
        
        dangerous_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'TRUNCATE', 'REPLACE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE',
            'LOAD', 'CALL'
        ]
        
        safe_starts = ['SELECT', 'WITH', 'EXPLAIN', 'SHOW', 'DESCRIBE']
        
        if not any(normalized.startswith(start) for start in safe_starts):
            return False
        
        for keyword in dangerous_keywords:
            if re.search(rf'\b{keyword}\b', normalized):
                return False
        
        return True
