"""
FastAPI Server for NL2SQL Compiler

REST API endpoints for the chat interface.
Sprint 2: Added persistent memory and CSV export.
"""

import os
import io
import csv
import shutil
import sqlite3
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our components
from ..services import (
    GroqLLMService, OpenAILLMService, GeminiLLMService,
    SQLiteDatabaseAdapter, PostgreSQLAdapter, MySQLAdapter,
    SqliteMemoryStore
)
from ..interfaces.llm_interface import ILLMService
from ..interfaces.database_interface import IDatabaseAdapter
from ..agent import NL2SQLAgent


def create_llm_service() -> ILLMService:
    """Factory function to create the appropriate LLM service based on config."""
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    
    if provider == "openai":
        return OpenAILLMService()
    elif provider == "gemini":
        return GeminiLLMService()
    elif provider == "groq":
        return GroqLLMService()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Supported: groq, openai, gemini")


def create_database_adapter() -> IDatabaseAdapter:
    """Factory function to create the appropriate database adapter based on config."""
    db_type = os.getenv("DB_TYPE", "sqlite").lower()
    
    if db_type == "sqlite":
        return SQLiteDatabaseAdapter()
    elif db_type == "postgresql" or db_type == "postgres":
        return PostgreSQLAdapter()
    elif db_type == "mysql":
        return MySQLAdapter()
    else:
        raise ValueError(f"Unknown DB type: {db_type}. Supported: sqlite, postgresql, mysql")


# Global instances (initialized on startup)
llm_service: Optional[ILLMService] = None
db_adapter: Optional[IDatabaseAdapter] = None
memory_store: Optional[SqliteMemoryStore] = None
agent: Optional[NL2SQLAgent] = None
default_db_path: Optional[str] = None

# Directory for uploaded databases
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    global llm_service, db_adapter, memory_store, agent, default_db_path
    
    print("🚀 Starting NL2SQL Compiler...")
    
    # Initialize services
    try:
        llm_service = create_llm_service()
        provider = os.getenv("LLM_PROVIDER", "groq").lower()
        print(f"✅ LLM Service initialized: {provider} / {llm_service.get_model_name()}")
        
        db_type = os.getenv("DB_TYPE", "sqlite").lower()
        db_adapter = create_database_adapter()
        connected = await db_adapter.connect()
        
        if db_type == "sqlite":
            default_db_path = db_adapter.db_path
        
        if connected:
            print(f"✅ Database connected: {db_type}")
        else:
            print("⚠️ Database connection failed")
        
        # Use persistent SQLite memory store
        memory_store = SqliteMemoryStore()
        print(f"✅ Persistent memory store initialized: {memory_store.db_path}")
        
        # Create the agent
        agent = NL2SQLAgent(
            llm_service=llm_service,
            database_adapter=db_adapter,
            memory_store=memory_store
        )
        print("✅ NL2SQL Agent ready!")
        
    except Exception as e:
        print(f"❌ Startup error: {e}")
        raise
    
    yield
    
    # Cleanup on shutdown
    print("👋 Shutting down...")
    if db_adapter:
        await db_adapter.disconnect()


