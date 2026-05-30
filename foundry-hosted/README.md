# Foundry Hosted Deployment - Demonstration

Shows how to deploy existing agents to Microsoft Foundry Agent Service without
altering the current flow or logic.

## Two deployment patterns

### 1. Account Agent as Foundry PromptAgent

Register the Account Agent's tools and instructions as a named PromptAgentDefinition
in Foundry. The agent definition (model + instructions + tool schemas) lives in
Foundry; tool execution still runs locally.

**Step 1 - Provision (run once):**
```
cd poc-maf-adk-a2a
.venv/Scripts/activate
python foundry-hosted/provision_account_agent.py
```

**Step 2 - Use via MAF FoundryAgent:**
```
python foundry-hosted/use_account_agent_maf.py
```

`use_account_agent_maf.py` shows two call patterns:
- `FoundryAgent` (MAF) - same `.run()` interface as the inline `Agent()` in maf-orchestrator
- `openai.responses.create()` (Responses API) - lower-level, framework-agnostic

### 2. Compliance Agent as Foundry HostedAgent

The `compliance_hosted_agent/` directory is a deployment scaffold. When deployed
to Foundry Agent Service, the entire compliance agent (MAF Agent + SQLite tools)
runs inside a Foundry-managed container.

**Local test:**
```
cd foundry-hosted/compliance_hosted_agent
pip install -r requirements.txt
python main.py
# Listening on http://localhost:8088

curl -X POST http://localhost:8088/responses \
  -H "Content-Type: application/json" \
  -d '{"input": "Analiza el riesgo del cliente 4", "stream": false}'
```

**Deploy to Foundry:**
```
winget install Microsoft.Azd
azd ext install azure.ai.agents
cd foundry-hosted/compliance_hosted_agent
azd init
azd env set FOUNDRY_PROJECT_ENDPOINT <your_endpoint>
azd env set FOUNDRY_MODEL <your_model>
azd ai agent deploy
```

After deployment, Foundry assigns the agent a name. Use it with `FoundryAgent`:
```python
from agent_framework.foundry import FoundryAgent
agent = FoundryAgent(
    project_endpoint="...",
    agent_name="compliance-hosted-agent",  # name assigned by Foundry on deploy
    credential=AzureCliCredential(),
)
result = await agent.run("Analiza el riesgo del cliente 4")
```

## Key difference: PromptAgent vs HostedAgent

| | PromptAgent | HostedAgent |
|---|---|---|
| Where definition lives | Foundry (name + version) | Foundry container |
| Where tools run | Caller's process | Inside container |
| Provisioned via | `project.agents.create_version()` | `azd ai agent deploy` |
| Use from MAF | `FoundryAgent(agent_version="1.0")` | `FoundryAgent()` (no version) |
| Scale | N/A | Foundry auto-scales |

## Files

```
foundry-hosted/
  provision_account_agent.py        # Creates PromptAgentDefinition in Foundry
  use_account_agent_maf.py          # Calls it via FoundryAgent + Responses API
  compliance_hosted_agent/
    main.py                         # HostedAgent scaffold (Starlette + MAF Agent)
    requirements.txt                # Container dependencies
```