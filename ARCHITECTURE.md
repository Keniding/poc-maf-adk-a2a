# POC: Orquestacion Multi-Agente - MAF + ADK + A2A

Prueba de concepto de comunicacion entre agentes de distintos frameworks (Microsoft Agent Framework y Google ADK) usando el protocolo A2A como capa de interoperabilidad.

---

## Tabla de contenidos

1. [Resumen del sistema](#1-resumen-del-sistema)
2. [Agentes del sistema](#2-agentes-del-sistema)
3. [Protocolo A2A](#3-protocolo-a2a)
4. [Azure AI Foundry](#4-azure-ai-foundry)
5. [Google ADK](#5-google-adk)
6. [Microsoft Agent Framework (MAF)](#6-microsoft-agent-framework-maf)
7. [Flujos del demo (5 flujos)](#7-flujos-del-demo)
8. [Tiempos y caracteristicas de cada flujo](#8-tiempos-y-caracteristicas-de-cada-flujo)
9. [Estructura del proyecto](#9-estructura-del-proyecto)
10. [Como levantar el sistema](#10-como-levantar-el-sistema)

---

## 1. Resumen del sistema

El sistema conecta tres agentes independientes, cada uno construido con un framework distinto, que se comunican entre si mediante el protocolo A2A (Agent-to-Agent). El orquestador MAF expone tres patrones de workflow distintos que se pueden seleccionar por llamada.

```
demo/orchestrator.py
        |
        |-- [Flujo 1] httpx secuencial --> Account Agent (8002) --> Compliance Agent (8001)
        |
        |-- [Flujo 2] asyncio.gather   --> Account Agent (8002)
        |                              --> Compliance Agent (8001)
        |
        |-- [Flujo 3] MAF Sequential (add_chain)
        |       AccountFetch -> ComplianceFetch -> SynthesisExecutor (Foundry)
        |
        |-- [Flujo 4] MAF Parallel (fan-out + fan-in)
        |       [AccountFetchParallel || ComplianceFetchParallel] -> ParallelSynthesis (Foundry)
        |
        |-- [Flujo 5] MAF Conditional (switch-case)
                QueryRouter --> cuenta-only  --> AccountOnlyExecutor
                           --> compliance-only --> ComplianceOnlyExecutor
                           --> default        --> FullEntry -> ComplianceFetch -> Synthesis (Foundry)
```

---

## 2. Agentes del sistema

### 2.1 Account Agent (Microsoft)

| Campo             | Valor                                                                 |
|-------------------|-----------------------------------------------------------------------|
| Puerto            | 8002                                                                  |
| Framework         | Implementacion custom con OpenAI tool calling (AsyncOpenAI)           |
| Modelo            | gpt-5.4-nano via Azure AI Foundry                                     |
| Autenticacion     | AzureCliCredential + get_bearer_token_provider                        |
| Directorio        | microsoft-agent/                                                      |
| Inicio            | .venv/Scripts/python.exe server.py                                    |
| Base de datos     | shared/database/banking.db (SQLite)                                   |

**Herramientas disponibles:**

- `search_customer(query: str)` - Busca clientes por nombre (insensible a acentos), email, telefono o ID exacto
- `get_customer_accounts(customer_id: int)` - Lista cuentas y saldos de un cliente
- `get_account_transactions(account_id: int, limit: int)` - Historial de transacciones de una cuenta
- `search_products(product_type: str)` - Catalogo de productos bancarios activos

**Como funciona el tool calling:**

El agente ejecuta un loop de hasta 10 iteraciones. En cada iteracion llama al modelo con el historial de mensajes y los schemas de herramientas. Si el modelo responde con `finish_reason = "tool_calls"`, se ejecutan las funciones Python correspondientes y se agrega el resultado al historial. Cuando el modelo responde con `finish_reason = "stop"`, se retorna el mensaje final al cliente A2A.

```python
# Esquema simplificado del loop
messages = [system, user]
for _ in range(10):
    response = await openai.chat.completions.create(model=..., messages=messages, tools=schemas)
    if response.finish_reason == "stop":
        return response.message.content
    if response.finish_reason == "tool_calls":
        for call in response.tool_calls:
            result = tool_map[call.name](**args)
            messages.append(tool_result)
```

---

### 2.2 Compliance Agent (Google ADK)

| Campo             | Valor                                                                 |
|-------------------|-----------------------------------------------------------------------|
| Puerto            | 8001                                                                  |
| Framework         | Google ADK 2.1.0 (InMemoryRunner)                                    |
| Modelo            | gemini-2.0-flash (o gemini-2.0-flash-preview segun disponibilidad)   |
| Autenticacion     | GOOGLE_API_KEY en variable de entorno                                 |
| Directorio        | google_agent/                                                         |
| Inicio            | C:/Users/User/miniconda3/python.exe server.py                         |
| Entorno Python    | miniconda3 (separado del .venv del proyecto)                          |

**Herramientas disponibles:**

- `get_customer_risk_profile(customer_id: int)` - Score de riesgo, balance total, y numero de transacciones marcadas
- `check_transaction_risk(customer_id: int, days: int)` - Analisis de patrones AML en transacciones recientes (estructuracion, retiro post-deposito, efectivo, montos altos)
- `get_compliance_rules(category: str)` - Reglas AML/KYC internas por categoria (AML, FRAUD, RISK)

**Por que entorno separado:**

Google ADK 2.1.0 requiere una version de `google-generativeai` y `protobuf` que es incompatible con `agent-framework` (que necesita protobuf < 7). Al correr el Compliance Agent con miniconda3 y el resto con .venv se evita el conflicto de dependencias.

**Como funciona el InMemoryRunner:**

ADK maneja el estado de sesion internamente. Para cada invocacion A2A se crea una nueva sesion, se envia el mensaje del usuario como `genai_types.Content`, y se itera sobre los eventos del runner hasta encontrar el evento final (`is_final_response()`).

```python
session = await runner.session_service.create_session(app_name=..., user_id=...)
content = genai_types.Content(role="user", parts=[genai_types.Part(text=user_message)])
async for event in runner.run_async(user_id=..., session_id=session.id, new_message=content):
    if event.is_final_response():
        final_text += event.content.parts[0].text
```

---

### 2.3 MAF Orchestrator

| Campo             | Valor                                                                 |
|-------------------|-----------------------------------------------------------------------|
| Puerto            | 8003 (opcional, puede correr inline en el demo)                       |
| Framework         | Microsoft Agent Framework 1.7.0 (agent-framework)                    |
| Modelo            | gpt-5.4-nano via FoundryChatClient + AzureCliCredential              |
| Directorio        | maf-orchestrator/                                                     |
| Inicio            | .venv/Scripts/python.exe server.py                                    |
| Patrones          | sequential, parallel, conditional (seleccionable por parametro)       |

**Executors por patron:**

| Executor                         | Patron(es)              | Entrada      | Salida              |
|----------------------------------|-------------------------|--------------|---------------------|
| `AccountFetchExecutor`           | sequential, conditional | str          | dict                |
| `ComplianceFetchExecutor`        | sequential, conditional | dict         | dict                |
| `SynthesisExecutor`              | sequential, conditional | dict         | yield_output (str)  |
| `AccountFetchParallelExecutor`   | parallel                | str          | dict                |
| `ComplianceFetchParallelExecutor`| parallel                | str          | dict                |
| `ParallelSynthesisExecutor`      | parallel                | list[dict]   | yield_output (str)  |
| `QueryRouterExecutor`            | conditional, parallel   | str          | str (re-emite)      |
| `AccountOnlyExecutor`            | conditional             | str          | yield_output (str)  |
| `ComplianceOnlyExecutor`         | conditional             | str          | yield_output (str)  |
| `FullAnalysisEntryExecutor`      | conditional             | str          | dict                |

El patron se selecciona via el parametro `workflow_type` en la llamada A2A al servidor 8003, o llamando directamente a `create_sequential_workflow`, `create_parallel_workflow`, o `create_conditional_workflow` desde codigo.

---

## 3. Protocolo A2A

### Que es A2A

A2A (Agent-to-Agent) es un protocolo de comunicacion estandar para que agentes de distintos frameworks se llamen entre si de forma interoperable. Define dos endpoints HTTP:

| Endpoint                        | Metodo | Descripcion                                              |
|---------------------------------|--------|----------------------------------------------------------|
| `/.well-known/agent.json`       | GET    | AgentCard: metadatos del agente (nombre, skills, URL)    |
| `/a2a`                          | POST   | Invocacion del agente via JSON-RPC 2.0                   |

### AgentCard (descubrimiento)

Permite que cualquier cliente descubra las capacidades del agente sin conocer su implementacion interna.

```json
{
  "name": "Compliance Agent",
  "description": "AML/KYC compliance specialist for banking risk analysis",
  "version": "1.0",
  "url": "http://localhost:8001",
  "skills": [
    {"name": "get_customer_risk_profile", "description": "..."},
    {"name": "check_transaction_risk", "description": "..."}
  ]
}
```

### Invocacion (JSON-RPC 2.0)

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "agent.invoke",
  "params": {
    "input": "Analiza el riesgo AML del cliente 4"
  }
}
```

**Response exitosa:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "output": "### Informe de Cumplimiento AML/KYC ..."
  }
}
```

**Response de error:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32603,
    "message": "descripcion del error"
  }
}
```

### Como se construye un servidor A2A

Los servidores A2A del proyecto usan Starlette con dos rutas:

```python
from starlette.applications import Starlette
from starlette.routing import Route

async def handle_agent_card(request):
    return JSONResponse(agent_card_dict)

async def handle_a2a(request):
    body = await request.json()
    if body["method"] == "agent.invoke":
        output = await run_agent(body["params"]["input"])
        return JSONResponse({"jsonrpc": "2.0", "id": body["id"], "result": {"output": output}})

app = Starlette(routes=[
    Route("/.well-known/agent.json", handle_agent_card),
    Route("/a2a", handle_a2a, methods=["POST"]),
])
```

### Por que A2A

- Es framework-agnostico: el cliente no sabe ni le importa si el agente usa OpenAI, Gemini, o cualquier otro modelo
- Permite despliegue independiente de cada agente
- El AgentCard funciona como contrato de interfaz (similar a un OpenAPI spec para agentes)
- Los agentes pueden estar en distintas maquinas, lenguajes, o clouds

---

## 4. Azure AI Foundry

### Que es

Azure AI Foundry es la plataforma de Microsoft para desplegar y consumir modelos de lenguaje en Azure. Ofrece un endpoint unificado compatible con la API de OpenAI.

### Endpoint del proyecto

```
https://kenidinghk-5470-resource.services.ai.azure.com/api/projects/kenidinghk-5470
```

El endpoint de la API de OpenAI compatible se construye como:
```
{foundry_project_endpoint}/openai/v1
```

### Tipos de agentes en Foundry

**Prompt Agent (lo que usa este proyecto para Account Agent):**

- Es un agente construido por el desarrollador con su propio loop de tool calling
- Se consume el modelo via `AsyncOpenAI` apuntando al endpoint de Foundry
- El desarrollador controla completamente el prompt del sistema, las herramientas, el historial de mensajes, y las iteraciones
- Ventaja: control total, sin dependencias adicionales de Foundry mas alla del modelo
- Desventaja: hay que implementar el loop de tool calling manualmente

```python
from openai import AsyncOpenAI
client = AsyncOpenAI(api_key=token_provider, base_url=f"{endpoint}/openai/v1")
response = await client.chat.completions.create(model="gpt-5.4-nano", messages=..., tools=...)
```

**Hosted Agent (Foundry-managed):**

- Foundry gestiona el estado, las herramientas, los archivos, y el ciclo de vida del agente
- Se crean via `AIProjectClient` y se ejecutan con `AgentThread`
- Soportan file search (RAG sobre documentos), code interpreter, y funciones personalizadas de forma nativa
- Ventaja: menos codigo, integracion nativa con Azure Storage, Bing, etc.
- Desventaja: menos control, requiere azure-ai-projects SDK con versiones especificas

**MAF Agent con FoundryChatClient (lo que usa este proyecto para Synthesis):**

- Es el tipo de agente del framework MAF que se conecta a Foundry
- Abstrae la autenticacion y el loop de conversacion
- Se integra nativamente en los workflows de MAF (`WorkflowBuilder`)
- La autenticacion usa `AzureCliCredential` directamente en el constructor

```python
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

agent = Agent(
    client=FoundryChatClient(
        project_endpoint="https://...",
        model="gpt-5.4-nano",
        credential=AzureCliCredential(),
    ),
    name="BankingOrchestrator",
    instructions="Eres un orquestador bancario...",
)
response = await agent.run("Dame el analisis del cliente 1")
```

### Autenticacion

El proyecto usa `AzureCliCredential` (autenticacion via `az login`) en lugar de API keys. Esto requiere:

```bash
az login --use-device-code --tenant "3aab1b80-48dc-42c9-9855-c5c0701ce4a0" --scope "https://ai.azure.com/.default"
```

Para obtener el token en codigo se usa `get_bearer_token_provider` de `azure-identity`, que retorna un callable sincronico. Al usarlo con `AsyncOpenAI` (que espera un callable asincrono) se envuelve en una funcion async:

```python
from azure.identity import AzureCliCredential, get_bearer_token_provider
credential = AzureCliCredential()
_sync_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")

async def async_token_provider() -> str:
    return _sync_provider()

client = AsyncOpenAI(api_key=async_token_provider, base_url=base_url)
```

### Modelo gpt-5.4-nano

El modelo desplegado en el proyecto es `gpt-5.4-nano`. Se referencia por su nombre de deployment (no por el nombre del modelo en OpenAI), que en este caso coincide. Se pasa como parametro `model` en cada llamada.

---

## 5. Google ADK

### Que es

Google ADK (Agent Development Kit) es el framework de Google para construir agentes con Gemini. Version usada: `google-adk==2.1.0`.

### Componentes principales

**Agent:**
Define el agente con nombre, modelo, instrucciones, y lista de herramientas Python.

```python
from google.adk.agents import Agent

root_agent = Agent(
    name="compliance_agent",
    model="gemini-2.0-flash",
    description="Especialista AML/KYC",
    instruction="Eres un especialista en cumplimiento bancario...",
    tools=[get_customer_risk_profile, check_transaction_risk, get_compliance_rules],
)
```

ADK detecta automaticamente los tipos de parametros y descripciones de las funciones a partir de sus docstrings y type hints para construir los schemas de herramientas. El nombre de la funcion debe ser exacto (el modelo lo llama por nombre).

**InMemoryRunner:**
Ejecuta el agente manteniendo el estado de sesion en memoria. Cada instancia del runner tiene su propio `session_service`.

```python
from google.adk.runners import InMemoryRunner
runner = InMemoryRunner(agent=root_agent, app_name="compliance_agent")
```

**Ciclo de ejecucion:**
ADK emite eventos durante la ejecucion. El evento final (`is_final_response() == True`) contiene el texto de respuesta del agente.

### Como nombrar el directorio

ADK requiere que el nombre del directorio del agente sea un identificador Python valido (sin guiones). En este proyecto el directorio es `google_agent/` (con underscore). El archivo `agent.py` en la raiz del directorio debe exponer `root_agent`.

### Herramientas del Compliance Agent

Las herramientas consultan directamente la base de datos SQLite `shared/database/banking.db`:

- `get_customer_risk_profile`: calcula score de riesgo basado en numero de transacciones marcadas, balance, y reglas internas
- `check_transaction_risk`: detecta patrones AML como estructuracion (transacciones justo bajo $10,000), retiro masivo post-deposito (>80% en 48h), depositos en efectivo grandes, y transacciones inusuales
- `get_compliance_rules`: retorna las reglas codificadas en el sistema (AML-001, AML-002, FRAUD-001, FRAUD-002, RISK-001, RISK-002)

---

## 6. Microsoft Agent Framework (MAF)

### Que es

Microsoft Agent Framework (`agent-framework==1.7.0`) es el framework de Microsoft para construir agentes y workflows multi-agente de produccion. Repositorio: `microsoft/agent-framework`. Reemplaza a Semantic Kernel para casos de uso de orquestacion con workflows.

### Instalacion

```bash
pip install agent-framework
# o con uv:
uv add agent-framework --prerelease=allow
```

Nota: requiere `protobuf < 7`. Si el proyecto tiene otras dependencias con protobuf >= 7 (como Google ADK), deben instalarse en entornos separados.

### Componentes base del workflow

**Executor:**

Unidad basica de procesamiento. Recibe un mensaje de un tipo determinado, lo procesa, y envia el resultado al siguiente executor (`ctx.send_message`) o lo emite como salida final del workflow (`ctx.yield_output`).

```python
from agent_framework import Executor, WorkflowContext
from agent_framework._workflows._executor import handler

class MiExecutor(Executor):
    def __init__(self):
        super().__init__(id="mi_executor")  # id unico obligatorio

    @handler
    async def handle(self, mensaje: str, ctx: WorkflowContext) -> None:
        resultado = await procesar(mensaje)
        await ctx.send_message(resultado)   # -> siguiente executor
        # alternativa:
        await ctx.yield_output(resultado)   # -> WorkflowRunResult.get_outputs()
```

Reglas del `@handler`:
- El tipo del primer parametro (despues de `self`) define que mensajes acepta ese executor
- Un executor puede tener multiples handlers para distintos tipos de entrada
- `ctx.send_message()` envia datos al executor siguiente en el grafo
- `ctx.yield_output()` expone el dato como resultado final del workflow

**WorkflowBuilder:**

Construye el grafo dirigido de executors antes de ejecutarlo.

```python
from agent_framework import WorkflowBuilder

workflow = WorkflowBuilder(start_executor=primer_exec).add_chain([...]).build()
result = await workflow.run("input inicial")
outputs = result.get_outputs()
```

**Metodos de WorkflowBuilder:**

| Metodo                                            | Patron           | Descripcion                                                                      |
|---------------------------------------------------|------------------|----------------------------------------------------------------------------------|
| `add_chain([e1, e2, e3])`                         | Secuencial       | Cadena: salida de e1 va a e2, salida de e2 va a e3                               |
| `add_edge(src, dst, condition=None)`              | Secuencial       | Arista dirigida simple; condition permite filtrar que mensajes se enrutan        |
| `add_fan_out_edges(src, [e1, e2])`                | Paralelo         | src envia el mismo mensaje a e1 y e2 simultaneamente                             |
| `add_fan_in_edges([e1, e2], dst)`                 | Convergencia     | dst espera a que e1 Y e2 terminen; recibe list con ambos resultados              |
| `add_switch_case_edge_group(src, [Case, Default])`| Condicional      | src envia a uno solo de los targets segun las condiciones evaluadas en orden     |
| `add_multi_selection_edge_group(src, targets, fn)`| Multi-seleccion  | fn recibe el mensaje y la lista de IDs de targets, retorna cuales reciben        |

**Agent + FoundryChatClient:**

Agente conversacional conectado a Azure AI Foundry. Se usa como paso de sintesis dentro de un workflow.

```python
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

agent = Agent(
    client=FoundryChatClient(
        project_endpoint="https://...",
        model="gpt-5.4-nano",
        credential=AzureCliCredential(),
    ),
    name="NombreAgente",
    instructions="Instrucciones del sistema...",
)
respuesta = await agent.run("pregunta o tarea")
```

---

### Patron 1: Sequential (add_chain)

**Funcion:** `create_sequential_workflow(settings)`

Cada paso espera al anterior. El compliance recibe como contexto el resultado de cuentas, lo que le permite hacer un analisis mas informado (sabe los montos de las transacciones marcadas antes de evaluar riesgo).

```
str (query del usuario)
    |
    v
AccountFetchExecutor               id="account_fetch"
  POST /a2a -> Account Agent (8002)
  ctx.send_message({"query": q, "account_info": "..."})
    |
    v
ComplianceFetchExecutor            id="compliance_fetch"
  POST /a2a -> Compliance Agent (8001)
  ctx.send_message({"query": q, "account_info": "...", "compliance_info": "..."})
    |
    v
SynthesisExecutor                  id="synthesis"
  agent.run(prompt con ambas respuestas) -> FoundryChatClient -> gpt-5.4-nano
  ctx.yield_output(informe_integrado)
    |
    v
result.get_outputs()[0]
```

**Construccion:**

```python
workflow = (
    WorkflowBuilder(start_executor=account_exec)
    .add_chain([account_exec, compliance_exec, synthesis_exec])
    .build()
)
```

**Cuando usarlo:** cuando el compliance necesita saber el detalle de cuentas antes de evaluar, o cuando el orden de los pasos es semanticamente importante.

**Tiempo total:** T_account + T_compliance + T_foundry (suma de los tres)

---

### Patron 2: Parallel (fan-out + fan-in)

**Funcion:** `create_parallel_workflow(settings)`

Ambos agentes reciben la misma query al mismo tiempo. El synthesis espera a que los dos terminen (fan-in) y luego recibe una lista con ambos resultados.

```
str (query del usuario)
    |
    v
QueryRouterExecutor                id="query_router"
  ctx.send_message(query)  -- re-emite sin cambios
    |
    +---------------------------+
    |                           |
    v                           v
AccountFetchParallelExecutor   ComplianceFetchParallelExecutor
id="account_fetch_parallel"    id="compliance_fetch_parallel"
POST /a2a Account (8002)       POST /a2a Compliance (8001)
send({"agent":"account",...})  send({"agent":"compliance",...})
    |                           |
    +---------------------------+
               | fan-in: espera a los dos
               v
ParallelSynthesisExecutor          id="parallel_synthesis"
  recibe list[dict] con ambos resultados
  itera para extraer account_info y compliance_info
  agent.run(prompt) -> FoundryChatClient -> gpt-5.4-nano
  ctx.yield_output(informe_integrado)
    |
    v
result.get_outputs()[0]
```

**Construccion:**

```python
workflow = (
    WorkflowBuilder(start_executor=router)
    .add_fan_out_edges(router, [account_exec, compliance_exec])
    .add_fan_in_edges([account_exec, compliance_exec], synthesis_exec)
    .build()
)
```

**Detalle del fan-in:** el executor de destino recibe una lista con todos los mensajes de los sources. En este caso `ParallelSynthesisExecutor.handle(self, results: list, ctx)` — el tipo de la anotacion debe ser `list` para que MAF sepa que este executor acepta mensajes agregados.

**Cuando usarlo:** cuando los dos agentes son independientes entre si (el compliance no necesita el resultado de cuentas para funcionar). Reduce el tiempo total al maximo de los dos en lugar de la suma.

**Tiempo total:** max(T_account, T_compliance) + T_foundry

---

### Patron 3: Conditional (switch-case)

**Funcion:** `create_conditional_workflow(settings)`

Un router analiza la query y la enruta a uno de tres caminos. Las condiciones se evaluan en orden y la primera que retorna `True` gana. Si ninguna condicion coincide, se usa `Default`.

```
str (query del usuario)
    |
    v
QueryRouterExecutor                id="query_router"
  ctx.send_message(query)
    |
    +-- is_account_only(query)?  ---> AccountOnlyExecutor
    |   keywords: cuenta, saldo,       id="account_only"
    |   balance, transaccion, etc.     POST /a2a Account (8002)
    |   (sin palabras de compliance)   ctx.yield_output("[Solo cuenta]\n...")
    |
    +-- is_compliance_only(query)? --> ComplianceOnlyExecutor
    |   keywords: riesgo, aml,         id="compliance_only"
    |   compliance, fraude, kyc, etc.  POST /a2a Compliance (8001)
    |   (sin palabras de cuenta)       ctx.yield_output("[Solo compliance]\n...")
    |
    +-- Default -----------------> FullAnalysisEntryExecutor
                                       id="full_analysis_entry"
                                       POST /a2a Account (8002)
                                       send({"query": q, "account_info": "..."})
                                           |
                                           v
                                       ComplianceFetchExecutor
                                           id="compliance_fetch"
                                           POST /a2a Compliance (8001)
                                           send({..., "compliance_info": "..."})
                                           |
                                           v
                                       SynthesisExecutor
                                           id="synthesis"
                                           agent.run(...) -> Foundry
                                           ctx.yield_output(informe)
```

**Construccion:**

```python
from agent_framework._workflows._edge import Case, Default

workflow = (
    WorkflowBuilder(start_executor=router)
    .add_switch_case_edge_group(
        router,
        [
            Case(condition=is_account_only, target=account_only),
            Case(condition=is_compliance_only, target=compliance_only),
            Default(target=full_entry),
        ],
    )
    .add_chain([full_entry, compliance_full, synthesis])
    .build()
)
```

**Logica de las condiciones en este proyecto:**

```python
def is_account_only(query: str) -> bool:
    keywords = {"cuenta", "saldo", "balance", "transaccion", "deposito", "retiro"}
    return (any(k in query.lower() for k in keywords)
            and not any(k in query.lower() for k in {"riesgo", "aml", "compliance"}))

def is_compliance_only(query: str) -> bool:
    keywords = {"riesgo", "aml", "compliance", "fraude", "kyc", "lavado"}
    return (any(k in query.lower() for k in keywords)
            and not any(k in query.lower() for k in {"cuenta", "saldo", "transaccion"}))
```

**Cuando usarlo:** cuando se quiere ahorrar llamadas a agentes innecesarios. Si el usuario solo pide cuentas, no tiene sentido llamar al agente de compliance (y viceversa). El default cubre el caso ambiguo con analisis completo.

**Tiempo total:**
- Ruta cuenta-only: T_account
- Ruta compliance-only: T_compliance
- Ruta default (full): T_account + T_compliance + T_foundry

### Patrones de workflow implementados

Ver seccion 6 para la explicacion detallada de cada patron.

**Seleccion del patron via A2A (servidor 8003):**

```json
{"jsonrpc":"2.0","method":"agent.invoke","id":1,
 "params":{"input":"...","workflow_type":"sequential"}}
```

Valores validos de `workflow_type`: `sequential` (default), `parallel`, `conditional`.

**Seleccion directa desde codigo (sin servidor):**

```python
from agents.orchestrator import create_sequential_workflow, run_orchestration
workflow = await create_sequential_workflow(settings)
result = await run_orchestration(workflow, query)
```

### Como esta construido el MAF Orchestrator

```
maf-orchestrator/
    agents/
        executors.py    -- 10 executors para los 3 patrones de workflow
        orchestrator.py -- create_sequential/parallel/conditional_workflow()
    config/
        settings.py     -- Settings (endpoint Foundry, URLs de agentes, puerto)
    server.py           -- servidor A2A en puerto 8003, acepta workflow_type
    .env                -- FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_MODEL, puertos
```

---

## 7. Flujos del demo

El script `demo/orchestrator.py` ejecuta cinco flujos en secuencia. Todos usan los mismos dos agentes base (Account en 8002, Compliance en 8001). Los tres flujos MAF corren inline (sin servidor 8003).

### Flujo 1: Sequential httpx (cliente 4 - Jose Fernandez Torres)

El demo actua como orquestador manual sin ningun framework. Llama a los dos agentes en secuencia con httpx y presenta los resultados concatenados, sin sintesis por LLM.

```
demo/orchestrator.py
  |
  |-- httpx POST http://localhost:8002/a2a  (bloqueante)
  |        {"method":"agent.invoke","params":{"input":"Dame informacion del cliente 4..."}}
  |        respuesta: info de cuentas + transacciones
  |
  |-- httpx POST http://localhost:8001/a2a  (bloqueante, despues del anterior)
  |        {"method":"agent.invoke","params":{"input":"Analiza el riesgo AML del cliente 4..."}}
  |        respuesta: score de riesgo + analisis AML
  |
  print(account_result + compliance_result)
```

Framework de orquestacion: ninguno. Solo httpx y await.
Resultado tipico: cliente 4 ALTO RIESGO, score 72/100, cuenta bloqueada, 3 transacciones flagged (deposito efectivo $15k, retiro urgente $14k, compra joyeria $3.2k).

### Flujo 2: Concurrent asyncio (cliente 2 - Carlos Rodriguez Perez)

Las dos llamadas A2A se lanzan en paralelo con `asyncio.gather`. El tiempo total es el maximo de los dos, no la suma. No hay sintesis por LLM.

```
demo/orchestrator.py
  |
  |-- asyncio.gather(
  |       httpx POST http://localhost:8002/a2a,
  |       httpx POST http://localhost:8001/a2a
  |   )
  |        -- ambas corren al mismo tiempo --
  |        -- se espera hasta que las dos completen --
  |
  print(account_result + compliance_result)
```

Framework de orquestacion: ninguno. asyncio.gather + httpx.
Resultado tipico: cliente 2 patron de estructuracion, 4 transacciones $9k-$9.8k en 48h, score 45/100 pero escalado a CRITICO por evidencia.

### Flujo 3: MAF Sequential add_chain (cliente 1 - Maria Garcia Lopez)

Primer patron MAF. Usa `add_chain` para encadenar tres executors en secuencia. El compliance recibe el resultado de cuentas en su contexto. La sintesis final es generada por Foundry.

```
WorkflowBuilder(start_executor=account_exec).add_chain([account, compliance, synthesis]).build()

query (str)
  -> AccountFetchExecutor     -- POST Account Agent (8002)
       send({"query", "account_info"})
  -> ComplianceFetchExecutor  -- POST Compliance Agent (8001)
       send({"query", "account_info", "compliance_info"})
  -> SynthesisExecutor        -- agent.run(prompt) -> Foundry gpt-5.4-nano
       yield_output(informe integrado)
  -> result.get_outputs()[0]
```

Diferencia respecto a flujo 1: la respuesta final no es la concatenacion de dos respuestas sino un informe sintetizado y estructurado por el modelo Foundry.

### Flujo 4: MAF Parallel fan-out + fan-in (cliente 2 - Carlos Rodriguez Perez)

Segundo patron MAF. Usa `add_fan_out_edges` para enviar la query a ambos agentes simultaneamente, y `add_fan_in_edges` para esperar a que los dos terminen antes de sintetizar.

```
WorkflowBuilder(start_executor=router)
  .add_fan_out_edges(router, [account_parallel, compliance_parallel])
  .add_fan_in_edges([account_parallel, compliance_parallel], parallel_synthesis)
  .build()

query (str)
  -> QueryRouterExecutor      -- re-emite la query sin cambios
       |                   |
       v                   v
  AccountFetchParallel   ComplianceFetchParallel   <- corren al mismo tiempo
  POST Account (8002)    POST Compliance (8001)
  send({"agent":"account", "info":"..."})
                         send({"agent":"compliance","info":"..."})
       |                   |
       +-------------------+   <- fan-in: espera a los dos
                  v
         ParallelSynthesisExecutor
           recibe list[dict] con ambos resultados
           agent.run(prompt) -> Foundry gpt-5.4-nano
           yield_output(informe)
  -> result.get_outputs()[0]
```

Diferencia respecto a flujo 3 (sequential): los agentes corren en paralelo por lo que el tiempo se reduce, pero el compliance no tiene el contexto de cuentas al momento de procesar.

### Flujo 5: MAF Conditional switch-case (3 queries distintas)

Tercer patron MAF. Usa `add_switch_case_edge_group` para enrutar la query a uno de tres caminos segun palabras clave detectadas en el texto.

```
WorkflowBuilder(start_executor=router)
  .add_switch_case_edge_group(router, [
      Case(is_account_only,    target=account_only),
      Case(is_compliance_only, target=compliance_only),
      Default(                 target=full_entry),
  ])
  .add_chain([full_entry, compliance_full, synthesis])
  .build()
```

El demo ejecuta tres queries para demostrar los tres caminos:

**Caso cuenta-only** ("Muestra las cuentas y saldo del cliente con ID 3"):
- `is_account_only` = True (contiene "cuenta", "saldo", sin palabras AML)
- Ruta: AccountOnlyExecutor -> yield_output directo
- Solo se llama al Account Agent, sin Compliance ni Foundry

**Caso compliance-only** ("Analiza el riesgo AML y compliance del cliente con ID 4"):
- `is_compliance_only` = True (contiene "riesgo", "aml", "compliance", sin palabras de cuenta)
- Ruta: ComplianceOnlyExecutor -> yield_output directo
- Solo se llama al Compliance Agent, sin Account ni Foundry

**Caso default / analisis completo** ("Dame informacion del cliente con ID 1"):
- Ninguna condicion especifica coincide
- Ruta: FullAnalysisEntryExecutor -> ComplianceFetchExecutor -> SynthesisExecutor
- Se llaman ambos agentes en secuencia y Foundry sintetiza

---

## 8. Tiempos y caracteristicas de cada flujo

| Caracteristica               | F1: Sequential httpx | F2: Concurrent asyncio | F3: MAF Sequential | F4: MAF Parallel   | F5: MAF Conditional        |
|------------------------------|----------------------|------------------------|--------------------|--------------------|----------------------------|
| Account Agent llamado        | Si (bloqueante)      | Si (paralelo)          | Si (bloqueante)    | Si (paralelo)      | Solo si ruta lo requiere   |
| Compliance Agent llamado     | Si (despues acc.)    | Si (paralelo)          | Si (despues acc.)  | Si (paralelo)      | Solo si ruta lo requiere   |
| Foundry / LLM llamado        | No                   | No                     | Si (sintesis)      | Si (sintesis)      | Solo en ruta default       |
| Compliance ve datos de cuenta| No                   | No                     | Si (en contexto)   | No                 | Si (en ruta default)       |
| Sintesis por LLM             | No (print manual)    | No (print manual)      | Si                 | Si                 | Solo en ruta default       |
| Tiempo total (caso completo) | T_acc + T_comp       | max(T_acc, T_comp)     | T_acc+T_comp+T_fnd | max(T_acc,T_comp)+T_fnd | Variable segun ruta   |
| Framework de orquestacion    | Ninguno (httpx)      | asyncio + httpx        | MAF WorkflowBuilder| MAF WorkflowBuilder| MAF WorkflowBuilder        |
| MAF API usada                | -                    | -                      | add_chain          | fan_out + fan_in   | switch_case_edge_group     |
| Requiere servidor 8003       | No                   | No                     | No (inline)        | No (inline)        | No (inline)                |

T_acc = tiempo Account Agent (tipicamente 3-8s segun cuantas tool calls necesite el modelo)
T_comp = tiempo Compliance Agent (tipicamente 4-10s segun Gemini)
T_fnd = tiempo sintesis Foundry gpt-5.4-nano (tipicamente 5-15s segun longitud del informe)

**Cuando elegir cada patron:**

- F1 (sequential httpx): prototipado rapido, sin dependencias de framework, muestra los resultados crudos por separado
- F2 (concurrent asyncio): mismo que F1 pero mas rapido, cuando los dos agentes son independientes
- F3 (MAF sequential): cuando el compliance se beneficia de conocer los datos de cuenta, y se quiere un informe unificado sintetizado por LLM
- F4 (MAF parallel): maxima velocidad con sintesis LLM, cuando los agentes son independientes entre si
- F5 (MAF conditional): eficiencia cuando el usuario solo necesita uno de los dos agentes; evita llamadas innecesarias

---

## 9. Estructura del proyecto

```
poc-maf-adk-a2a/
    microsoft-agent/            -- Account Agent (OpenAI tool calling + Foundry)
        agents/
            account_agent.py    -- AccountAgent class, loop de tool calling
            tools.py            -- search_customer, get_customer_accounts, etc.
        config/settings.py      -- Settings (endpoint, modelo, puerto)
        server.py               -- servidor A2A en puerto 8002
        .env                    -- FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_MODEL_DEPLOYMENT_NAME

    google_agent/               -- Compliance Agent (Google ADK + Gemini)
        agent.py                -- root_agent con herramientas AML/KYC
        agents/
            compliance_agent.py -- instrucciones y definicion del agente
            tools.py            -- get_customer_risk_profile, check_transaction_risk, etc.
        config/settings.py      -- Settings (modelo, puerto)
        server.py               -- servidor A2A en puerto 8001

    maf-orchestrator/           -- MAF Orchestrator (WorkflowBuilder + FoundryChatClient)
        agents/
            executors.py        -- 10 executors para los 3 patrones de workflow:
                                   Sequential: AccountFetchExecutor, ComplianceFetchExecutor, SynthesisExecutor
                                   Parallel:   AccountFetchParallelExecutor, ComplianceFetchParallelExecutor, ParallelSynthesisExecutor
                                   Conditional: QueryRouterExecutor, AccountOnlyExecutor, ComplianceOnlyExecutor, FullAnalysisEntryExecutor
            orchestrator.py     -- create_sequential/parallel/conditional_workflow() + run_orchestration()
        config/settings.py      -- Settings (Foundry endpoint, model, agent URLs, puerto)
        server.py               -- servidor A2A en puerto 8003, acepta workflow_type en params
        .env                    -- FOUNDRY_PROJECT_ENDPOINT, FOUNDRY_MODEL, ACCOUNT_AGENT_URL, etc.

    shared/
        database/
            banking.db          -- SQLite con clientes, cuentas, transacciones, productos
            setup_db.py         -- script de inicializacion de la base de datos

    demo/
        orchestrator.py         -- demo de los 3 flujos (sequential, concurrent, MAF workflow)

    pyproject.toml              -- dependencias del .venv (agent-framework, openai, starlette, etc.)
    .venv/                      -- entorno virtual para microsoft-agent y maf-orchestrator
```

### Dependencias criticas por entorno

**.venv (microsoft-agent + maf-orchestrator):**
- `agent-framework==1.7.0` (MAF, incluye FoundryChatClient, WorkflowBuilder)
- `openai>=2.0.0` (client asincrono para Account Agent)
- `azure-identity>=1.21.0` (AzureCliCredential)
- `azure-ai-projects>=2.1.0` (AIProjectClient, opcional)
- `starlette`, `uvicorn` (servidores A2A)
- `httpx` (cliente HTTP para llamadas A2A)

**miniconda3 (google_agent):**
- `google-adk==2.1.0`
- `google-genai` (cliente Gemini)
- `protobuf>=7.35.0` (incompatible con agent-framework, por eso entorno separado)
- `starlette`, `uvicorn`

---

## 10. Como levantar el sistema

### Prerequisitos

1. `az login` con acceso al proyecto Foundry (`kenidinghk-5470`)
2. Variable `GOOGLE_API_KEY` con una API key valida de Google AI Studio
3. Base de datos inicializada: `.venv/Scripts/python.exe shared/database/setup_db.py`

### Inicio de agentes (3 terminales)

```powershell
# Terminal 1 - Account Agent
cd microsoft-agent
..\.venv\Scripts\python.exe server.py
# Escucha en http://localhost:8002

# Terminal 2 - Compliance Agent (usa miniconda)
C:\Users\User\miniconda3\python.exe google_agent/server.py
# Escucha en http://localhost:8001

# Terminal 3 - MAF Orchestrator (opcional, para acceso A2A en 8003)
cd maf-orchestrator
..\.venv\Scripts\python.exe server.py
# Escucha en http://localhost:8003
```

### Ejecutar el demo

```powershell
# Desde la raiz del proyecto
.\.venv\Scripts\python.exe demo/orchestrator.py
```

Corre los 3 flujos en secuencia. El flujo MAF WorkflowBuilder no necesita el servidor 8003 activo.

### Probar un agente individualmente con curl

```bash
# AgentCard
curl http://localhost:8002/.well-known/agent.json

# Invocar Account Agent
curl -X POST http://localhost:8002/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"agent.invoke","id":1,"params":{"input":"Busca al cliente con ID 1"}}'

# MAF Orchestrator - patron sequential (default)
curl -X POST http://localhost:8003/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"agent.invoke","id":1,"params":{"input":"Analiza al cliente con ID 4","workflow_type":"sequential"}}'

# MAF Orchestrator - patron parallel
curl -X POST http://localhost:8003/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"agent.invoke","id":1,"params":{"input":"Analiza al cliente con ID 2","workflow_type":"parallel"}}'

# MAF Orchestrator - patron conditional (solo cuentas)
curl -X POST http://localhost:8003/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"agent.invoke","id":1,"params":{"input":"Muestra el saldo y cuentas del cliente 1","workflow_type":"conditional"}}'
```

### Variables de entorno por agente

**microsoft-agent/.env:**
```
FOUNDRY_PROJECT_ENDPOINT=https://kenidinghk-5470-resource.services.ai.azure.com/api/projects/kenidinghk-5470
FOUNDRY_MODEL_DEPLOYMENT_NAME=gpt-5.4-nano
FOUNDRY_AGENT_NAME=account-agent
FOUNDRY_API_KEY=
AZURE_CREDENTIAL_TYPE=AzureCliCredential
ACCOUNT_A2A_PORT=8002
```

**google_agent/.env (o variable de entorno del sistema):**
```
GOOGLE_API_KEY=tu_api_key_aqui
GOOGLE_A2A_PORT=8001
```

**maf-orchestrator/.env:**
```
FOUNDRY_PROJECT_ENDPOINT=https://kenidinghk-5470-resource.services.ai.azure.com/api/projects/kenidinghk-5470
FOUNDRY_MODEL=gpt-5.4-nano
ACCOUNT_AGENT_URL=http://localhost:8002
COMPLIANCE_AGENT_URL=http://localhost:8001
MAF_ORCHESTRATOR_PORT=8003
```