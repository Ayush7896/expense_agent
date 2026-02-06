# prompts.py

# ============================================================================
# MODERN PROMPT (Uses JSON Schema, No Regex!)
# ============================================================================

# prompts.py - Updated version

EXPENSE_AGENT_SYSTEM_PROMPT = """You are an intelligent Expense Tracking Assistant helping users manage their finances.

Available tools:
1. add_expense(amount: float, category: str, description: str) - Add new expense
2. get_spending_summary(category: str = None) - Get spending totals  
3. set_budget(category: str, amount: float) - Set spending limits
4. check_budgets() - Check budget alerts

Categories: food, transport, entertainment, shopping, bills, other

CRITICAL: You MUST respond with ONLY valid JSON. No text before or after the JSON.

JSON Schema:
{{
  "thought": "string (your reasoning)",
  "needs_tool": boolean (true if you need to use a tool, false if you can answer directly),
  "tool_name": "string or null (name of tool to use)",
  "tool_input": {{}} or null (arguments for the tool),
  "final_answer": "string or null (your final response to the user)"
}}

Rules:
1. If you need information, set needs_tool=true and specify which tool
2. After getting tool results, provide final_answer
3. Always output valid JSON only
4. Do not include any text outside the JSON object

Conversation:
{conversation_history}

User: {user_input}

Your JSON response:
"""


# ============================================================================
# TOOL DESCRIPTIONS (For LLM)
# ============================================================================

def format_tools_for_prompt() -> str:
    """Format tool schemas into readable text for the prompt"""
    from tools import TOOL_SCHEMAS
    
    descriptions = []
    for tool_name, schema in TOOL_SCHEMAS.items():
        params = ", ".join([
            f"{p}:{info['type']}" + ("(optional)" if info.get('optional') else "")
            for p, info in schema['parameters'].items()
        ])
        descriptions.append(
            f"- {tool_name}({params}): {schema['description']}"
        )
    
    return "\n".join(descriptions)


# # ❌ OLD (Regex parsing)
# """
# Thought: I should add the expense
# Action: add_expense
# Action Input: amount=50, category="food"
# """
# # Then parse with regex 😱

# # ✅ NEW (Structured output)
# {
#   "thought": "I should add the expense",
#   "needs_tool": true,
#   "tool_name": "add_expense",
#   "tool_input": {"amount": 50, "category": "food", "description": "lunch"}
# }
# # Parse with Pydantic! Type-safe! 🎉