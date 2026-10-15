from typing import Literal
from pydantic import BaseModel,Field
class TaskRequest(BaseModel):
    query:str=Field(min_length=1,max_length=12000)
    idioma_destino:str|None=Field(default=None,max_length=60)
    requires_approval:bool|None=None
class ApprovalRequest(BaseModel):
    approved:bool
    note:str|None=Field(default=None,max_length=2000)
class TaskAccepted(BaseModel):
    job_id:str
    status:Literal["PENDING"]
class TaskView(BaseModel):
    job_id:str
    status:str
    query:str
    requires_approval:bool
    created_at:str
    updated_at:str
    result:str|None=None
    error:str|None=None
    approval:dict|None=None
    approval_required:dict|None=None
