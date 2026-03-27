# NL2SQL Compiler

> Ask questions in plain English, get answers from your database.

An AI-powered conversational agent that converts natural language queries into SQL, executes them, and explains the results — all through a clean chat interface.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green?logo=fastapi)
![LangChain](https://img.shields.io/badge/LangChain-Powered-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Features

| Feature | Description |
|---------|-------------|
| Natural Language Queries | Ask questions in plain English — no SQL knowledge required |
| Multi-LLM Support | Groq (Llama 3), OpenAI (GPT-4o), Google Gemini |
| Multi-Database Support | SQLite, PostgreSQL, MySQL |
| Upload Your Database | Upload `.db` files and instantly query your own data |
| Data Visualization | Interactive charts (bar, line, pie, doughnut) |
| CSV Export | Download query results as CSV files |
| Multi-Turn Conversations | Context-aware follow-up questions |
| Read-Only Safety | Only SELECT queries allowed — your data stays safe |
| SQL Explanation | Every generated query is explained in plain English |
| Persistent History | Chat sessions are saved across browser refreshes |

---

## Architecture

Built with SOLID principles and a pluggable, interface-driven architecture:

```
┌─────────────────────────────────────────────┐
│                  FastAPI Server              │
├─────────────────────────────────────────────┤
│               NL2SQL Agent                   │
│  (Orchestrates: LLM → SQL → Execute → Response)  │
├──────────┬──────────────┬───────────────────┤
│ ILLMService │ IDatabaseAdapter │ IMemoryStore  │
│  ├─ Groq    │  ├─ SQLite       │  ├─ SQLite   │
│  ├─ OpenAI  │  ├─ PostgreSQL   │  └─ InMemory │
│  └─ Gemini  │  └─ MySQL        │               │
└──────────┴──────────────┴───────────────────┘
```

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/rishu03-ai/NL2SQL_Compiler.git
cd NL2SQL-Compiler

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure

Create a `.env` file in the project root:

```env
# LLM Provider (choose one)
LLM_PROVIDER=groq            # groq | openai | gemini
GROQ_API_KEY=your_groq_key   # If using Groq
OPENAI_API_KEY=your_key      # If using OpenAI
GOOGLE_API_KEY=your_key      # If using Gemini

# Optional: Model override
LLM_MODEL=llama-3.3-70b-versatile

# Database (default: sqlite)
DB_TYPE=sqlite
DB_PATH=./sample.db

# For PostgreSQL:
# DB_TYPE=postgresql
# DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# For MySQL:
# DB_TYPE=mysql
# DB_HOST=localhost
# DB_PORT=3306
# DB_NAME=mydb
# DB_USER=root
# DB_PASSWORD=secret
```

### 3. Run

```bash
python main.py
```

Open **http://localhost:8000** in your browser.

---

## Project Structure

```
NL2SQL Compiler/
├── main.py                      # Entry point
├── sample.db                    # Default demo database
├── requirements.txt
├── .env                         # Configuration (not in git)
├── .gitignore
│
├── src/
│   ├── interfaces/              # Abstract interfaces (SOLID)
│   │   ├── llm_interface.py     # ILLMService
│   │   ├── database_interface.py # IDatabaseAdapter
│   │   ├── memory_interface.py  # IMemoryStore
│   │   └── agent_interface.py   # IAgent
│   │
│   ├── services/                # Concrete implementations
│   │   ├── llm_service.py       # Groq LLM
│   │   ├── openai_service.py    # OpenAI LLM
│   │   ├── gemini_service.py    # Gemini LLM
│   │   ├── database_service.py  # SQLite adapter
│   │   ├── postgresql_service.py # PostgreSQL adapter
│   │   ├── mysql_service.py     # MySQL adapter
│   │   ├── memory_service.py    # In-memory store
│   │   └── sqlite_memory_service.py # Persistent store
│   │
│   ├── agent/
│   │   └── nl2sql_agent.py      # Core AI agent
│   │
│   └── api/
│       └── server.py            # FastAPI endpoints
│
├── static/                      # Frontend
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
├── tests/
│   └── test_core.py             # Unit tests
│
└── uploads/                     # User-uploaded databases
```

---

## Running Tests

```bash
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serve chat UI |
| `POST` | `/api/chat` | Send a natural language query |
| `GET` | `/api/sessions` | List all chat sessions |
| `GET` | `/api/sessions/{id}` | Get session messages |
| `DELETE` | `/api/sessions/{id}` | Delete a session |
| `GET` | `/api/schema` | Get database schema |
| `POST` | `/api/export/csv` | Export query data as CSV |
| `POST` | `/api/upload-database` | Upload a SQLite database |
| `POST` | `/api/reset-database` | Reset to default database |
| `GET` | `/api/database-info` | Get active database info |
| `GET` | `/api/health` | Health check |

---

## Switching Providers

### LLM Providers

Change `LLM_PROVIDER` in your `.env` file:

```env
# Groq (fastest, free tier available)
LLM_PROVIDER=groq
GROQ_API_KEY=your_key

# OpenAI (GPT-4o)
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key

# Google Gemini
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_key
```

### Database Providers

Change `DB_TYPE` in your `.env` file:

```env
# SQLite (default, zero config)
DB_TYPE=sqlite
DB_PATH=./sample.db

# PostgreSQL
DB_TYPE=postgresql
DATABASE_URL=postgresql://user:pass@host:5432/db

# MySQL
DB_TYPE=mysql
DB_HOST=localhost
DB_NAME=mydb
DB_USER=root
DB_PASSWORD=secret
```

---

## Security

- **Read-only queries only** — INSERT, UPDATE, DELETE, DROP are all blocked
- **SQL injection prevention** — Queries are validated before execution
- **API keys stored in `.env`** — Never committed to version control
- **Uploaded databases validated** — Must be valid SQLite files with actual tables

---

## Tech Stack

- **Backend:** Python, FastAPI, LangChain
- **Frontend:** Vanilla HTML/CSS/JS, Chart.js
- **LLM:** Groq (Llama 3), OpenAI (GPT-4o), Google Gemini
- **Database:** SQLite (default), PostgreSQL, MySQL
- **Architecture:** SOLID principles, Dependency Injection, Factory Pattern

---

## License

MIT License — feel free to use, modify, and distribute.
