# Arquitectura del sistema

## Vision general

```
demo/orchestrator.py
        |
        |-- [Flujo 1] httpx secuencial ----> Account Agent (8002) -> Compliance Agent (8001)
        |
        |-- [Flujo 2] asyncio.gather  -----> Account Agent (8002)
        |                                --> Compliance Agent (8001)
        |
        |-- [Flujo 3] MAF Sequential ------> AccountFetch -> ComplianceFetch -> Synthesis (Foundry)
        |
        |-- [Flujo 4] MAF Parallel --------> [AccountFetch || ComplianceFetch] -> Synthesis (Foundry)
        |
        |-- [Flujo 5] MAF Conditional -----> QueryRouter --> account-only | compliance-only | full chain


foundry-hosted/
        |-- provision_account_agent.py    --> Foundry PromptAgent (interbank-account-agent)
        |-- compliance_hosted_agent/      --> Foundry HostedAgent (container en Foundry Agent Service)
```

---

## Agentes del sistema

### Account Agent (Microsoft)

| Campo | Valor |
|---|---|
| Puerto | 8002 |
| Framework | Implementacion custom con OpenAI tool calling (AsyncOpenAI) |
| Modelo | gpt-5.4-nano via Azure AI Foundry |
| Autenticacion | AzureCliCredential + get_bearer_token_provider |
| Directorio | `microsoft-agent/` |
| Inicio | `.venv/Scripts/python.exe server.py` |
| Base de datos | `shared/database/banking.db` (SQLite) |

**Herramientas:**
- `search_customer(query)` — busca por nombre (sin acentos), email, telefono, o ID
- `get_customer_accounts(customer_id)` — cuentas y saldos de un cliente
- `get_account_transactions(account_id, limit)` — historial de transacciones
- `search_products(product_type)` — catalogo de productos bancarios

**Loop de tool calling:**

```python
messages = [system, user]
for _ in range(10):
    response = await openai.chat.completions.create(model=..., messages=messages, tools=schemas)
    if response.finish_reason == "stop":
        return response.message.content
    if response.finish_reason == "tool_calls":
        for call in response.tool_calls:
            result = tool_map[call.name](**json.loads(call.arguments))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
```

---

### Compliance Agent (Google ADK)

| Campo | Valor |
|---|---|
| Puerto | 8001 |
| Framework | Google ADK 2.x (InMemoryRunner) |
| Modelo | gemini-2.0-flash |
| Autenticacion | GOOGLE_API_KEY |
| Directorio | `google_agent/` |
| Inicio | `C:\Users\User\miniconda3\python.exe server.py` |
| Entorno Python | miniconda3 (separado por conflicto de protobuf) |

**Herramientas:**
- `get_customer_risk_profile(customer_id)` — score de riesgo, balance total, numero de cuentas
- `check_transaction_risk(customer_id, days)` — analisis AML: estructuracion, efectivo, transacciones marcadas
- `get_compliance_rules(category)` — reglas internas AML/KYC/FRAUD por categoria

**Por que entorno separado:**

`agent-framework` requiere `protobuf < 7`. Google ADK requiere `protobuf >= 7.35.0`.
Son mutuamente excluyentes. El Compliance Agent corre con miniconda3; el resto con `.venv`.

**InMemoryRunner (ADK):**

ADK maneja estado de sesion internamente. Para cada invocacion A2A se crea una sesion nueva.

```python
session = await runner.session_service.create_session(app_name=..., user_id=...)
content = genai_types.Content(role="user", parts=[genai_types.Part(text=query)])
async for event in runner.run_async(user_id=..., session_id=session.id, new_message=content):
    if event.is_final_response():
        return event.content.parts[0].text
```

---

### MAF Orchestrator

| Campo | Valor |
|---|---|
| Puerto | 8003 (opcional) o inline |
| Framework | Microsoft Agent Framework (agent-framework) |
| Modelo | gpt-5.4-nano via FoundryChatClient + AzureCliCredential |
| Directorio | `maf-orchestrator/` |

**Tres patrones de workflow:**

#### Pattern 1: Sequential (add_chain)

```
AccountFetchExecutor -> ComplianceFetchExecutor -> SynthesisExecutor
     str query              dict{query,account}        dict{...,compliance} -> yield_output
```

```python
WorkflowBuilder(start_executor=account_exec)
    .add_chain([account_exec, compliance_exec, synthesis_exec])
    .build()
```

#### Pattern 2: Parallel (fan-out + fan-in)

```
QueryRouterExecutor ---> AccountFetchParallelExecutor --|
                    |                                   |--> ParallelSynthesisExecutor
                    |--> ComplianceFetchParallelExecutor|
```

El fan-in recibe `list[dict]` con todos los resultados acumulados.

```python
WorkflowBuilder(start_executor=router)
    .add_fan_out_edges(router, [account_exec, compliance_exec])
    .add_fan_in_edges([account_exec, compliance_exec], synthesis_exec)
    .build()
```

#### Pattern 3: Conditional (switch-case)

```
QueryRouterExecutor --> Case(is_account_only)    --> AccountOnlyExecutor
                    --> Case(is_compliance_only) --> ComplianceOnlyExecutor
                    --> Default                  --> FullAnalysisEntryExecutor -> ComplianceFetchExecutor -> SynthesisExecutor
```

```python
WorkflowBuilder(start_executor=router)
    .add_switch_case_edge_group(router, [
        Case(condition=is_account_only, target=account_only),
        Case(condition=is_compliance_only, target=compliance_only),
        Default(target=full_entry),
    ])
    .add_chain([full_entry, compliance_full, synthesis])
    .build()
```

