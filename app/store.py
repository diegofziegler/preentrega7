import json
from datetime import datetime,timezone
from typing import Any
from redis.asyncio import Redis
def now()->str:return datetime.now(timezone.utc).isoformat()
class JobStore:
    def __init__(self,redis:Redis,prefix:str="agent-api:job:"):self.redis,self.prefix=redis,prefix
    def key(self,job_id:str)->str:return f"{self.prefix}{job_id}"
    async def create(self,job_id:str,payload:dict[str,Any])->dict[str,Any]:
        stamp=now()
        job={"job_id":job_id,"status":"PENDING","query":payload["query"],"idioma_destino":payload.get("idioma_destino") or "Español","requires_approval":payload["requires_approval"],"created_at":stamp,"updated_at":stamp,"result":None,"error":None,"approval":None}
        await self.redis.set(self.key(job_id),json.dumps(job,ensure_ascii=False))
        return job
    async def get(self,job_id:str)->dict[str,Any]|None:
        raw=await self.redis.get(self.key(job_id));return json.loads(raw) if raw else None
    async def update(self,job_id:str,**fields:Any)->dict[str,Any]|None:
        job=await self.get(job_id)
        if job is None:return None
        job.update(fields);job["updated_at"]=now()
        await self.redis.set(self.key(job_id),json.dumps(job,ensure_ascii=False));return job
    async def pending_jobs(self)->list[dict[str,Any]]:
        result=[]
        async for key in self.redis.scan_iter(match=f"{self.prefix}*"):
            raw=await self.redis.get(key)
            if raw:
                job=json.loads(raw)
                if job["status"] in {"PENDING","RUNNING","APPROVED"}:result.append(job)
        return result
