from typing import Literal, Any
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from state import MultiAgentState
from supervisor import run_supervisor_node
from agents.research_agent import run_research_node
from agents.analyst_agent import run_analyst_node
from logger import get_agent_logger
load_dotenv()
logger=get_agent_logger()
def route_supervisor(state: MultiAgentState)->Literal["researcher","analyst","__end__"]:
    node=state.get("next")
    return node if node in ("researcher","analyst") else END
def approval_gate(state: MultiAgentState)->dict[str,Any]:
    if not state.get("requires_approval",False): return {"approved":True}
    decision=interrupt({"type":"human_approval_required","message":"La tarea requiere aprobación humana.","task":state.get("task_description","")})
    return {"approved":bool(decision.get("approved",False))}
def route_approval(state: MultiAgentState)->Literal["supervisor","__end__"]:
    return "supervisor" if state.get("approved",False) else END
def create_orchestrator_graph(checkpointer=None):
    builder=StateGraph(MultiAgentState)
    builder.add_node("approval_gate",approval_gate)
    builder.add_node("supervisor",run_supervisor_node)
    builder.add_node("researcher",run_research_node)
    builder.add_node("analyst",run_analyst_node)
    builder.add_edge(START,"approval_gate")
    builder.add_conditional_edges("approval_gate",route_approval,{"supervisor":"supervisor",END:END})
    builder.add_conditional_edges("supervisor",route_supervisor,{"researcher":"researcher","analyst":"analyst",END:END})
    builder.add_edge("researcher","supervisor")
    builder.add_edge("analyst","supervisor")
    return builder.compile(checkpointer=checkpointer)
graph=create_orchestrator_graph()
