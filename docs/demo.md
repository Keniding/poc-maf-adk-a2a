# Como correr el demo

## Prerequisitos

Los dos agentes A2A deben estar corriendo antes de ejecutar el demo:

- Account Agent en puerto 8002 (`microsoft-agent/server.py` con `.venv`)
- Compliance Agent en puerto 8001 (`google_agent/server.py` con `miniconda3`)

Ver [setup.md](setup.md) para como levantarlos.

## Ejecutar el demo completo

```powershell
cd C:\Users\User\Documents\workspace\poc-maf-adk-a2a
.venv\Scripts\python.exe demo\orchestrator.py
```

El script ejecuta los 5 flujos en secuencia y muestra el output de cada uno.

## Los 5 flujos

### Flujo 1 — Secuencial A2A (httpx)

```
Account Agent (8002) --[A2A]--> Compliance Agent (8001) --> Sintesis manual
```

El orquestador llama a cada agente en secuencia usando `httpx` y el protocolo JSON-RPC.
No hay framework de orquestacion — solo HTTP puro.

Cliente de prueba: `A2AClient` en `demo/orchestrator.py`.

### Flujo 2 — Concurrente A2A (asyncio.gather)

```
Account Agent (8002) --|
                       |--> asyncio.gather --> Resultado combinado
Compliance Agent (8001)|
```

Ambos agentes se invocan en paralelo con `asyncio.gather`. Sin framework de orquestacion.

### Flujo 3 — MAF Sequential (add_chain)

```
AccountFetchExecutor -> ComplianceFetchExecutor -> SynthesisExecutor (Foundry)
```

Workflow MAF con `WorkflowBuilder.add_chain`. Cada executor espera al anterior.
El executor de sintesis usa un `Agent` con `FoundryChatClient` para generar el informe final.

### Flujo 4 — MAF Parallel (fan-out + fan-in)

```
QueryRouterExecutor --|-> AccountFetchParallelExecutor  --|
                      |                                   |--> ParallelSynthesisExecutor
                      |--> ComplianceFetchParallelExecutor|
```

Fan-out: ambos agentes reciben el mismo query simultaneamente.
Fan-in: `ParallelSynthesisExecutor` recibe `list[dict]` con los resultados de ambas ramas.

### Flujo 5 — MAF Conditional (switch-case)

```
QueryRouterExecutor --> [cuenta|saldo|balance]       --> AccountOnlyExecutor
                    --> [riesgo|aml|compliance|kyc]  --> ComplianceOnlyExecutor
                    --> (default)                    --> FullAnalysisEntryExecutor -> ComplianceFetchExecutor -> SynthesisExecutor
```

El router evalua keywords en el query y enruta a uno de tres caminos.
Tres queries de prueba muestran los tres caminos.

## Comparacion de flujos

| Flujo | Framework | Paralelismo | Sintesis con LLM | Patron MAF |
|---|---|---|---|---|
| 1 Secuencial A2A | ninguno | no | no | n/a |
| 2 Concurrente A2A | ninguno | si | no | n/a |
| 3 MAF Sequential | MAF | no | si (Foundry) | add_chain |
| 4 MAF Parallel | MAF | si | si (Foundry) | fan-out + fan-in |
| 5 MAF Conditional | MAF | segun ruta | segun ruta | switch-case |

## Codigo relevante

| Archivo | Descripcion |
|---|---|
| `demo/orchestrator.py` | Entry point del demo, 5 flujos |
| `maf-orchestrator/agents/orchestrator.py` | Creacion de los 3 workflows MAF |
| `maf-orchestrator/agents/executors.py` | 10 executors (sequential, parallel, conditional) |
| `maf-orchestrator/server.py` | Servidor A2A del orquestador (puerto 8003) |