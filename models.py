# 💡 Intuition:

# Database models = How data looks in PostgreSQL
# Agent models = How LLM structures its output (replaces regex!)
# API models = What users send/receive


from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Literal

# ============================================================================
# DATABASE MODELS (What we store in PostgreSQL)
# ============================================================================

class ExpenseCreate(BaseModel):
    """
    Schema for creating a new expense  
    """
    amount: float = Field(..., gt=0, description="Amount spent in dollars")
    category: Literal["food", "transport", "entertainment", "shopping", "bills", "other"]
    description: str = Field(..., min_length=1, max_length=200)

    @field_validator('amount')
    def round_amount(cls,v):
        return round(v,2)
    

class Expense(BaseModel):
    """
    Complete expense record from database   
    """
    id: int
    amount: float
    category: str
    description: str
    created_at: datetime
    user_id: Optional[str] = None

    class Config:
        from_attributes = True   # Allows SQLALchemy model conversion


class BudgetCreate(BaseModel):
    """
    Schema for setting a budget
    """
    category: str
    amount: float = Field(..., gt = 0)


class Budget(BaseModel):
    """
    Budget record from database  
    """
    id: int
    category: str
    amount: float
    user_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# AGENT MODELS (What the LLM outputs) - NO MORE REGEX!
# ============================================================================

class AgentThought(BaseModel):
    """
    The agent's reasoning step

    LLM will output JSON matching this schema!
    No regex parsing needed!   
    """
    thought: str = Field(..., description = "What the agent is thinking")
    needs_tool: bool = Field(..., description="Does the agent need to use a tool?")
    tool_name: Optional[str] = Field(None, description="Which tool to use")
    tool_input: Optional[dict] = Field(None, description="Arguments for the tool")
    final_answer: Optional[str] = Field(None, description="Final response if task is complete")

class ToolResult(BaseModel):
    """
    Standardized tool execution result  
    """
    success: bool 
    message: str
    data: Optional[dict] = None

# ============================================================================
# API MODELS (What users send/receive)
# ============================================================================

class ChatRequest(BaseModel):
    """
    User's question to the agent
    """
    message: str = Field(..., min_length=1, max_length=500)
    user_id : Optional[str] = "default_user"

class ChatResponse(BaseModel):
    """
    Agent's Response to the user  
    """
    answer: str
    steps_taken: int
    tools_used: List[str]
    execution_time: float