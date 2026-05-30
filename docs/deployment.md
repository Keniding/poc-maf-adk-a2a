# Despliegue de agentes en Azure AI Foundry

Este documento describe como desplegar los agentes del proyecto en Foundry.
Todos los archivos estan en `foundry-hosted/`.

## Tipos de agente en Foundry

### PromptAgent

Un PromptAgent es una **definicion de agente almacenada en Foundry**: nombre, version,
modelo, instrucciones, y esquemas de herramientas. El agente vive en Foundry como un
recurso nombrado y versionado.

- Las herramientas se ejecutan en el proceso del cliente (no en Foundry)
- Se provisiona con `AIProjectClient.agents.create_version()`
- Se llama via `openai.responses.create()` con `agent_reference` o via `FoundryAgent` de MAF
- No requiere contenedor ni infraestructura adicional
- Ventaja: simple, sin deploy de codigo

### HostedAgent

Un HostedAgent es **codigo que corre dentro de la infraestructura de Foundry**
(Azure Container Registry + Foundry Agent Service). El agente completo (logica,
herramientas, loop de llamadas) vive en un container gestionado por Foundry.

- Las herramientas se ejecutan dentro del container
- Se despliega con `azd ai agent deploy`
- Foundry gestiona escalado, ciclo de vida, telemetria, y managed identity
- La autenticacion usa `DefaultAzureCredential` (managed identity del container, sin `az login`)
- El container expone `POST /responses` y `GET /readiness`
- Ventaja: sin gestion de infraestructura, autoscaling, logs centralizados en portal

## Comparacion

| | PromptAgent | HostedAgent |
|---|---|---|
| Donde vive la definicion | Foundry (nombre + version) | Container en Foundry Agent Service |
| Donde corren las herramientas | Proceso del cliente | Dentro del container |
| Como se provisiona | `project.agents.create_version()` | `azd ai agent deploy` |
| Autenticacion | AzureCliCredential (local) | DefaultAzureCredential (managed identity) |
| Uso desde MAF | `FoundryAgent(agent_version="1")` | `FoundryAgent()` (sin version) |
| Escalado | N/A | Foundry autoscala |
| Requiere container | No | Si (Docker) |

---

## Agente 1: Account Agent como PromptAgent

Registra el Account Agent (instrucciones + 4 herramientas) como agente nombrado en Foundry.

### Provision (una sola vez)

```powershell
cd C:\Users\User\Documents\workspace\poc-maf-adk-a2a
.venv\Scripts\activate
python foundry-hosted\provision_account_agent.py
```

Output esperado:
```
Connecting to Foundry: https://kenidinghk-5470-resource.services.ai.azure.com/api/projects/kenidinghk-5470
Provisioning agent 'interbank-account-agent' v1.0...
Agent provisioned: name=interbank-account-agent, version=1
```

El agente queda visible en el portal Foundry bajo Build > Agents.

### Uso via MAF FoundryAgent

```powershell
python foundry-hosted\use_account_agent_maf.py
```

El script muestra dos formas de llamar al agente:

**Opcion 1 - MAF FoundryAgent** (reemplaza el `Agent` inline del maf-orchestrator):
```python
from agent_framework.foundry import FoundryAgent

agent = FoundryAgent(
    project_endpoint=settings.foundry_project_endpoint,
    agent_name="interbank-account-agent",
    agent_version="1",
    credential=AzureCliCredential(),
    tools=[search_customer, get_customer_accounts, get_account_transactions, search_products],
)
result = await agent.run("Dame las cuentas del cliente 1")
```

**Opcion 2 - Responses API directa** (framework-agnostico):
```python
from azure.ai.projects import AIProjectClient

project = AIProjectClient(endpoint=..., credential=...)
openai = project.get_openai_client()

response = openai.responses.create(
    extra_body={"agent_reference": {"name": "interbank-account-agent", "type": "agent_reference"}},
    input="Dame las cuentas del cliente 1",
)
print(response.output_text)
```

---

## Agente 2: Compliance Agent como HostedAgent

El Compliance Agent completo (MAF Agent + tools SQLite) corre como container
en Foundry Agent Service.

### Prerequisitos

```powershell
# Instalar Azure Developer CLI
winget install Microsoft.Azd

# Instalar extension de agentes (version 0.1.27-preview o superior)
azd ext install azure.ai.agents

# Autenticar
azd auth login
```

### Estructura del scaffold

```
foundry-hosted/compliance_hosted_agent/
├── main.py           # Servidor Starlette con /responses y /readiness
├── tools.py          # Copia de las tools con DB_PATH local
├── banking.db        # Base de datos bundleada en el container
├── requirements.txt  # Dependencias del container
├── Dockerfile        # Imagen Docker
├── agent.yaml        # Definicion del agente (generado por azd ai agent init)
├── azure.yaml        # Configuracion de servicio (generado por azd ai agent init)
└── infra/            # Bicep para ACR y recursos (generado por azd ai agent init)
```

### Provision (crea ACR y recursos de infra)

```powershell
cd foundry-hosted\compliance_hosted_agent

# Si el resource group ya existe en otra region:
azd env set AZURE_LOCATION eastus

azd provision
```

Crea: Azure Container Registry, model deployment, conexion Foundry-ACR.

### Deploy (build y push del container)

```powershell
azd deploy
```

Hace build del Dockerfile en el ACR (remote build) y registra el container
como HostedAgent en Foundry. Output al terminar:

```
Agent playground: https://ai.azure.com/.../agents/compliance-hosted-agent
Agent endpoint:   https://kenidinghk-5470-resource.services.ai.azure.com/
                  api/projects/kenidinghk-5470/agents/compliance-hosted-agent/
                  endpoint/protocols/openai/responses?api-version=v1
```

### Prueba local antes de deploy

```powershell
cd foundry-hosted\compliance_hosted_agent
pip install -r requirements.txt
python main.py
```

```powershell
# En otra terminal
curl -X POST http://localhost:8088/responses `
  -H "Content-Type: application/json" `
  -d '{"input": "Analiza el riesgo del cliente 4", "stream": false}'
```

### Endpoints del HostedAgent

| Endpoint | Metodo | Descripcion |
|---|---|---|
| `/readiness` | GET | Health check — debe retornar HTTP 200 para que Foundry conecte |
| `/responses` | POST | Invocacion del agente — body: `{"input": "...", "stream": false}` |

### Uso desde MAF FoundryAgent (post-deploy)

Una vez desplegado, se puede llamar desde cualquier cliente MAF sin servidor local:

```python
from agent_framework.foundry import FoundryAgent
from azure.identity import AzureCliCredential

agent = FoundryAgent(
    project_endpoint="https://kenidinghk-5470-resource.services.ai.azure.com/api/projects/kenidinghk-5470",
    agent_name="compliance-hosted-agent",  # sin agent_version = HostedAgent
    credential=AzureCliCredential(),
)
result = await agent.run("Analiza el riesgo del cliente 4")
```

### Actualizaciones

Cada vez que cambias el codigo, basta con re-deploy (sin re-provision):

```powershell
azd deploy
```

---

## Variables de entorno en el container

El container recibe estas variables de `agent.yaml` y del entorno azd:

| Variable | Valor | Fuente |
|---|---|---|
| `FOUNDRY_PROJECT_ENDPOINT` | endpoint del proyecto | `.azure/.env` (azd) |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | `gpt-5.4-nano` | `agent.yaml` |
| `PORT` | `8088` | default en main.py |

`main.py` lee `AZURE_AI_MODEL_DEPLOYMENT_NAME` con fallback a `FOUNDRY_MODEL` para
compatibilidad con entorno local.