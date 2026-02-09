from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import get_db, ExpenseRepository
from models import ChatRequest, ChatResponse, ExpenseCreate, Expense
from agent import chat_with_agent
from typing import List
from contextlib import asynccontextmanager
import traceback
import logging
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# STARTUP
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ============================
    # STARTUP
    # ============================
    print("🚀 Expense Tracking Agent API starting...")
    print("📊 Database: Connected")
    print("🤖 Agent: Ready")
    print("✅ API: Running on http://localhost:8000")
    print("📚 Docs: http://localhost:8000/docs")

    yield

    # ============================
    # SHUTDOWN
    # ============================
    print("🛑 Expense Tracking Agent API shutting down...")
    print("📊 Database: Disconnected")
    print("🤖 Agent: Stopped")
app = FastAPI(
    title="Expense Tracking Agent API",
    description="AI-powered expense tracking with natural language",
    version = "1.0.0",
    lifespan = lifespan

)

# CORS middleware (for web frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# AGENT ENDPOINTS
# ============================================================================

@app.post("/chat", response_model = ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Chat with the expense agent"""
    try:
        logger.info(f"Received request: {request.message} from user {request.user_id}")
        
        result = chat_with_agent(request.message, request.user_id)
        
        logger.info(f"Agent response: {result}")
        return ChatResponse(**result)
        
    except Exception as e:
        # Log the full error
        logger.error(f"Error in chat endpoint: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Return detailed error (only in development!)
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "type": type(e).__name__,
                "traceback": traceback.format_exc()
            }
        )
    
# ============================================================================
# DIRECT DATABASE ENDPOINTS (Bypass Agent)
# ============================================================================

@app.post("/expenses", response_model=Expense)
async def create_expense_direct(
    expense: ExpenseCreate,
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """
    Directly add expense without agent.
    Useful for integrations that don't need natural language.
    """
    repo = ExpenseRepository(db)
    return repo.create_expenses(expense, user_id)

@app.get("/expenses", response_model=List[Expense])
async def get_expenses(
    user_id: str = "default_user",
    category: str = None,
    db: Session = Depends(get_db)
):
    """Get all expenses for a user"""
    repo = ExpenseRepository(db)
    return repo.get_expenses_by_category(user_id, category)

@app.get("/expenses/summary")
async def get_expense_summary(
    user_id: str = "default_user",
    db: Session = Depends(get_db)
):
    """Get spending summary by category"""
    repo = ExpenseRepository(db)
    return {
        "totals": repo.get_total_by_category(user_id),
        "alerts": repo.check_budget_alerts(user_id)
    }

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Check if API and database are running"""
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")

