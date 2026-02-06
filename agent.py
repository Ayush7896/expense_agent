from typing import TypedDict, Annotated, Literal, List
from langgraph.graph import START, StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from models import AgentThought, ToolResult
from tools import TOOLS
from prompts import EXPENSE_AGENT_SYSTEM_PROMPT
import json
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    """
    Everything the agent tracks     
    """
    user_input: str
    user_id: str
    conversation_history: List[dict]  # List for {role, content} messages
    current_thought: AgentThought
    iterations: int
    final_answer: str
    tools_used: List[str]

# ============================================================================
# AGENT NODE (WITH STRUCTURED OUTPUT!)
# ============================================================================

def agent_reasoning_node(state: AgentState) -> AgentState:
    """
    Agent's reasoning step using structured output

    No more REGEX, LLM outputs JSON the pydantic validates  
    """
    # Initialize LLM with structured output

    llm = ChatOpenAI(
        model = "gpt-4o-mini",
        temperature =0,
        model_kwargs={
            "response_format": {"type": "json_object"}  # Force JSON output
        }
    )
    # Build conversation history
    history_text = "\n".join([
        f"{msg['role']}: {msg['content']}"
        for msg in state["conversation_history"]
    ])
    
    # Build prompt
    prompt = EXPENSE_AGENT_SYSTEM_PROMPT.format(
        conversation_history=history_text,
        user_input=state["user_input"]
    )
    
    print(f"\n{'='*70}")
    print(f"🧠 REASONING STEP {state['iterations'] + 1}")
    print(f"{'='*70}\n")
    
    # Call LLM
    response = llm.invoke([HumanMessage(content=prompt)])
    
    print(f"🤖 LLM Raw Response:\n{response.content}\n")

    # Parse JSON response into Pydantic model (NO REGEX!)
    try:
        thought_data = json.loads(response.content)
        agent_thought = AgentThought(**thought_data)  # Pydantic validation!
        
        print(f"✅ Parsed AgentThought:")
        print(f"   Thought: {agent_thought.thought}")
        print(f"   Needs Tool: {agent_thought.needs_tool}")
        print(f"   Tool: {agent_thought.tool_name}")
        print(f"   Input: {agent_thought.tool_input}")
        print(f"   Final Answer: {agent_thought.final_answer}\n")
        
    except Exception as e:
        print(f"❌ Error parsing LLM output: {e}")
        # Fallback
        agent_thought = AgentThought(
            thought="Error parsing response",
            needs_tool=False,
            final_answer="I encountered an error. Please try again."
        )
    
    # Update state
    return {
        "current_thought": agent_thought,
        "iterations": state["iterations"] + 1,
        "conversation_history": state["conversation_history"] + [
            {"role": "assistant", "content": agent_thought.thought}
        ],
        "final_answer": agent_thought.final_answer or state.get("final_answer", "")
    }

# ============================================================================
# TOOL EXECUTION NODE
# ============================================================================

def tool_execution_node(state: AgentState) -> AgentState:
    """Execute the tool the agent decided to use"""
    thought = state["current_thought"]
    
    if not thought.tool_name:
        return state
    
    print(f"{'='*70}")
    print(f"🔧 EXECUTING TOOL: {thought.tool_name}")
    print(f"{'='*70}")
    print(f"Input: {thought.tool_input}\n")
    
    # Get tool function
    tool_func = TOOLS.get(thought.tool_name)
    
    if not tool_func:
        result = ToolResult(
            success=False,
            message=f"Unknown tool: {thought.tool_name}"
        )
    else:
        try:
            # Execute tool with user_id
            tool_input = thought.tool_input or {}
            tool_input["user_id"] = state["user_id"]
            
            result = tool_func(**tool_input)
            
        except Exception as e:
            result = ToolResult(
                success=False,
                message=f"Tool execution error: {str(e)}"
            )
    
    print(f"🔍 Tool Result:\n{result.message}\n")
    
    # Add tool result to conversation history
    return {
        "conversation_history": state["conversation_history"] + [
            {"role": "tool", "content": f"Tool '{thought.tool_name}' result: {result.message}"}
        ],
        "tools_used": state.get("tools_used", []) + [thought.tool_name]
    }

# ============================================================================
# ROUTING LOGIC
# ============================================================================

def should_continue(state: AgentState) -> Literal["execute_tool", "finish"]:
    """Decide next step"""
    thought = state["current_thought"]
    
    # Has final answer?
    if thought.final_answer:
        print("✅ Decision: FINISH (final answer ready)\n")
        return "finish"
    
    # Hit iteration limit?
    if state["iterations"] >= 10:
        print("⚠️ Decision: FINISH (max iterations)\n")
        return "finish"
    
    # Needs tool?
    if thought.needs_tool and thought.tool_name:
        print(f"➡️ Decision: EXECUTE_TOOL ({thought.tool_name})\n")
        return "execute_tool"
    
    print("⚠️ Decision: FINISH (no action)\n")
    return "finish"

# ============================================================================
# BUILD GRAPH
# ============================================================================

def create_expense_agent():
    """Create the expense agent graph"""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("reasoning", agent_reasoning_node)
    workflow.add_node("tool_execution", tool_execution_node)
    
    # Entry point
    workflow.set_entry_point("reasoning")
    
    # Conditional routing
    workflow.add_conditional_edges(
        "reasoning",
        should_continue,
        {
            "execute_tool": "tool_execution",
            "finish": END
        }
    )
    
    # Loop back after tool execution
    workflow.add_edge("tool_execution", "reasoning")
    
    return workflow.compile()

# ============================================================================
# CONVENIENCE INTERFACE
# ============================================================================

def chat_with_agent(message: str, user_id: str = "default_user") -> dict:
    """Simple chat interface"""
    agent = create_expense_agent()
    
    import time
    start_time = time.time()
    
    result = agent.invoke({
        "user_input": message,
        "user_id": user_id,
        "conversation_history": [],
        "current_thought": None,
        "iterations": 0,
        "final_answer": "",
        "tools_used": []
    })
    
    execution_time = time.time() - start_time
    
    return {
        "answer": result.get("final_answer", "No answer generated"),
        "steps_taken": result["iterations"],
        "tools_used": result.get("tools_used", []),
        "execution_time": round(execution_time,2)
    }



# LLM outputs this JSON:
# {
#   "thought": "I need to add the expense",
#   "needs_tool": true,
#   "tool_name": "add_expense",
#   "tool_input": {"amount": 50, "category": "food", "description": "lunch"}
# }

# # We parse with Pydantic:
# agent_thought = AgentThought(**json.loads(response.content))

# # Type-safe! Validated! No regex fragility!