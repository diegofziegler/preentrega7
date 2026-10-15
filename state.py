from typing import Annotated,Sequence
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
class MultiAgentState(TypedDict,total=False):
    messages:Annotated[Sequence[BaseMessage],add_messages]
    next:str
    idioma_destino:str
    task_completed:bool
    iterations:int
    requires_approval:bool
    task_description:str
    approved:bool
    execution_error:str
