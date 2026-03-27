"""
NL2SQL Agent Implementation

The core conversational agent that handles natural language queries,
generates SQL, executes queries, and provides helpful responses.
"""

from typing import Optional, List
import json

from ..interfaces.agent_interface import IAgent, AgentResponse
from ..interfaces.llm_interface import ILLMService, ChatMessage
from ..interfaces.database_interface import IDatabaseAdapter
from ..interfaces.memory_interface import IMemoryStore


# Response generation prompt
RESPONSE_PROMPT = """You are a friendly data assistant helping non-technical users understand their data.

Your task is to take the query result and explain it in a helpful, conversational way.

RULES:
1. Be conversational and friendly
2. Summarize the data in plain English
3. If there's a table of data, you can mention key highlights
4. Suggest follow-up questions the user might want to ask
5. If the query failed, explain the error in simple terms and suggest how to rephrase
6. Keep responses concise but helpful

USER'S QUESTION: {question}

SQL QUERY EXECUTED: {sql}

QUERY RESULT:
{result}

Please provide a helpful response:"""


CLARIFICATION_PROMPT = """You are a data assistant. The user asked a question that is ambiguous or unclear.
You need to ask a clarifying question to understand what they want.

DATABASE SCHEMA:
{schema}

USER'S QUESTION: {question}

Based on the schema and the question, what clarifying question would you ask?
Be friendly and offer specific options when possible.

CLARIFYING QUESTION:"""


