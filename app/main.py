import asyncio,logging,os
from contextlib import asynccontextmanager
from uuid import uuid4
from fastapi import FastAPI,HTTPException,Request,status
from redis.asyncio import Redis
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from graph import create_orchestrator_graph
from app.schemas import ApprovalRequest,TaskAccepted,TaskRequest,TaskView
from app.store import JobStore
from app.worker import TaskWorker
from tracing import setup_phoenix_tracing
logging.basicConfig(level=os.getenv("LOG_LEVEL","INFO"))
def is_critical(query:str)->bool:
    terms=("borrar","eliminar","ejecutar","transferir","pagar","comprar","publicar","enviar","contratar","costo alto","coste alto","irreversible","producción")
    return any(term in query.casefold() for term in terms)
@asynccontextmanager
async def lifespan(app:FastAPI):
    url=os.getenv("REDIS_URL","redis://localhost:6379/0")
    redis=Redis.from_url(url,decode_responses=True)
    await redis.ping()
    saver_context=AsyncRedisSaver.from_conn_string(url)
    saver=await saver_context.__aenter__()
    await saver.asetup()
    setup_phoenix_tracing()
    store=JobStore(redis);queue=asyncio.Queue();graph=create_orchestrator_graph(checkpointer=saver);worker=TaskWorker(store,graph,queue)
    app.state.redis,app.state.store,app.state.queue=redis,store,queue
    workers=[asyncio.create_task(worker.run()) for _ in range(int(os.getenv("WORKER_CONCURRENCY","2")))]
    app.state.workers=workers
    for job in await store.pending_jobs():
        if job["status"] in {"RUNNING","APPROVED"}:await store.update(job["job_id"],status="PENDING")
        await queue.put(job["job_id"])
    try:yield
    finally:
        for task in workers:task.cancel()
        await asyncio.gather(*workers,return_exceptions=True)
        await saver_context.__aexit__(None,None,None)
        await redis.aclose()
app=FastAPI(title="API Multiagente de Investigación",version="1.0.0",lifespan=lifespan)
@app.get("/health")
async def health(request:Request):
    try:await request.app.state.redis.ping();return {"status":"ok","redis":"ok"}
    except Exception as exc:raise HTTPException(503,"Redis no está disponible.") from exc
@app.post("/tasks",response_model=TaskAccepted,status_code=status.HTTP_202_ACCEPTED)
async def create_task(payload:TaskRequest,request:Request):
    job_id=str(uuid4())
    critical=payload.requires_approval if payload.requires_approval is not None else is_critical(payload.query)
    job=await request.app.state.store.create(job_id,{"query":payload.query,"idioma_destino":payload.idioma_destino,"requires_approval":critical})
    await request.app.state.queue.put(job_id)
    return TaskAccepted(job_id=job_id,status=job["status"])
@app.get("/tasks/{job_id}",response_model=TaskView)
async def get_task(job_id:str,request:Request):
    job=await request.app.state.store.get(job_id)
    if job is None:raise HTTPException(404,"Trabajo no encontrado.")
    return job
@app.post("/tasks/{job_id}/approve",response_model=TaskView,status_code=status.HTTP_202_ACCEPTED)
async def approve_task(job_id:str,payload:ApprovalRequest,request:Request):
    store:JobStore=request.app.state.store;job=await store.get(job_id)
    if job is None:raise HTTPException(404,"Trabajo no encontrado.")
    if job["status"]!="WAITING_APPROVAL":raise HTTPException(409,f"Estado actual: {job['status']}.")
    updated=await store.update(job_id,status="PENDING",approval={"approved":payload.approved,"note":payload.note},approval_required=None)
    await request.app.state.queue.put(job_id);return updated
