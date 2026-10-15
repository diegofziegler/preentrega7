import os
from typing import Dict,Any
from dotenv import load_dotenv
from langchain_core.messages import AIMessage,SystemMessage
from state import MultiAgentState
from supervisor import extract_error_code,build_error_message
from logger import get_agent_logger
from llm import get_llm
load_dotenv()
logger=get_agent_logger()
DEFAULT_LANGUAGE=os.getenv("DEFAULT_LANGUAGE","Español")
def run_analyst_node(state:MultiAgentState)->Dict[str,Any]:
    language=state.get("idioma_destino") or DEFAULT_LANGUAGE
    prompt=("Sos especialista en análisis. Usá únicamente el reporte de investigación, sin conocimiento externo. "
    f"Respondé exclusivamente en {language}; indicá si los documentos no tienen evidencia.")
    try:
        response=get_llm(temperature=0.0).invoke([SystemMessage(content=prompt),*list(state["messages"])])
        return {"messages":[AIMessage(content=f"[RESPUESTA FINAL - ANALISTA]\n{response.content}",name="analista")]}
    except Exception as e:
        logger.exception("Excepción en Analyst")
        error=build_error_message(extract_error_code(e))
        return {"messages":[AIMessage(content=error,name="analista")],"execution_error":error}
