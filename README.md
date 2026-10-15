# Pre-entrega 7: API multiagente asíncrona

API FastAPI para el sistema Supervisor–Researcher–Analyst de Módulo 6. Usa LangGraph, Redis para estados y checkpoints, Phoenix/OpenInference y aprobación humana.

## Flujo
- POST /tasks persiste PENDING, encola y devuelve job_id con HTTP 202.
- GET /tasks/{job_id} consulta el estado.
- POST /tasks/{job_id}/approve reanuda el grafo pausado.
- Los estados incluyen PENDING, RUNNING, WAITING_APPROVAL, DONE, REJECTED y FAILED.
- Redis conserva trabajos/checkpoints; el worker de esta entrega despacha desde una cola local de proceso y reencola pendientes al reiniciar.
- requires_approval=true fuerza aprobación; si se omite, un detector por palabras clave señala operaciones sensibles.

## Requisitos e inicio
Python 3.12+, uv, Docker Compose y clave Gemini o Groq en .env.
1. Copiar .env.example a .env y configurar la clave.
2. Sincronizar dependencias: uv sync
3. Levantar Redis y Phoenix: docker compose up -d redis phoenix
4. Iniciar API: uv run uvicorn app.main:app --reload
API: http://localhost:8000; Swagger: /docs; Phoenix: http://localhost:6006.

## Docker
Con .env configurado: docker compose up --build

## HITL
Crear tarea con requires_approval true y esperar WAITING_APPROVAL:
~~~bash
curl -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"query":"Investigar el tema","requires_approval":true}'
~~~
Aprobar o rechazar con POST /tasks/JOB_ID/approve y JSON {"approved":true,"note":"Revisado"} o {"approved":false}. Consultar con GET /tasks/JOB_ID. /health comprueba Redis.

## Carga y capturas
Con API y servicios activos ejecutar uv run python scripts/load_test.py. El script envía cinco POST concurrentes, sigue su estado y guarda screenshots/load-test-results.json. En Phoenix, filtrar el proyecto preentrega7-multiagente y capturar trazas, costo/uso de tokens por ejecución y latencia p95 reales dentro de screenshots/. El costo depende de que el proveedor reporte uso de tokens y Phoenix tenga precios/modelo configurados; el JSON local no sustituye las capturas.

La API inicializa OpenInference al arrancar mediante tracing.py; revisar Phoenix para confirmar que recibe las trazas.
