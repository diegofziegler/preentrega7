import asyncio,logging
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from app.store import JobStore
logger=logging.getLogger("agent_api.worker")
class TaskWorker:
    def __init__(self,store:JobStore,graph,queue:asyncio.Queue):self.store,self.graph,self.queue=store,graph,queue
    async def run(self):
        while True:
            job_id=await self.queue.get()
            try:await self.process(job_id)
            except asyncio.CancelledError:raise
            except Exception:
                logger.exception("Error inesperado procesando %s",job_id)
                await self.store.update(job_id,status="FAILED",error="Error interno del worker.")
            finally:self.queue.task_done()
    async def process(self,job_id:str):
        job=await self.store.get(job_id)
        if not job or job["status"] in {"DONE","FAILED","REJECTED","WAITING_APPROVAL"}:return
        approval=job.get("approval")
        await self.store.update(job_id,status="RUNNING",error=None)
        config={"configurable":{"thread_id":job_id}}
        try:
            if approval is not None:
                result=await self.graph.ainvoke(Command(resume=approval),config=config)
            else:
                state={"messages":[HumanMessage(content=job["query"])],"idioma_destino":job["idioma_destino"],"iterations":0,"requires_approval":job["requires_approval"],"task_description":job["query"]}
                result=await self.graph.ainvoke(state,config=config)
            if approval is not None:await self.store.update(job_id,approval=None)
            interrupts=result.get("__interrupt__",[])
            if interrupts:
                detail=getattr(interrupts[0],"value",{})
                await self.store.update(job_id,status="WAITING_APPROVAL",approval_required=detail)
                return
            if result.get("execution_error"):
                await self.store.update(job_id,status="FAILED",error=result["execution_error"],approval=None)
                return
            if approval is not None and not approval.get("approved",False):
                await self.store.update(job_id,status="REJECTED",result="La persona revisora rechazó la ejecución.",approval=None)
                return
            messages=result.get("messages",[])
            final=next((m for m in reversed(messages) if getattr(m,"name","")=="analista"),messages[-1] if messages else None)
            await self.store.update(job_id,status="DONE",result=str(final.content) if final else "Finalizado sin respuesta.",error=None,approval=None)
        except Exception as exc:
            logger.exception("Fallo procesando %s",job_id)
            await self.store.update(job_id,status="FAILED",error=str(exc),approval=None)
