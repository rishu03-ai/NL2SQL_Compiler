"""
PostgreSQL Database Adapter Implementation

Concrete implementation of IDatabaseAdapter for PostgreSQL.
Uses asyncpg for async PostgreSQL connections.
"""

import os
import re
from typing import List, Optional

from ..interfaces.database_interface import IDatabaseAdapter, TableInfo, QueryResult


class PostgreSQLAdapter(IDatabaseAdapter):
    """
    PostgreSQL Database Adapter implementation.
    
    Provides read-only access to PostgreSQL databases.
    Implements IDatabaseAdapter for pluggability.
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        connection_string: Optional[str] = None
    ):
        """
        Initialize PostgreSQL adapter.
        
        Can be configured via individual params or a connection string.
        Falls back to environment variables.
        """
        self.host = host or os.getenv("DB_HOST", "localhost")
        self.port = port or int(os.getenv("DB_PORT", "5432"))
        self.database = database or os.getenv("DB_NAME", "postgres")
        self.user = user or os.getenv("DB_USER", "postgres")
        self.password = password or os.getenv("DB_PASSWORD", "")
        self.connection_string = connection_string or os.getenv("DATABASE_URL")
        
        self._pool = None
        self._schema_cache: Optional[List[TableInfo]] = None
    
    async def connect(self) -> bool:
        """Establish connection to PostgreSQL database."""
        try:
            import asyncpg
            
            if self.connection_string:
                self._pool = await asyncpg.create_pool(self.connection_string, min_size=1, max_size=5)
            else:
                self._pool = await asyncpg.create_pool(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    min_size=1,
                    max_size=5
                )
            
            # Load schema into cache
            await self.get_schema()
            return True
        except ImportError:
            print("❌ asyncpg not installed. Run: pip install asyncpg")
            return False
        except Exception as e:
            print(f"PostgreSQL connection error: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Close the database connection pool."""
        if self._pool:
            await self._pool.close()
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
                # Use a read-only transaction for extra safety
                async with conn.transaction(readonly=True):
                    rows = await conn.fetch(query)
                    
                    if not rows:
                        return QueryResult(
                            success=True,
                            columns=[],
                            rows=[],
                            row_count=0,
                            query_executed=query
                        )
                    
                    columns = list(rows[0].keys())
                    rows_as_lists = [list(row.values()) for row in rows]
                    
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
                # Get all user tables
                table_rows = await conn.fetch("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """)
                
                for table_row in table_rows:
                    table_name = table_row['table_name']
                    
                    # Get column info
                    col_rows = await conn.fetch("""
                        SELECT 
                            c.column_name,
                            c.data_type,
                            c.is_nullable,
                            CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key
                        FROM information_schema.columns c
                        LEFT JOIN (
                            SELECT kcu.column_name
                            FROM information_schema.table_constraints tc
                            JOIN information_schema.key_column_usage kcu 
                                ON tc.constraint_name = kcu.constraint_name
                            WHERE tc.table_name = $1 
                            AND tc.constraint_type = 'PRIMARY KEY'
                        ) pk ON c.column_name = pk.column_name
                        WHERE c.table_name = $1 AND c.table_schema = 'public'
                        ORDER BY c.ordinal_position
                    """, table_name)
                    
                    columns = []
                    for col in col_rows:
                        columns.append({
                            "name": col['column_name'],
                            "type": col['data_type'].upper(),
                            "nullable": col['is_nullable'] == 'YES',
                            "primary_key": col['is_primary_key']
                        })
                    
                    # Get row count
                    count_row = await conn.fetchrow(
                        f'SELECT COUNT(*) as cnt FROM "{table_name}"'
                    )
                    row_count = count_row['cnt'] if count_row else 0
                    
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
        
        lines = ["DATABASE SCHEMA (PostgreSQL):", "=" * 50]
        
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
            'COPY', 'VACUUM', 'CLUSTER', 'REINDEX'
        ]
        
        safe_starts = ['SELECT', 'WITH', 'EXPLAIN']
        
        if not any(normalized.startswith(start) for start in safe_starts):
            return False
        
        for keyword in dangerous_keywords:
            if re.search(rf'\b{keyword}\b', normalized):
                return False
        
        return True
