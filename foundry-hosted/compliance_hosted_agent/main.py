"""
Compliance Agent - Foundry Hosted Agent scaffold.

This is the entry point for deploying the compliance agent as a HostedAgent
in Microsoft Foundry Agent Service (deployed via `azd ai agent deploy`).

How a Hosted Agent differs from a PromptAgent:
  - PromptAgent: definition (instructions + tools) stored in Foundry, tool
    execution runs in the calling client's process.
  - HostedAgent: the entire agent code runs inside Foundry's managed container.
    Foundry handles scaling, lifecycle, and telemetry. No client-side tool loop.

The server exposes POST /responses — the Foundry Responses API protocol.
Foundry Agent Service calls this endpoint when the hosted agent is invoked
from the playground, the SDK, or another agent via agent_reference.

Deployment steps:
  1. Install azd and the AI agents extension:
       winget install Microsoft.Azd
       azd ext install azure.ai.agents        # version 0.1.27-preview or later
  2. From this directory, initialize:
       azd init
  3. Configure environment:
       azd env set FOUNDRY_PROJECT_ENDPOINT <your_endpoint>
       azd env set FOUNDRY_MODEL <your_model_deployment>
  4. Deploy:
       azd ai agent deploy

Local testing (runs on http://localhost:8088):
  python main.py
  curl -X POST http://localhost:8088/responses \
       -H "Content-Type: application/json" \
       -d '{"input": "Analiza el riesgo del cliente 4", "stream": false}'

The Foundry Toolkit VS Code extension (Foundry Toolkit: Deploy Hosted Agent)
also deploys this scaffold and provides an Agent Inspector for local debugging.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "google_agent"))

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from agents.tools import (
    check_transaction_risk,
    get_compliance_rules,
    get_customer_risk_profile,
)


COMPLIANCE_INSTRUCTIONS = """\
Eres un especialista en compliance y anti-lavado de dinero (AML) para Interbank.

Capacidades:
- Analizar perfil de riesgo del cliente
- Revisar transacciones en busca de patrones sospechosos
- Verificar reglas AML/KYC
- Generar reportes de alertas

Reglas:
- Siempre inicia obteniendo el perfil de riesgo con get_customer_risk_profile
- Luego verifica transacciones con check_transaction_risk
- Si risk_score > 70, marca como ALTO RIESGO
- Si detectas patrones de estructuracion, alerta inmediatamente
- Incluye reglas de compliance relevantes usando get_compliance_rules
- Se preciso y tecnico en tus reportes
- Responde en espanol
"""


def _build_agent() -> Agent:
    """
    Create the compliance agent backed by Foundry's hosted infrastructure.

    When running as a HostedAgent:
    - FoundryChatClient reads FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_MODEL from env.
    - DefaultAzureCredential uses the container's managed identity (no az login needed).
    - Tools run inside the container alongside this process.
    """
    return Agent(
        client=FoundryChatClient(
            project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            model=os.environ.get("FOUNDRY_MODEL", "gpt-4o-mini"),
            credential=DefaultAzureCredential(),
        ),
        name="ComplianceHostedAgent",
        instructions=COMPLIANCE_INSTRUCTIONS,
        tools=[
            check_transaction_risk,
            get_compliance_rules,
            get_customer_risk_profile,
        ],
    )


_agent = _build_agent()


async def handle_responses(request: Request) -> JSONResponse:
    """
    POST /responses — Foundry Responses API protocol.

    Foundry Agent Service (and the VS Code Inspector) call this endpoint.
    Body: {"input": "<user message>", "stream": false}
    Response: {"output_text": "<agent response>"}
    """
    body = await request.json()
    user_input = body.get("input", "")
    stream = body.get("stream", False)

    if stream:
        # Streaming not implemented in this scaffold.
        # For streaming, use starlette.responses.StreamingResponse
        # with an async generator yielding SSE events.
        return JSONResponse({"error": "stream=true not supported in this scaffold"}, status_code=400)

    result = await _agent.run(user_input)
    return JSONResponse({"output_text": str(result)})


app = Starlette(routes=[
    Route("/responses", handle_responses, methods=["POST"]),
])


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8088"))
    print(f"Compliance Hosted Agent running on http://localhost:{port}")
    print("Endpoint: POST /responses")
    print(f'Test: curl -X POST http://localhost:{port}/responses '
          '-H "Content-Type: application/json" '
          '-d \'{"input": "Analiza el riesgo del cliente 4", "stream": false}\'')

    uvicorn.run(app, host="0.0.0.0", port=port)