**Executors:**

| Executor | Patron | Entrada | Salida |
|---|---|---|---|
| `AccountFetchExecutor` | sequential, conditional | str | dict |
| `ComplianceFetchExecutor` | sequential, conditional | dict | dict |
| `SynthesisExecutor` | sequential, conditional | dict | yield_output |
| `AccountFetchParallelExecutor` | parallel | str | dict |
| `ComplianceFetchParallelExecutor` | parallel | str | dict |
| `ParallelSynthesisExecutor` | parallel | list[dict] | yield_output |
| `QueryRouterExecutor` | conditional, parallel | str | str |
| `AccountOnlyExecutor` | conditional | str | yield_output |
| `ComplianceOnlyExecutor` | conditional | str | yield_output |
| `FullAnalysisEntryExecutor` | conditional | str | dict |

---

## Protocolo A2A

A2A (Agent-to-Agent) es un protocolo HTTP estandar para comunicacion entre agentes de
distintos frameworks. Define dos endpoints:

| Endpoint | Metodo | Descripcion |
|---|---|---|
| `/.well-known/agent.json` | GET | AgentCard: nombre, skills, URL del agente |
| `/a2a` | POST | Invocacion via JSON-RPC 2.0 |

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "agent.invoke",
  "params": {"input": "Analiza el riesgo del cliente 4"}
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {"output": "PERFIL DE RIESGO - Cliente 4 ..."}
}
```

**Por que A2A:**
- Framework-agnostico: el cliente no sabe si el agente usa OpenAI, Gemini, u otro
- Permite despliegue independiente de cada agente
- AgentCard como contrato de interfaz (equivalente a OpenAPI spec para agentes)
- Los agentes pueden estar en distintas maquinas, lenguajes, o clouds

---

## Azure AI Foundry

### Que es

Plataforma Microsoft para desplegar y consumir modelos de lenguaje en Azure.
Endpoint del proyecto:
```
https://kenidinghk-5470-resource.services.ai.azure.com/api/projects/kenidinghk-5470
```

### FoundryChatClient (MAF)

Conector de MAF con Foundry. Lee `FOUNDRY_PROJECT_ENDPOINT` y `FOUNDRY_MODEL` del entorno.

```python
from agent_framework.foundry import FoundryChatClient

client = FoundryChatClient(
    project_endpoint=settings.foundry_project_endpoint,
    model=settings.foundry_model,
    credential=AzureCliCredential(),
)
agent = Agent(client=client, name="...", instructions="...", tools=[...])
result = await agent.run("query")
```

### PromptAgent (en Foundry)

Agente registrado en Foundry como recurso nombrado y versionado.

- La definicion (modelo + instrucciones + esquemas de herramientas) vive en Foundry
- Las herramientas se ejecutan en el proceso del cliente
- Se crea con `AIProjectClient.agents.create_version()`
- Se llama con `FoundryAgent(agent_name=..., agent_version=...)` o via Responses API

```python
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool

project = AIProjectClient(endpoint=..., credential=...)
agent = project.agents.create_version(
    agent_name="interbank-account-agent",
    definition=PromptAgentDefinition(
        model="gpt-5.4-nano",
        instructions="...",
        tools=[FunctionTool(name="search_customer", ...)],
    ),
)
```

### HostedAgent (en Foundry Agent Service)

Codigo del agente desplegado como container dentro de Foundry.

- El agente completo (logica + herramientas) corre en un container gestionado por Foundry
- Foundry gestiona escalado, ciclo de vida, telemetria
- La autenticacion usa managed identity (`DefaultAzureCredential`, sin `az login`)
- El container expone `POST /responses` y `GET /readiness`
- Se despliega con `azd ai agent deploy`

Ver [deployment.md](deployment.md) para el proceso completo.

---

## Google ADK

Google Agent Development Kit (ADK) es el framework de Google para construir agentes
con herramientas. El agente se define declarativamente con instrucciones y lista de funciones.

```python
from google.adk.agents.llm_agent import Agent

agent = Agent(
    name="compliance_agent",
    model="gemini-2.0-flash",
    instruction="...",
    tools=[get_customer_risk_profile, check_transaction_risk, get_compliance_rules],
)
```

ADK integra con A2A via `to_a2a()` de `google.adk.a2a.utils.agent_to_a2a`:

```python
from google.adk.a2a.utils.agent_to_a2a import to_a2a

app = to_a2a(agent, host="localhost", port=8001, protocol="http")
```

Esto genera automaticamente:
- AgentCard en `/.well-known/agent.json`
- Endpoint A2A en `/a2a`
- Cola de tareas interna con executor
- Soporte de streaming

---

## Tiempos y caracteristicas por flujo

| Flujo | Llamadas LLM | Paralelismo | Tiempo estimado | Sintesis con LLM |
|---|---|---|---|---|
| 1 Secuencial A2A | 2 (uno por agente) | No | 8-15s | No |
| 2 Concurrente A2A | 2 (paralelo) | Si | 5-10s | No |
| 3 MAF Sequential | 3 (account + compliance + synthesis) | No | 12-20s | Si |
| 4 MAF Parallel | 3 (account || compliance + synthesis) | Si | 8-15s | Si |
| 5 MAF Conditional | 1-3 (segun ruta) | Segun ruta | 4-15s | Segun ruta |

Tiempos con modelo gpt-5.4-nano en Azure AI Foundry region eastus2.
Los agentes A2A incurren en una llamada HTTP adicional por cada invocacion.