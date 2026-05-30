# POC: Orquestacion Multi-Agente — MAF + ADK + A2A + Foundry

Prueba de concepto que demuestra comunicacion entre agentes de distintos frameworks
(Microsoft Agent Framework y Google ADK) usando el protocolo A2A como capa de
interoperabilidad, con despliegue de agentes en Azure AI Foundry.

## Que incluye este proyecto

| Componente | Framework | Puerto | Descripcion |
|---|---|---|---|
| Account Agent | OpenAI tool-calling custom | 8002 | Consulta de cuentas y transacciones bancarias |
| Compliance Agent | Google ADK 2.x | 8001 | Analisis de riesgo AML/KYC |
| MAF Orchestrator | Microsoft Agent Framework | 8003 / inline | 3 patrones de workflow (sequential, parallel, conditional) |
| Foundry PromptAgent | AIProjectClient SDK | cloud | Account Agent registrado como agente nombrado en Foundry |
| Foundry HostedAgent | MAF + azd | cloud | Compliance Agent desplegado como container en Foundry |

## Estructura

```
poc-maf-adk-a2a/
├── microsoft-agent/          # Account Agent (OpenAI tool-calling, puerto 8002)
├── google_agent/             # Compliance Agent (Google ADK, puerto 8001)
├── maf-orchestrator/         # Orquestador MAF con 3 patrones de workflow
├── foundry-hosted/           # Despliegue en Foundry (PromptAgent + HostedAgent)
│   ├── provision_account_agent.py   # Registra Account Agent como PromptAgent
│   ├── use_account_agent_maf.py     # Uso via MAF FoundryAgent + Responses API
│   └── compliance_hosted_agent/     # Scaffold para despliegue como HostedAgent
├── demo/                     # Demo de los 5 flujos de orquestacion
├── shared/database/          # Base de datos SQLite compartida
└── docs/                     # Documentacion detallada
```

## Documentacion

| Documento | Descripcion |
|---|---|
| [docs/setup.md](docs/setup.md) | Instalacion, configuracion y prerequisitos |
| [docs/architecture.md](docs/architecture.md) | Arquitectura completa: agentes, A2A, MAF, Foundry |
| [docs/demo.md](docs/demo.md) | Como correr los 5 flujos del demo |
| [docs/deployment.md](docs/deployment.md) | Despliegue de agentes en Foundry (PromptAgent y HostedAgent) |

## Inicio rapido

```powershell
# 1. Instalar dependencias (MAF + Account Agent)
uv sync

# 2. Configurar variables de entorno
copy maf-orchestrator\.env.example maf-orchestrator\.env
# Editar con tu FOUNDRY_PROJECT_ENDPOINT y FOUNDRY_MODEL

# 3. Autenticar con Azure
az login

# 4. Levantar Account Agent (terminal 1)
.venv\Scripts\python.exe microsoft-agent\server.py

# 5. Levantar Compliance Agent (terminal 2, usa miniconda3)
C:\Users\User\miniconda3\python.exe google_agent\server.py

# 6. Correr el demo (terminal 3)
.venv\Scripts\python.exe demo\orchestrator.py
```

Ver [docs/setup.md](docs/setup.md) para instrucciones completas.