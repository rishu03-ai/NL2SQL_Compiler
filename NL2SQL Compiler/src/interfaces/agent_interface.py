"""
Agent Interface (Dependency Inversion Principle)

This abstract interface defines the contract for the AI agent.
Allows different agent implementations (LangChain, custom, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel


class AgentResponse(BaseModel):
    """Response from the agent."""
    message: str  # The natural language response to show user
    sql_query: Optional[str] = None  # The SQL that was generated (if any)
    sql_explanation: Optional[str] = None  # Plain English explanation of the SQL
    query_result: Optional[Dict[str, Any]] = None  # The data retrieved
    needs_clarification: bool = False  # Whether agent needs more info
    clarification_question: Optional[str] = None  # What to ask user
    error: Optional[str] = None  # Error message if something went wrong
    metadata: Optional[Dict[str, Any]] = None  # Additional info


class IAgent(ABC):
    """
    Abstract interface for the NL2SQL Agent.
    
    The agent is responsible for:
    1. Understanding user's natural language query
    2. Deciding what tools/actions to use
    3. Generating and executing SQL
    4. Formulating a helpful response
    
    This follows the Dependency Inversion Principle.
    """
    
    @abstractmethod
    async def process_message(
        self,
        user_message: str,
        session_id: str
    ) -> AgentResponse:
        """
        Process a user message and return a response.
        
        This is the main entry point for the agent. It will:
        1. Look at conversation history for context
        2. Understand what the user is asking
        3. Generate SQL if needed
        4. Execute the query
        5. Format a helpful response
        
        Args:
            user_message: The user's natural language input
            session_id: The conversation session ID for context
            
        Returns:
            AgentResponse with the result
        """
        pass
    
    @abstractmethod
    async def get_schema_summary(self) -> str:
        """
        Get a human-readable summary of the database schema.
        
        Returns:
            Description of available tables and their purpose
        """
        pass
    
    @abstractmethod
    async def suggest_questions(self) -> list[str]:
        """
        Suggest questions the user might want to ask.
        
        Returns:
            List of example questions based on the schema
        """
        pass
