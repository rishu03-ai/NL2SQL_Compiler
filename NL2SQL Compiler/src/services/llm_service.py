"""
Groq LLM Service Implementation

Concrete implementation of ILLMService for Groq API.
Can be easily swapped with OpenAI, Gemini, or other providers.
"""

import os
from typing import List, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from ..interfaces.llm_interface import ILLMService, ChatMessage, LLMResponse


# SQL Generation prompt template
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


class GroqLLMService(ILLMService):
    """
    Groq LLM Service implementation.
    
    Uses LangChain's ChatGroq for API communication.
    Implements the ILLMService interface for pluggability.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Groq LLM Service.
        
        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
            model: Model name (defaults to LLM_MODEL env var or llama-3.3-70b-versatile)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model or os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY is required")
        
        self.client = ChatGroq(
            api_key=self.api_key,
            model_name=self.model
        )
    
    async def generate(
        self,
        messages: List[ChatMessage],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> LLMResponse:
        """Generate a response from Groq LLM."""
        
        # Convert messages to LangChain format
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
        
        # Generate response
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
        
        # Format conversation context
        context_str = ""
        if conversation_context:
            context_lines = []
            for msg in conversation_context[-6:]:  # Last 6 messages for context
                context_lines.append(f"{msg.role.upper()}: {msg.content}")
            context_str = "\n".join(context_lines)
        else:
            context_str = "No previous context"
        
        # Build the prompt
        prompt = SQL_GENERATION_PROMPT.format(
            schema=schema_info,
            context=context_str,
            question=natural_language_query
        )
        
        # Generate SQL
        response = await self.generate(
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=0.1  # Low temperature for precise SQL
        )
        
        # Clean up the response (remove markdown code blocks if present)
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
