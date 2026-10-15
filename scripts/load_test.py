"""Lanza cinco solicitudes concurrentes y registra la latencia individual del job."""
import asyncio,json,os,time
from pathlib import Path
import httpx
API=os.getenv("API_URL","http://localhost:8000")
QUERY=os.getenv("LOAD_TEST_QUERY","¿Quién fue Kanbun Uechi y qué estilo de Karate desarrolló?")
async def main():
    async with httpx.AsyncClient(base_url=API,timeout=30) as client:
        started=time.perf_counter()
        responses=await asyncio.gather(*(client.post("/tasks",json={"query":QUERY}) for _ in range(5)))
        for response in responses:response.raise_for_status()
        ids=[response.json()["job_id"] for response in responses]
        accepted=time.perf_counter()
        async def poll(job_id):
            while True:
                response=await client.get(f"/tasks/{job_id}");response.raise_for_status()
                job=response.json()
                if job["status"] in {"DONE","FAILED","REJECTED","WAITING_APPROVAL"}:
                    job["latency_seconds"]=time.perf_counter()-accepted
                    return job
                await asyncio.sleep(1)
        results=await asyncio.gather(*(poll(i) for i in ids))
        latencies=sorted(item["latency_seconds"] for item in results)
        p95=latencies[max(0,__import__("math").ceil(.95*len(latencies))-1)]
        report={"count":5,"job_ids":ids,"statuses":[j["status"] for j in results],"latency_seconds":latencies,"latency_p95_seconds":p95,"submit_seconds":accepted-started,"total_seconds":time.perf_counter()-started,"note":"La latencia local no reemplaza la métrica del dashboard Phoenix. Consultar Phoenix para costos por ejecución y p95 de trazas."}
        Path("screenshots").mkdir(exist_ok=True)
        Path("screenshots/load-test-results.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":asyncio.run(main())
