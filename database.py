from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from typing import List, Optional
from models import Expense as ExpenseSchema, Budget as BudgetSchema

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DB_URI = "postgresql://postgres:ayush@172.29.208.1:5432/agent_campusx?sslmode=disable"

# create SQLAlchemy engine

engine = create_engine(
    DB_URI,
    pool_size = 10,     # Connection Pool size
    max_overflow = 20,  # Max Extra connections
    pool_pre_ping = True,  # Verfiy connections before use
    echo= False  # Set true to see sql queries
)

# create session factory
SessionLocal = sessionmaker(autocommit = False, autoflush = False, bind = engine)


# base class for models

Base = declarative_base()

# ============================================================================
# DATABASE TABLES (SQLAlchemy ORM)
# ============================================================================

class ExpenseTable(Base):
    """
    POstgresql table for expense
    Why use ORM instead of raw SQL?
    - Type safety
    - Automatic migrations
    - Relationship handling
    - SQL injection prevention
   
    """
    __tablename__ = "expenses"

    id = Column(Integer, primary_key = True, index = True)
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=False, index=True)  # Index for fast category queries
    description = Column(String(200), nullable=False)
    user_id = Column(String(100), nullable=False, default="default_user", index=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)

    # composite index for user + category queries (very common)
    __table_args__ = (
        Index('idx_user_category', 'user_id', 'category'),
    )

class BudgetTable(Base):
    """PostgreSQL table for budgets"""
    __tablename__ = "budgets"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    user_id = Column(String(100), nullable=False, default="default_user")
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    
    __table_args__ = (
        Index('idx_user_budget_category', 'user_id', 'category', unique=True),  # One budget per category per user
    )

# ============================================================================
# CREATE TABLES
# ===========================================================================

def init_db():
    """
    Initialize database tables  
    """
    Base.metadata.create_all(bind = engine)
    print("✅ Database tables created successfully!")

# ============================================================================
# DATABASE OPERATIONS (The "Repository Pattern")
# ============================================================================

class ExpenseRepository:
    """  
    Repository pattern: All database operations in one place

    Why?
    - single source of truth for data access
    - Easy to test (can mock this)
    - Easy to switch databases (just rewrite this class)
    - Transaction management in one place
    """

    def __init__(self, db_session):
        self.db = db_session

    def create_expenses(self, expense: ExpenseSchema, user_id: str = "default_user"):
        """
        Add new expense to database  
        """
        db_expense = ExpenseTable(
            amount = expense.amount,
            category = expense.category,
            description = expense.description,
            user_id = user_id
        )
        self.db.add(db_expense)
        self.db.commit()
        self.db.refresh(db_expense)

        return ExpenseSchema.model_validate(db_expense)
    
    def get_expenses_by_category(self, user_id: str, category: Optional[str] = None) -> List[ExpenseSchema]:
        """
        Get expenses, optionally filtered by category  
        """

        query = self.db.query(ExpenseTable).filter(ExpenseTable.user_id == user_id)
        if category:
            query = query.filter(ExpenseTable.category == category)

        expenses = query.order_by(ExpenseTable.created_at.desc()).all()
        return [ExpenseSchema.model_validate(e) for e in expenses]
    

    def get_total_by_category(self, user_id: str) -> dict:
        """
        Get total spending per category  
        """
        from sqlalchemy import func

        result = self.db.query(
            ExpenseTable.category,
            func.sum(ExpenseTable.amount).label('total')
        ).filter(
            ExpenseTable.user_id == user_id
        ).group_by(
            ExpenseTable.category
        ).all()

        return {row.category: float(row.total) for row in result}
    
    def set_budget(self, category: str, amount: float, user_id: str = "default_user") -> BudgetSchema:
        """Set or update budget for a category"""
        # Check if budget exists
        existing = self.db.query(BudgetTable).filter(
            BudgetTable.user_id == user_id,
            BudgetTable.category == category
        ).first()
        
        if existing:
            existing.amount = amount
            self.db.commit()
            self.db.refresh(existing)
            return BudgetSchema.from_orm(existing)
        else:
            new_budget = BudgetTable(
                category=category,
                amount=amount,
                user_id=user_id
            )
            self.db.add(new_budget)
            self.db.commit()
            self.db.refresh(new_budget)
            return BudgetSchema.from_orm(new_budget)
    
    def get_budgets(self, user_id: str) -> List[BudgetSchema]:
        """Get all budgets for a user"""
        budgets = self.db.query(BudgetTable).filter(
            BudgetTable.user_id == user_id
        ).all()
        return [BudgetSchema.from_orm(b) for b in budgets]
    
    def check_budget_alerts(self, user_id: str) -> List[dict]:
        """Check which categories are over budget"""
        budgets = self.get_budgets(user_id)
        totals = self.get_total_by_category(user_id)
        
        alerts = []
        for budget in budgets:
            spent = totals.get(budget.category, 0)
            if spent > budget.amount:
                alerts.append({
                    "category": budget.category,
                    "budget": budget.amount,
                    "spent": spent,
                    "overage": spent - budget.amount
                })
        
        return alerts
    
# ============================================================================
# DATABASE DEPENDENCY (For FastAPI)
# ============================================================================

def get_db():
    """
    Dependency function for FastAPI.
    
    Creates a new database session for each request,
    ensures it's closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize on import
init_db()


# # ❌ BAD: Database logic scattered everywhere
# def add_expense_tool():
#     # SQL directly in tool function
#     db.execute("INSERT INTO expenses...")
#     # Hard to test, hard to change database

# # ✅ GOOD: Repository pattern
# def add_expense_tool():
#     repo = ExpenseRepository(db)
#     repo.create_expense(expense)
#     # Tool doesn't know about SQL
#     # Easy to test with mock repository
#     # Easy to switch from PostgreSQL to MongoDB