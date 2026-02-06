from typing import Optional
from models import ExpenseCreate, ToolResult
from database import ExpenseRepository, get_db

# ============================================================================
# TOOL DEFINITIONS (No Database Knowledge!)
# ============================================================================

def add_expense_tool(
        amount: float,
        category: str,
        description: str,
        user_id: str = "default_user"
) -> ToolResult:
    """
    Add a new expense
        
    This tool ONLY knows about business logic.
    Database operations delegated to repository.
    """
    try:
        # validate input using pydantic
        expense_data = ExpenseCreate(
            amount = amount,
            category = category,
            description = description
        )

        # get database session
        db = next(get_db())
        repo = ExpenseRepository(db)

        # create expense
        expense = repo.create_expenses(expense_data, user_id)

        return ToolResult(
            success=True,
            message=f"✓ Expense added: ${expense.amount} for {expense.category}",
            data={"expense_id": expense.id, "amount": expense.amount}
        )

    except Exception as e:
        return ToolResult(
            success=False,
            message=f"✗ Error adding expense: {str(e)}",
            data=None
        )
    
def get_spending_summary_tool(
    category: Optional[str] = None,
    user_id: str = "default_user"
) -> ToolResult:
    """Get spending summary"""
    try:
        db = next(get_db())
        repo = ExpenseRepository(db)
        
        if category:
            expenses = repo.get_expenses_by_category(user_id, category)
            total = sum(e.amount for e in expenses)
            message = f"Category '{category}': {len(expenses)} expenses, Total: ${total:.2f}"
        else:
            totals = repo.get_total_by_category(user_id)
            message = "Spending by category:\n"
            grand_total = 0
            for cat, amount in totals.items():
                message += f"  • {cat.capitalize()}: ${amount:.2f}\n"
                grand_total += amount
            message += f"Grand Total: ${grand_total:.2f}"
        
        return ToolResult(
            success=True,
            message=message,
            data={"totals": totals if not category else {category: total}}
        )
        
    except Exception as e:
        return ToolResult(
            success=False,
            message=f"✗ Error: {str(e)}",
            data=None
        )

def set_budget_tool(
    category: str,
    amount: float,
    user_id: str = "default_user"
) -> ToolResult:
    """Set budget for a category"""
    try:
        db = next(get_db())
        repo = ExpenseRepository(db)
        
        budget = repo.set_budget(category, amount, user_id)
        
        return ToolResult(
            success=True,
            message=f"✓ Budget set for {category}: ${amount}",
            data={"category": budget.category, "amount": budget.amount}
        )
        
    except Exception as e:
        return ToolResult(
            success=False,
            message=f"✗ Error: {str(e)}",
            data=None
        )

def check_budgets_tool(user_id: str = "default_user") -> ToolResult:
    """Check budget alerts"""
    try:
        db = next(get_db())
        repo = ExpenseRepository(db)
        
        alerts = repo.check_budget_alerts(user_id)
        
        if not alerts:
            message = "✓ All categories within budget!"
        else:
            message = "⚠️ BUDGET ALERTS:\n"
            for alert in alerts:
                message += f"  • {alert['category']}: ${alert['spent']:.2f} spent (budget: ${alert['budget']:.2f}), over by ${alert['overage']:.2f}\n"
        
        return ToolResult(
            success=True,
            message=message,
            data={"alerts": alerts}
        )
        
    except Exception as e:
        return ToolResult(
            success=False,
            message=f"✗ Error: {str(e)}",
            data=None
        )

# ============================================================================
# TOOL REGISTRY (For Agent)
# ============================================================================

TOOLS = {
    "add_expense": add_expense_tool,
    "get_spending_summary": get_spending_summary_tool,
    "set_budget": set_budget_tool,
    "check_budgets": check_budgets_tool,
}

# ============================================================================
# TOOL SCHEMAS (For LLM to understand tools)
# ============================================================================

TOOL_SCHEMAS = {
    "add_expense": {
        "name": "add_expense",
        "description": "Add a new expense to track spending",
        "parameters": {
            "amount": {"type": "float", "description": "Amount in dollars"},
            "category": {"type": "string", "description": "Category: food, transport, entertainment, shopping, bills, other"},
            "description": {"type": "string", "description": "What was purchased"}
        },
        "required": ["amount", "category", "description"]
    },
    "get_spending_summary": {
        "name": "get_spending_summary",
        "description": "Get spending summary by category",
        "parameters": {
            "category": {"type": "string", "description": "Optional: specific category to check", "optional": True}
        },
        "required": []
    },
    "set_budget": {
        "name": "set_budget",
        "description": "Set spending limit for a category",
        "parameters": {
            "category": {"type": "string", "description": "Category name"},
            "amount": {"type": "float", "description": "Budget limit in dollars"}
        },
        "required": ["category", "amount"]
    },
    "check_budgets": {
        "name": "check_budgets",
        "description": "Check if any categories are over budget",
        "parameters": {},
        "required": []
    }
}


# **💡 Separation of Concerns:**
# """
# Tool Function                    Repository                Database
#      │                              │                         │
#      ├──────────────────────────────▶ Create expense         │
#      │  (Business logic)             │  (Data operation)      │
#      │                               │                         │
#      │                               ├─────────────────────────▶ INSERT INTO
#      │                               │                         │  (SQL)
#      │                               │ ◀───────────────────────┤
#      │ ◀─────────────────────────────┤                         │
#      │                                                         │
# """