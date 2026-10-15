import os
from typing import Dict,Any
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import AIMessage
from langgraph.prebuilt import create_react_agent
from state import MultiAgentState
from rag import search_context_sync
from supervisor import extract_error_code,build_error_message
from logger import get_agent_logger
from llm import get_llm
load_dotenv()
logger=get_agent_logger()
@tool
def buscar_en_vectorstore(query:str)->str:
    """Busca en la base documental histórica. Consultar siempre en español."""
    result=search_context_sync(query,k=4)
    return f"RESULTADOS DE BÚSQUEDA (Fuentes: {result['sources']}):\n{result['context']}"
PROMPT=("Eres investigador documental. Consulta la herramienta vectorial en español, cita las fuentes "
"y no realices el análisis final.")
def run_research_node(state:MultiAgentState)->Dict[str,Any]:
    try:
        agent=create_react_agent(model=get_llm(temperature=0.1),tools=[buscar_en_vectorstore],prompt=PROMPT)
        result=agent.invoke({"messages":list(state["messages"])})
        return {"messages":[AIMessage(content=f"[REPORTE DE INVESTIGACIÓN]\n{result['messages'][-1].content}",name="investigador")]}
    except Exception as e:
        logger.exception("Excepción en Researcher")
        error=build_error_message(extract_error_code(e))
        return {"messages":[AIMessage(content=error,name="investigador")],"execution_error":error}
