import re
from typing import Literal,Dict,Any
from dotenv import load_dotenv
from pydantic import BaseModel,Field
from langchain_core.messages import SystemMessage,AIMessage
from state import MultiAgentState
from logger import get_agent_logger
from llm import get_llm
load_dotenv()
logger=get_agent_logger()
MAX_ITERATIONS=5
class RouterResponse(BaseModel):
    next_agent:Literal["researcher","analyst","FINISH"]=Field(description="Siguiente agente.")
    reasoning:str=Field(description="Motivo breve.")
SUPERVISOR_PROMPT=("Sos el Supervisor Orquestador. Si no hay reporte elegí researcher. "
"Después del reporte elegí analyst. Después de la respuesta final elegí FINISH. Evitá bucles.")
def extract_error_code(e:Exception)->str:
    s=str(e)
    if "429" in s or "RESOURCE_EXHAUSTED" in s or "rate_limit" in s.lower():return "429 RESOURCE_EXHAUSTED"
    if "401" in s or "UNAUTHENTICATED" in s or "API key" in s:return "401 UNAUTHENTICATED"
    if "403" in s or "PERMISSION_DENIED" in s:return "403 PERMISSION_DENIED"
    if "500" in s or "INTERNAL" in s:return "500 INTERNAL_SERVER_ERROR"
    m=re.search(r"(\d{3}\s+[A-Z_]+)",s)
    return m.group(1) if m else "ERROR_TECNICO"
def build_error_message(code:str)->str:return f"En este momento no puedo responder debido a problemas técnicos\n{code}"
async def run_supervisor_node(state:MultiAgentState)->Dict[str,Any]:
    iterations=state.get("iterations",0)+1
    if iterations>=MAX_ITERATIONS:return {"next":"FINISH","iterations":iterations}
    try:
        llm=get_llm(temperature=0.0).with_structured_output(RouterResponse)
        decision:RouterResponse=await llm.ainvoke([SystemMessage(content=SUPERVISOR_PROMPT),*list(state["messages"])])
        return {"next":decision.next_agent,"iterations":iterations}
    except Exception as e:
        logger.exception("Excepción en Supervisor")
        error=build_error_message(extract_error_code(e))
        return {"messages":[AIMessage(content=error,name="supervisor")],"next":"FINISH","iterations":iterations,"execution_error":error}
