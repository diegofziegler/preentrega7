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
4. Iniciar la API:
~~~powershell
uv run uvicorn app.main:app --reload
~~~
La API queda en http://localhost:8000, Swagger UI en http://localhost:8000/docs y Phoenix en http://localhost:6006.

## Docker
Con .env configurado: docker compose up --build

## HITL
Crear tarea con requires_approval true y esperar WAITING_APPROVAL:
~~~bash
curl -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"query":"Investigar el tema","requires_approval":true}'
~~~
Aprobar o rechazar con POST /tasks/JOB_ID/approve y JSON {"approved":true,"note":"Revisado"} o {"approved":false}. Consultar con GET /tasks/JOB_ID. /health comprueba Redis.

## Prueba paso a paso: API, cinco solicitudes y observabilidad

Sigue estos pasos en Windows PowerShell. Mantén abiertas las ventanas indicadas. Para que las tareas terminen correctamente y aparezcan trazas con tokens en Phoenix, configura una clave válida de Gemini o Groq en .env.

### 1. Preparar el entorno

Abre PowerShell en la carpeta del proyecto:

~~~powershell
Set-Location 'C:\Users\MINI PC\_diego\coderhouse\preentrega7'
~~~

Si todavía no existe .env, créalo desde el ejemplo:

~~~powershell
Copy-Item .env.example .env
~~~

Edita .env y completa GEMINI_API_KEY o GROQ_API_KEY. Deja LLM_PROVIDER en gemini o cámbialo a groq según la clave que configuraste. No compartas ni subas .env al repositorio.

Instala y sincroniza las dependencias con uv:

~~~powershell
uv sync
~~~

### 2. Iniciar Redis y Phoenix

En la primera ventana de PowerShell, inicia los servicios:

~~~powershell
docker compose up -d redis phoenix
~~~

Comprueba que estén activos:

~~~powershell
docker compose ps
~~~

Redis Stack debe aparecer como healthy o running. Incluye RedisJSON y RediSearch, necesarios para los checkpoints de LangGraph. Puedes comprobar los módulos con:

~~~powershell
docker compose exec redis redis-cli INFO modules
~~~

La salida debe incluir los módulos search y ReJSON. Comprueba también la conexión básica:

~~~powershell
docker compose exec redis redis-cli ping
~~~

La respuesta esperada es PONG. Como la API se inicia desde Windows, el puerto Redis debe estar publicado en el host. Confirma el mapeo con docker compose port redis 6379; debe mostrar el puerto 6379 de localhost. Si ya habías iniciado los contenedores antes de agregar el mapeo, aplica el cambio ejecutando docker compose up -d redis phoenix y vuelve a comprobar.

### 3. Iniciar la API

En una segunda ventana de PowerShell, ve a la carpeta del proyecto e inicia Uvicorn. Ejecuta solamente esta línea:

~~~powershell
Set-Location 'C:\Users\MINI PC\_diego\coderhouse\preentrega7'
uv run uvicorn app.main:app --reload
~~~

Deja esa ventana abierta mientras haces la prueba. La API estará en http://localhost:8000 y Swagger UI en http://localhost:8000/docs.

### 4. Confirmar que la API está disponible

En una tercera ventana de PowerShell, consulta el endpoint de salud:

~~~powershell
Invoke-RestMethod http://localhost:8000/health
~~~

Debe devolver status como ok y redis como ok. Si no responde, confirma que Redis sigue activo y revisa los mensajes de error de la ventana de Uvicorn.

### 5. Lanzar las cinco solicitudes concurrentes

Desde la tercera ventana, en la carpeta del proyecto, ejecuta:

~~~powershell
Set-Location 'C:\Users\MINI PC\_diego\coderhouse\preentrega7'
uv run python scripts/load_test.py
~~~

El script envía cinco POST /tasks en paralelo, consulta cada trabajo hasta que termine y muestra los cinco job_id, sus estados y la latencia p95 local. La corrida debe terminar con cinco estados DONE. El archivo screenshots/load-test-results.json guarda el resumen de esa corrida.

Si algún trabajo aparece FAILED, revisa el error consultando su estado con el job_id:

~~~powershell
Invoke-RestMethod http://localhost:8000/tasks/PEGA_AQUI_EL_JOB_ID
~~~

Revisa también los logs de Uvicorn. Confirma que la clave del proveedor esté bien configurada y que Phoenix y Redis sigan activos. No interpretes un FAILED como una corrida exitosa.

### 6. Revisar las trazas y guardar la evidencia

Abre http://localhost:6006 en el navegador. En el proyecto preentrega7-multiagente, selecciona el intervalo de tiempo que contiene la corrida y confirma que aparezcan las ejecuciones de los cinco trabajos y sus spans de LangGraph/LangChain.

Guarda capturas reales en la carpeta screenshots del repositorio:

1. Una captura de las trazas que muestre los cinco trabajos y los spans de sus nodos.
2. Una captura de la latencia p95 de esa corrida en Phoenix.
3. Una captura del costo por ejecución o del uso de tokens y el costo calculado por Phoenix.

La latencia p95 y el costo que se entregan como evidencia deben corresponder a esta corrida en el dashboard. El valor local de screenshots/load-test-results.json sirve para comprobar el envío y los estados, pero no sustituye las capturas de Phoenix. Para que Phoenix calcule el costo, el proveedor debe informar el uso de tokens y el modelo/precio debe estar reconocido o configurado en Phoenix.

### 7. Comprobar el flujo de aprobación humana (opcional)

Para forzar una tarea que se detenga a la espera de una persona, envía:

~~~powershell
$task = Invoke-RestMethod -Method Post -Uri http://localhost:8000/tasks -ContentType 'application/json' -Body '{"query":"Revisar esta tarea antes de ejecutarla","requires_approval":true}'
$task
~~~

Consulta el estado usando el job_id que devolvió la respuesta:

~~~powershell
Invoke-RestMethod "http://localhost:8000/tasks/$($task.job_id)"
~~~

Debe llegar a WAITING_APPROVAL. Apruébala para reanudar el grafo:

~~~powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/tasks/$($task.job_id)/approve" -ContentType 'application/json' -Body '{"approved":true,"note":"Revisado"}'
~~~

Después vuelve a consultar el estado hasta que llegue a DONE. Para rechazarla, cambia approved a false; el estado final será REJECTED.

### 8. Detener los servicios

Detén Uvicorn con Ctrl+C en su ventana. Cuando termines de revisar Phoenix y guardar las capturas, puedes detener Redis y Phoenix con:

~~~powershell
docker compose down
~~~