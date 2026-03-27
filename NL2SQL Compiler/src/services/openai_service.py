"""
OpenAI LLM Service Implementation

Concrete implementation of ILLMService for OpenAI API.
Supports GPT-4o, GPT-4, GPT-3.5-turbo, etc.
"""

import os
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from ..interfaces.llm_interface import ILLMService, ChatMessage, LLMResponse


# SQL Generation prompt template (same as Groq for consistency)
SQL_GENERATION_PROMPT = """You are an expert SQL query generator. Your task is to convert natural language questions into accurate SQL queries.

DATABASE SCHEMA:
{schema}

IMPORTANT RULES:
1. Generate ONLY SELECT queries (read-only operations)
2. Never generate INSERT, UPDATE, DELETE, DROP, or any write operations
3. Return ONLY the SQL query, no explanations
4. Use proper SQL syntax for the given database
5. If the question is ambiguous, make reasonable assumptions
6. Use appropriate JOINs when data spans multiple tables
7. Use aliases for clarity when needed

CONVERSATION CONTEXT (for reference):
{context}

USER QUESTION: {question}

SQL QUERY:"""


class OpenAILLMService(ILLMService):
    """
    OpenAI LLM Service implementation.
    
    Uses LangChain's ChatOpenAI for API communication.
    Implements the ILLMService interface for pluggability.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize OpenAI LLM Service.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name (defaults to LLM_MODEL env var or gpt-4o-mini)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o-mini")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required")
        
        self.client = ChatOpenAI(
            api_key=self.api_key,
            model=self.model
        )
    
    async def generate(
        self,
        messages: List[ChatMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Generate a response from OpenAI LLM."""
        
        langchain_messages = []
        
        if system_prompt:
            langchain_messages.append(SystemMessage(content=system_prompt))
        
        for msg in messages:
            if msg.role == "user":
                langchain_messages.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                langchain_messages.append(AIMessage(content=msg.content))
            elif msg.role == "system":
                langchain_messages.append(SystemMessage(content=msg.content))
        
        response = await self.client.ainvoke(langchain_messages)
        
        return LLMResponse(
            content=response.content,
            model=self.model,
            tokens_used=response.response_metadata.get("token_usage", {}).get("total_tokens"),
            raw_response={"response_metadata": response.response_metadata}
        )
    
    async def generate_sql(
        self,
        natural_language_query: str,
        schema_info: str,
        conversation_context: Optional[List[ChatMessage]] = None
    ) -> str:
        """Generate SQL from natural language query."""
        
        context_str = ""
        if conversation_context:
            context_lines = []
            for msg in conversation_context[-6:]:
                context_lines.append(f"{msg.role.upper()}: {msg.content}")
            context_str = "\n".join(context_lines)
        else:
            context_str = "No previous context"
        
        prompt = SQL_GENERATION_PROMPT.format(
            schema=schema_info,
            context=context_str,
            question=natural_language_query
        )
        
        response = await self.generate(
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=0.1
        )
        
        sql = response.content.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        
        return sql.strip()
    
    def get_model_name(self) -> str:
        """Return the current model name."""
        return self.model
