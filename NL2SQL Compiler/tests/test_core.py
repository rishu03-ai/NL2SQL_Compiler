"""
Unit Tests for NL2SQL Compiler

Tests core components: database adapter, safety checks, agent interface.
Run with: python -m pytest tests/ -v
"""

import pytest
import os
import sys
import sqlite3
import tempfile

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.interfaces.database_interface import TableInfo, QueryResult
from src.interfaces.llm_interface import ChatMessage, LLMResponse
from src.interfaces.agent_interface import AgentResponse
from src.services.database_service import SQLiteDatabaseAdapter


# ==========================================
# Test Fixtures
# ==========================================

@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    
    # Create test tables
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            age INTEGER
        )
    """)
    
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            amount REAL,
            status TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Insert test data
    cursor.executemany(
        "INSERT INTO users (name, email, age) VALUES (?, ?, ?)",
        [
            ("Alice", "alice@test.com", 30),
            ("Bob", "bob@test.com", 25),
            ("Charlie", "charlie@test.com", 35),
        ]
    )
    
    cursor.executemany(
        "INSERT INTO orders (user_id, amount, status) VALUES (?, ?, ?)",
        [
            (1, 99.99, "completed"),
            (1, 149.50, "completed"),
            (2, 75.00, "pending"),
            (3, 200.00, "completed"),
        ]
    )
    
    conn.commit()
    conn.close()
    
    yield path
    
    # Cleanup
    os.unlink(path)


@pytest.fixture
def db_adapter(temp_db):
    """Create a database adapter connected to the temp DB."""
    adapter = SQLiteDatabaseAdapter(db_path=temp_db)
    return adapter


# ==========================================
# Model Tests
# ==========================================

class TestModels:
    """Test Pydantic models."""
    
    def test_chat_message(self):
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
    
    def test_llm_response(self):
        resp = LLMResponse(content="SELECT * FROM users", model="test-model")
        assert resp.content == "SELECT * FROM users"
        assert resp.tokens_used is None
    
    def test_agent_response(self):
        resp = AgentResponse(
            message="Found 3 users",
            sql_query="SELECT * FROM users",
            sql_explanation="Gets all users from the database"
        )
        assert resp.message == "Found 3 users"
        assert resp.sql_explanation is not None
        assert resp.needs_clarification is False
        assert resp.error is None
    
    def test_query_result(self):
        result = QueryResult(
            success=True,
            columns=["id", "name"],
            rows=[[1, "Alice"], [2, "Bob"]],
            row_count=2,
            query_executed="SELECT id, name FROM users"
        )
        assert result.success is True
        assert result.row_count == 2
    
    def test_table_info(self):
        info = TableInfo(
            name="users",
            columns=[{"name": "id", "type": "INTEGER"}],
            row_count=10
        )
        assert info.name == "users"
        assert info.row_count == 10


# ==========================================
# Database Adapter Tests
# ==========================================

class TestSQLiteDatabaseAdapter:
    """Test SQLite database adapter."""
    
    @pytest.mark.asyncio
    async def test_connect(self, db_adapter):
        result = await db_adapter.connect()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_connect_invalid_path(self):
        adapter = SQLiteDatabaseAdapter(db_path="/nonexistent/path/db.sqlite")
        result = await adapter.connect()
        # SQLite creates the file, so it actually connects
        # but there would be no tables
        assert result is True
    
    @pytest.mark.asyncio
    async def test_get_schema(self, db_adapter):
        await db_adapter.connect()
        schema = await db_adapter.get_schema()
        
        assert len(schema) == 2
        table_names = [t.name for t in schema]
        assert "users" in table_names
        assert "orders" in table_names
    
    @pytest.mark.asyncio
    async def test_get_schema_columns(self, db_adapter):
        await db_adapter.connect()
        schema = await db_adapter.get_schema()
        
        users_table = next(t for t in schema if t.name == "users")
        col_names = [c["name"] for c in users_table.columns]
        assert "id" in col_names
        assert "name" in col_names
        assert "email" in col_names
        assert "age" in col_names
    
    @pytest.mark.asyncio
    async def test_get_schema_row_count(self, db_adapter):
        await db_adapter.connect()
        schema = await db_adapter.get_schema()
        
        users_table = next(t for t in schema if t.name == "users")
        assert users_table.row_count == 3
        
        orders_table = next(t for t in schema if t.name == "orders")
        assert orders_table.row_count == 4
    
    @pytest.mark.asyncio
    async def test_execute_select(self, db_adapter):
        await db_adapter.connect()
        result = await db_adapter.execute_query("SELECT * FROM users")
        
        assert result.success is True
        assert result.row_count == 3
        assert "name" in result.columns
    
    @pytest.mark.asyncio
    async def test_execute_select_with_where(self, db_adapter):
        await db_adapter.connect()
        result = await db_adapter.execute_query("SELECT name FROM users WHERE age > 28")
        
        assert result.success is True
        assert result.row_count == 2
    
    @pytest.mark.asyncio
    async def test_execute_count(self, db_adapter):
        await db_adapter.connect()
        result = await db_adapter.execute_query("SELECT COUNT(*) as total FROM orders")
        
        assert result.success is True
        assert result.rows[0][0] == 4
    
    @pytest.mark.asyncio
    async def test_execute_join(self, db_adapter):
        await db_adapter.connect()
        result = await db_adapter.execute_query("""
            SELECT u.name, SUM(o.amount) as total
            FROM users u
            JOIN orders o ON u.id = o.user_id
            GROUP BY u.name
        """)
        
        assert result.success is True
        assert result.row_count == 3
    
    @pytest.mark.asyncio
    async def test_execute_invalid_query(self, db_adapter):
        await db_adapter.connect()
        result = await db_adapter.execute_query("SELECT * FROM nonexistent_table")
        
        assert result.success is False
        assert result.error_message is not None
    
    @pytest.mark.asyncio
    async def test_get_table_info(self, db_adapter):
        await db_adapter.connect()
        info = await db_adapter.get_table_info("users")
        
        assert info is not None
        assert info.name == "users"
        assert info.row_count == 3
    
    @pytest.mark.asyncio
    async def test_get_table_info_not_found(self, db_adapter):
        await db_adapter.connect()
        info = await db_adapter.get_table_info("nonexistent")
        
        assert info is None
    
    @pytest.mark.asyncio
    async def test_get_schema_as_string(self, db_adapter):
        await db_adapter.connect()
        schema_str = db_adapter.get_schema_as_string()
        
        assert "users" in schema_str
        assert "orders" in schema_str
        assert "id" in schema_str
    
    @pytest.mark.asyncio
    async def test_disconnect(self, db_adapter):
        await db_adapter.connect()
        await db_adapter.disconnect()
        
        # Schema cache should be cleared
        assert db_adapter._schema_cache is None


# ==========================================
# Safety / Read-Only Tests
# ==========================================

class TestReadOnlySafety:
    """Test that write operations are blocked."""
    
    @pytest.fixture
    def adapter(self, db_adapter):
        return db_adapter
    
    def test_select_allowed(self, adapter):
        assert adapter.is_read_only_query("SELECT * FROM users") is True
    
    def test_select_with_join(self, adapter):
        assert adapter.is_read_only_query("SELECT u.name FROM users u JOIN orders o ON u.id = o.user_id") is True
    
    def test_with_cte_allowed(self, adapter):
        assert adapter.is_read_only_query("WITH cte AS (SELECT * FROM users) SELECT * FROM cte") is True
    
    def test_explain_allowed(self, adapter):
        assert adapter.is_read_only_query("EXPLAIN SELECT * FROM users") is True
    
    def test_insert_blocked(self, adapter):
        assert adapter.is_read_only_query("INSERT INTO users (name) VALUES ('Eve')") is False
    
    def test_update_blocked(self, adapter):
        assert adapter.is_read_only_query("UPDATE users SET name='Eve' WHERE id=1") is False
    
    def test_delete_blocked(self, adapter):
        assert adapter.is_read_only_query("DELETE FROM users WHERE id=1") is False
    
    def test_drop_blocked(self, adapter):
        assert adapter.is_read_only_query("DROP TABLE users") is False
    
    def test_create_blocked(self, adapter):
        assert adapter.is_read_only_query("CREATE TABLE hack (id INT)") is False
    
    def test_alter_blocked(self, adapter):
        assert adapter.is_read_only_query("ALTER TABLE users ADD COLUMN hack TEXT") is False
    
    def test_truncate_blocked(self, adapter):
        assert adapter.is_read_only_query("TRUNCATE TABLE users") is False
    
    @pytest.mark.asyncio
    async def test_write_query_returns_error(self, adapter):
        await adapter.connect()
        result = await adapter.execute_query("INSERT INTO users (name) VALUES ('Hacker')")
        
        assert result.success is False
        assert "read-only" in result.error_message.lower() or "SELECT" in result.error_message
    
    @pytest.mark.asyncio
    async def test_data_unchanged_after_blocked_write(self, adapter):
        await adapter.connect()
        
        # Try to insert (should be blocked)
        await adapter.execute_query("INSERT INTO users (name) VALUES ('Hacker')")
        
        # Verify no data was changed
        result = await adapter.execute_query("SELECT COUNT(*) FROM users")
        assert result.rows[0][0] == 3  # Still 3 original rows


# ==========================================
# Factory / Config Tests
# ==========================================

class TestConfig:
    """Test configuration and factory logic."""
    
    def test_sqlite_adapter_default_path(self):
        adapter = SQLiteDatabaseAdapter()
        assert adapter.db_path is not None
    
    def test_sqlite_adapter_custom_path(self):
        adapter = SQLiteDatabaseAdapter(db_path="/tmp/test.db")
        assert adapter.db_path == "/tmp/test.db"
    
    def test_agent_response_optional_fields(self):
        resp = AgentResponse(message="Hello")
        assert resp.sql_query is None
        assert resp.sql_explanation is None
        assert resp.query_result is None
        assert resp.error is None
