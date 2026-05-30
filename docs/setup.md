# Setup e Instalacion

## Prerequisitos

| Herramienta | Version | Para que |
|---|---|---|
| Python | 3.11+ | Entorno principal (.venv) |
| uv | cualquiera | Gestor de paquetes del proyecto |
| Miniconda3 | cualquiera | Entorno aislado para Google ADK |
| Azure CLI | cualquiera | Autenticacion con Azure AI Foundry |
| azd (Azure Developer CLI) | 1.25.0+ | Despliegue de HostedAgent en Foundry |
| azd AI Agents extension | 0.1.27-preview+ | Comandos `azd ai agent` |

## Instalacion de dependencias

### Entorno principal (.venv) — MAF + Account Agent + Demo

```powershell
# Desde la raiz del proyecto
uv sync
```

Instala: `agent-framework`, `azure-identity`, `azure-ai-projects`, `starlette`, `uvicorn`, `httpx`, `python-dotenv`, `aiosqlite`.

### Entorno Google ADK (miniconda3) — Compliance Agent

Google ADK requiere `protobuf >= 7.35.0` que es incompatible con `agent-framework` (necesita `protobuf < 7`). Por eso el Compliance Agent corre en un entorno separado.

```powershell
# Instalar dependencias en miniconda3
C:\Users\User\miniconda3\python.exe -m pip install google-adk aiosqlite python-dotenv
```

## Configuracion

### 1. MAF Orchestrator + Account Agent

Crear `maf-orchestrator/.env` (o copiar desde el ejemplo si existe):

```env
FOUNDRY_PROJECT_ENDPOINT=https://kenidinghk-5470-resource.services.ai.azure.com/api/projects/kenidinghk-5470
FOUNDRY_MODEL=gpt-5.4-nano
ACCOUNT_AGENT_URL=http://localhost:8002
COMPLIANCE_AGENT_URL=http://localhost:8001
MAF_ORCHESTRATOR_PORT=8003
```

### 2. Compliance Agent (Google ADK)

Crear `google_agent/.env`:

```env
GOOGLE_API_KEY=tu_api_key_aqui
GOOGLE_MODEL=gemini-2.0-flash
A2A_PORT=8001
```

### 3. Autenticacion Azure

```powershell
az login
# Verificar que la cuenta correcta esta activa
az account show
```

## Levantar los servidores

### Terminal 1: Account Agent (puerto 8002)

```powershell
cd C:\Users\User\Documents\workspace\poc-maf-adk-a2a
.venv\Scripts\python.exe microsoft-agent\server.py
```

Esperar: `Starting A2A server on port 8002`

### Terminal 2: Compliance Agent (puerto 8001)

```powershell
cd C:\Users\User\Documents\workspace\poc-maf-adk-a2a
C:\Users\User\miniconda3\python.exe google_agent\server.py
```

Esperar: `Starting Compliance Agent A2A Server on port 8001`

### (Opcional) Terminal 3: MAF Orchestrator como servidor A2A (puerto 8003)

Solo necesario si quieres llamar al orquestador via HTTP. El demo lo corre de forma inline.

```powershell
.venv\Scripts\python.exe maf-orchestrator\server.py
```

## Verificar que todo esta corriendo

```powershell
# AgentCard del Account Agent
curl http://localhost:8002/.well-known/agent.json

# AgentCard del Compliance Agent
curl http://localhost:8001/.well-known/agent.json

# Invocar Account Agent directamente
curl -X POST http://localhost:8002/a2a `
  -H "Content-Type: application/json" `
  -d '{"jsonrpc":"2.0","id":1,"method":"agent.invoke","params":{"input":"Buscar cliente con ID 1"}}'
```

## Base de datos

El archivo `shared/database/banking.db` ya esta inicializado con datos de prueba.
Si necesitas recrearlo:

```powershell
.venv\Scripts\python.exe shared\database\setup_db.py
```

Contiene 5 clientes con distintos perfiles de riesgo, cuentas, transacciones, y reglas de compliance.

## Estructura de entornos

```
poc-maf-adk-a2a/
├── .venv/                  # MAF + Account Agent + Demo + MAF Orchestrator
│   └── ...                 # agent-framework, azure-*, starlette, httpx
└── C:\Users\User\miniconda3\  # Google ADK
    └── ...                 # google-adk, google-generativeai, protobuf>=7
```

La separacion de entornos existe por un conflicto de `protobuf`:
- `agent-framework` requiere `protobuf < 7`
- `google-adk` requiere `protobuf >= 7.35.0`

No hay forma de satisfacer ambas restricciones en el mismo entorno.