def create_app() -> FastAPI:
    """Factory function to create the FastAPI app."""
    
    app = FastAPI(
        title="NL2SQL Compiler",
        description="An AI agent that converts natural language to SQL queries",
        version="0.2.0",  # Sprint 2
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Mount static files
    static_path = os.path.join(os.path.dirname(__file__), "..", "..", "static")
    if os.path.exists(static_path):
        app.mount("/static", StaticFiles(directory=static_path), name="static")
    
    return app


# Create the app
app = create_app()


# ==========================================
# Request/Response Models
# ==========================================

class ChatRequest(BaseModel):
    """Chat message request."""
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response."""
    message: str
    session_id: str
    sql_query: Optional[str] = None
    sql_explanation: Optional[str] = None
    data: Optional[dict] = None
    needs_clarification: bool = False
    error: Optional[str] = None


class SessionInfo(BaseModel):
    """Session information."""
    session_id: str
    title: Optional[str] = None
    message_count: int
    created_at: str
    updated_at: str


class ExportRequest(BaseModel):
    """Request for exporting data."""
    columns: List[str]
    rows: List[List]
    filename: Optional[str] = "export"


# ==========================================
# API Endpoints
# ==========================================

@app.get("/")
async def root():
    """Serve the main chat UI."""
    static_path = os.path.join(os.path.dirname(__file__), "..", "..", "static", "index.html")
    return FileResponse(static_path)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat message and return the agent's response."""
    
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    # Create new session if not provided
    session_id = request.session_id
    if not session_id:
        session = await memory_store.create_session()
        session_id = session.session_id
    
    # Process the message
    response = await agent.process_message(
        user_message=request.message,
        session_id=session_id
    )
    
    return ChatResponse(
        message=response.message,
        session_id=session_id,
        sql_query=response.sql_query,
        sql_explanation=response.sql_explanation,
        data=response.query_result,
        needs_clarification=response.needs_clarification,
        error=response.error
    )


@app.get("/api/sessions")
async def get_sessions():
    """Get all conversation sessions."""
    
    if not memory_store:
        raise HTTPException(status_code=500, detail="Memory store not initialized")
    
    sessions = await memory_store.get_all_sessions()
    
    # Get message counts for each session
    result = []
    for s in sessions:
        messages = await memory_store.get_messages(s.session_id)
        result.append(SessionInfo(
            session_id=s.session_id,
            title=s.title,
            message_count=len(messages),
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat()
        ))
    
    return result


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Get a specific session with all messages."""
    
    if not memory_store:
        raise HTTPException(status_code=500, detail="Memory store not initialized")
    
    session = await memory_store.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session.session_id,
        "title": session.title,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
                "metadata": m.metadata
            }
            for m in session.messages
        ]
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a conversation session."""
    
    if not memory_store:
        raise HTTPException(status_code=500, detail="Memory store not initialized")
    
    deleted = await memory_store.delete_session(session_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"success": True}


@app.get("/api/schema")
async def get_schema():
    """Get the database schema summary."""
    
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    schema = await agent.get_schema_summary()
    suggestions = await agent.suggest_questions()
    
    return {
        "schema": schema,
        "suggested_questions": suggestions
    }


@app.post("/api/export/csv")
async def export_csv(request: ExportRequest):
    """Export data as CSV file."""
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(request.columns)
    
    # Write data rows
    for row in request.rows:
        writer.writerow(row)
    
    # Prepare response
    output.seek(0)
    
    filename = f"{request.filename}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@app.get("/api/query")
async def direct_query(q: str = Query(..., description="Natural language query")):
    """Direct query endpoint for quick queries without session."""
    
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    # Create a temporary session
    session = await memory_store.create_session()
    
    # Process the query
    response = await agent.process_message(
        user_message=q,
        session_id=session.session_id
    )
    
    return {
        "query": q,
        "message": response.message,
        "sql_query": response.sql_query,
        "data": response.query_result,
        "error": response.error
    }


@app.post("/api/upload-database")
async def upload_database(file: UploadFile = File(...)):
    """Upload a SQLite database file to query."""
    global db_adapter, agent
    
    if not file.filename.endswith('.db'):
        raise HTTPException(
            status_code=400,
            detail="Only .db (SQLite) files are supported."
        )
    
    # Save uploaded file
    upload_path = os.path.join(UPLOADS_DIR, file.filename)
    try:
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    
    # Validate it's a real SQLite database
    try:
        conn = sqlite3.connect(upload_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        
        if len(tables) == 0:
            os.remove(upload_path)
            raise HTTPException(
                status_code=400,
                detail="The uploaded database has no tables."
            )
    except sqlite3.DatabaseError:
        os.remove(upload_path)
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid SQLite database."
        )
    
    # Disconnect old database and connect to new one
    try:
        if db_adapter:
            await db_adapter.disconnect()
        
        db_adapter = SQLiteDatabaseAdapter(db_path=upload_path)
        connected = await db_adapter.connect()
        
        if not connected:
            raise HTTPException(status_code=500, detail="Failed to connect to uploaded database.")
        
        # Recreate agent with new database
        agent = NL2SQLAgent(
            llm_service=llm_service,
            database_adapter=db_adapter,
            memory_store=memory_store
        )
        
        # Get schema info for response
        schema = await agent.get_schema_summary()
        suggestions = await agent.suggest_questions()
        
        return {
            "success": True,
            "filename": file.filename,
            "message": f"Database '{file.filename}' loaded successfully!",
            "schema": schema,
            "suggested_questions": suggestions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load database: {e}")


@app.post("/api/reset-database")
async def reset_database():
    """Reset to the default sample database."""
    global db_adapter, agent
    
    try:
        if db_adapter:
            await db_adapter.disconnect()
        
        db_adapter = SQLiteDatabaseAdapter(db_path=default_db_path)
        connected = await db_adapter.connect()
        
        if not connected:
            raise HTTPException(status_code=500, detail="Failed to reconnect to default database.")
        
        # Recreate agent
        agent = NL2SQLAgent(
            llm_service=llm_service,
            database_adapter=db_adapter,
            memory_store=memory_store
        )
        
        schema = await agent.get_schema_summary()
        suggestions = await agent.suggest_questions()
        
        return {
            "success": True,
            "message": "Reset to default database.",
            "schema": schema,
            "suggested_questions": suggestions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset database: {e}")


@app.get("/api/database-info")
async def get_database_info():
    """Get info about the currently active database."""
    if not db_adapter:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    is_default = os.path.abspath(db_adapter.db_path) == os.path.abspath(default_db_path)
    filename = os.path.basename(db_adapter.db_path)
    
    schema = await db_adapter.get_schema()
    table_count = len(schema)
    total_rows = sum(t.row_count for t in schema)
    
    return {
        "filename": filename,
        "is_default": is_default,
        "table_count": table_count,
        "total_rows": total_rows,
        "tables": [t.name for t in schema]
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.3.0",
        "llm": llm_service.get_model_name() if llm_service else "not initialized",
        "database": db_adapter.db_path if db_adapter else "not connected",
        "memory": "persistent (SQLite)"
    }