class NL2SQLAgent(IAgent):
    """
    NL2SQL Conversational Agent.
    
    Orchestrates the flow:
    1. Receive user message
    2. Check if clarification needed
    3. Generate SQL from natural language
    4. Execute query
    5. Generate friendly response
    
    Follows Dependency Inversion - depends on abstractions (interfaces),
    not concrete implementations.
    """
    
    def __init__(
        self,
        llm_service: ILLMService,
        database_adapter: IDatabaseAdapter,
        memory_store: IMemoryStore
    ):
        """
        Initialize the agent with its dependencies.
        
        Args:
            llm_service: LLM service for text generation
            database_adapter: Database adapter for query execution
            memory_store: Memory store for conversation history
        """
        self.llm = llm_service
        self.db = database_adapter
        self.memory = memory_store
    
    async def process_message(
        self,
        user_message: str,
        session_id: str
    ) -> AgentResponse:
        """Process a user message and return a response."""
        
        try:
            # Save user message to history
            await self.memory.add_message(
                session_id=session_id,
                role="user",
                content=user_message
            )
            
            # Get conversation history for context
            history = await self.memory.get_messages(session_id, limit=10)
            context_messages = [
                ChatMessage(role=msg.role, content=msg.content)
                for msg in history[:-1]  # Exclude the message we just added
            ]
            
            # Get database schema
            schema_str = self.db.get_schema_as_string()
            
            # Check if we need clarification (e.g., very vague query)
            if self._needs_clarification(user_message):
                clarification = await self._get_clarification(user_message, schema_str)
                
                # Save assistant response
                await self.memory.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=clarification
                )
                
                return AgentResponse(
                    message=clarification,
                    needs_clarification=True,
                    clarification_question=clarification
                )
            
            # Generate SQL from the question
            sql_query = await self.llm.generate_sql(
                natural_language_query=user_message,
                schema_info=schema_str,
                conversation_context=context_messages
            )
            
            # Execute the query
            query_result = await self.db.execute_query(sql_query)
            
            # Generate response based on result
            if query_result.success:
                response_text = await self._generate_response(
                    question=user_message,
                    sql=sql_query,
                    result=query_result
                )
                
                # Generate SQL explanation
                explanation = await self._explain_sql(sql_query)
                
                # Save assistant response with metadata
                await self.memory.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=response_text,
                    metadata={
                        "sql_query": sql_query,
                        "sql_explanation": explanation,
                        "row_count": query_result.row_count
                    }
                )
                
                return AgentResponse(
                    message=response_text,
                    sql_query=sql_query,
                    sql_explanation=explanation,
                    query_result={
                        "columns": query_result.columns,
                        "rows": query_result.rows,
                        "row_count": query_result.row_count
                    }
                )
            else:
                # Query failed - generate helpful error message
                error_response = await self._handle_query_error(
                    question=user_message,
                    sql=sql_query,
                    error=query_result.error_message
                )
                
                await self.memory.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=error_response,
                    metadata={"sql_query": sql_query, "error": query_result.error_message}
                )
                
                return AgentResponse(
                    message=error_response,
                    sql_query=sql_query,
                    error=query_result.error_message
                )
        
        except Exception as e:
            error_msg = f"I encountered an unexpected error: {str(e)}. Please try rephrasing your question."
            
            await self.memory.add_message(
                session_id=session_id,
                role="assistant",
                content=error_msg,
                metadata={"error": str(e)}
            )
            
            return AgentResponse(
                message=error_msg,
                error=str(e)
            )
    
    async def get_schema_summary(self) -> str:
        """Get a human-readable summary of the database schema."""
        schema = await self.db.get_schema()
        
        if not schema:
            return "No tables found in the database."
        
        lines = ["Here's what's in the database:\n"]
        
        for table in schema:
            column_names = [col["name"] for col in table.columns]
            lines.append(f"📊 **{table.name}** ({table.row_count} rows)")
            lines.append(f"   Columns: {', '.join(column_names)}\n")
        
        return "\n".join(lines)
    
    async def suggest_questions(self) -> list[str]:
        """Suggest questions based on the database schema."""
        schema = await self.db.get_schema()
        
        suggestions = []
        
        for table in schema:
            table_name = table.name.lower()
            
            # Generate contextual suggestions based on table names
            if "customer" in table_name or "user" in table_name:
                suggestions.append(f"How many customers do we have?")
                suggestions.append(f"Show me the top 10 customers")
            
            if "order" in table_name:
                suggestions.append(f"What's the total number of orders?")
                suggestions.append(f"Show me recent orders")
            
            if "product" in table_name:
                suggestions.append(f"Which products are most popular?")
                suggestions.append(f"List all products")
            
            if "employee" in table_name:
                suggestions.append(f"How many employees do we have?")
                suggestions.append(f"Show employees by department")
            
            if "transaction" in table_name or "payment" in table_name:
                suggestions.append(f"What's our total revenue?")
                suggestions.append(f"Show recent transactions")
        
        # Return unique suggestions, limited to 6
        unique_suggestions = list(dict.fromkeys(suggestions))
        return unique_suggestions[:6]
    
    def _needs_clarification(self, message: str) -> bool:
        """Check if the message is too vague and needs clarification."""
        # Very short messages might need clarification
        if len(message.split()) < 3:
            vague_words = ["show", "get", "find", "display", "what", "how", "report"]
            return message.lower().split()[0] in vague_words if message.split() else False
        return False
    
    async def _get_clarification(self, question: str, schema: str) -> str:
        """Generate a clarifying question."""
        prompt = CLARIFICATION_PROMPT.format(schema=schema, question=question)
        
        response = await self.llm.generate(
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=0.7
        )
        
        return response.content
    
    async def _generate_response(self, question: str, sql: str, result) -> str:
        """Generate a friendly response based on query results."""
        
        # Format result for LLM
        if result.row_count == 0:
            result_str = "No data found matching the query."
        elif result.row_count <= 10:
            # Show all data
            result_str = f"Columns: {', '.join(result.columns)}\n"
            result_str += f"Rows ({result.row_count}):\n"
            for row in result.rows:
                result_str += f"  {row}\n"
        else:
            # Show summary for large results
            result_str = f"Found {result.row_count} rows.\n"
            result_str += f"Columns: {', '.join(result.columns)}\n"
            result_str += f"First 5 rows:\n"
            for row in result.rows[:5]:
                result_str += f"  {row}\n"
            result_str += f"... and {result.row_count - 5} more rows"
        
        prompt = RESPONSE_PROMPT.format(
            question=question,
            sql=sql,
            result=result_str
        )
        
        response = await self.llm.generate(
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=0.7
        )
        
        return response.content
    
    async def _handle_query_error(self, question: str, sql: str, error: str) -> str:
        """Generate helpful error message."""
        prompt = f"""The user asked: "{question}"

I generated this SQL: {sql}

But it failed with error: {error}

Please explain what went wrong in simple terms and suggest how the user might rephrase their question.
Be friendly and helpful."""
        
        response = await self.llm.generate(
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=0.7
        )
        
        return response.content
    
    async def _explain_sql(self, sql: str) -> str:
        """Generate a plain English explanation of the SQL query."""
        prompt = f"""Explain this SQL query in one short, simple sentence that a non-technical person can understand. Do NOT use any technical jargon. Just describe what data it retrieves.

SQL: {sql}

Explanation:"""
        
        response = await self.llm.generate(
            messages=[ChatMessage(role="user", content=prompt)],
            temperature=0.3
        )
        
        return response.content.strip()
