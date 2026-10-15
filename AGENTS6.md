# Pre-entrega 6: Orquestador multi-agente especializado

## ¿Qué debes construir?

Debes entregar un prototipo funcional de un **Orquestador Multi-Agente de Análisis e Investigación**. El sistema debe ser capaz de procesar una solicitud de usuario que requiera al menos dos dominios de especialización distintos y una fase de síntesis final.

### Especificaciones Confirmadas y Configuraciones

- **Soporte Multi-Proveedor de LLM**: Configurable mediante la variable `LLM_PROVIDER` (`gemini` o `groq` en el archivo `.env`).
  - **Gemini**: `GEMINI_API_KEY` y `GEMINI_MODEL_NAME` (predeterminado: `gemini-3-flash-preview`).
  - **Groq**: `GROQ_API_KEY` y `GROQ_MODEL_NAME` (predeterminado: `llama-3.3-70b-versatile`).
- **Observabilidad con Arize Phoenix (OpenInference)**:
  - `PHOENIX_COLLECTOR_ENDPOINT`: Endpoint local OTLP/HTTP (predeterminado: `http://localhost:6006/v1/traces`).
  - `PHOENIX_PROJECT_NAME`: Nombre del proyecto en Phoenix (predeterminado: `orquestador-multi-agente`).
- **Token Opcional HuggingFace**: `HF_TOKEN` para evitar advertencias de velocidad al descargar modelos de embeddings de HuggingFace.
- **Modelo de Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (HuggingFace, local).
- **Idioma de Respuesta por Defecto**: Configurado vía variable `DEFAULT_LANGUAGE` en `.env` (predeterminado: `"Español"`).
- **Auto-Ingesta RAG**: El sistema verifica la existencia de `./vectorstore`. Si no existe o está vacío, ejecuta automáticamente la ingesta a partir de los documentos Markdown en `./data`.
- **Archivos de Log**: Ubicados en `./log/`:
  - `agentes.log`: Registra los eventos del Orquestador Multi-Agente / Supervisor.
  - `rag.log`: Registra los eventos del sistema RAG / Retriever / Vector DB.
- **Gestión de Entorno y Dependencias**: Gestor `uv` con `pyproject.toml` y `requirements.txt`.
- **Manejo Elegante de Excepciones**:
  - En lugar de exponer un stacktrace en la consola cuando ocurre una excepción de API / cuota (por ejemplo, `429 RESOURCE_EXHAUSTED`), el error completo se registra en `log/agentes.log`.
  - El sistema captura la excepción y retorna un mensaje limpio y elegante en el orquestador:
    - **Línea 1**: `En este momento no puedo responder debido a problemas técnicos`
    - **Línea 2**: `<CÓDIGO / RESUMEN DE ERROR>` (ejemplo: `429 RESOURCE_EXHAUSTED`).

### Requerimientos Técnicos:

1. **Topología Jerárquica**: Un nodo `Supervisor` que actúa como router inteligente y controlador de flujo.
2. **Mínimo de 2 Agentes Especialistas**:
   - **Agente de Búsqueda/Investigación**: Con herramientas para consultar la Vector DB sobre los documentos en `./data`.
   - **Agente de Análisis/Cómputo**: Especializado en procesar los datos obtenidos, traducir/sintetizar la respuesta final en el `idioma_destino` especificado.
3. **Estado Compartido Estructurado**: Un esquema de `State` en LangGraph que permita rastrear qué agente ha contribuido con qué información, evitando la pérdida de contexto en la comunicación asíncrona.
4. **Flujo de Supervisión**: El supervisor debe decidir si la tarea está completa o si algún especialista debe refinar su output antes de dar la respuesta final.

## Pasos Sugeridos

1. **Define tu Estado**: Diseña una clase `TypedDict` que herede de `MessagesState`. Incluye campos como `idioma_destino` y `next`.
2. **Crea los Agentes Especialistas**: Define funciones que utilicen `create_react_agent` de LangGraph o prompts específicos para cada rol. Asegúrate de que cada uno tenga herramientas acotadas.
3. **Implementa el Supervisor**: Este es el cerebro. Su prompt debe ser claro: "Dada la conversación actual, ¿quién debe intervenir ahora o es momento de finalizar?". Debe mapear sus respuestas a los nombres de los nodos del grafo.
4. **Construye el Grafo**: Une los puntos. Usa `add_node` para cada agente y para el supervisor. Define las `Conditional Edges` que conecten al supervisor con los especialistas.
5. **Prueba la Interacción**: Lanza una consulta que obligue al supervisor a enviar la tarea al Investigador, recibir el dato, enviarlo al Analista y finalmente cerrar la conversación.

## Errores Comunes a Evitar

- **El "Supervisor Infinito"**: No definir una condición de parada clara, haciendo que el supervisor y los agentes entren en un bucle de correcciones eternas. Tip: Implementa un contador de pasos o un criterio de "Suficiencia" estricto.
- **Contaminación de Contexto**: Pasar todo el historial a todos los agentes en cada turno. Para sistemas explicables, los sub-agentes se ejecutan de forma aislada.

## Entregable

### Qué entregás y en qué formato

- **Tipo:** Código: repositorio github con `state.py`, la carpeta `agents/` (investigación + análisis), el grafo con nodo Supervisor, y un `README.md` con el diagrama Mermaid del grafo, explicando la topología elegida.
- **Adicional:** Notebook `demo.ipynb` o script `main.py` que demuestre el flujo de delegación.

---

## Buenas Prácticas

- **Uso de Salida Estructurada (Structured Output) en el Supervisor**
- **Atribución Clara de Mensajes (`name`)**
- **Aislamiento de Herramientas**
- **Aislamiento de Estado (Encapsulación en Nodos Wrapper)**
- **Invocación Asistida o Asíncrona Streaming (`astream`)**
