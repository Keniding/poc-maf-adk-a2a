"""
Compliance Agent - Foundry Hosted Agent.

Deployment: azd provision && azd deploy
Local test: python main.py
  curl -X POST http://localhost:8088/responses \
       -H "Content-Type: application/json" \
       -d '{"input": "Analiza el riesgo del cliente 4", "stream": false}'
"""

import os

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from tools import check_transaction_risk, get_compliance_rules, get_customer_risk_profile

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

# azd sets AZURE_AI_MODEL_DEPLOYMENT_NAME; fallback for local testing
_MODEL = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME") or os.environ.get("FOUNDRY_MODEL", "gpt-4o-mini")

_agent = Agent(
    client=FoundryChatClient(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model=_MODEL,
        credential=DefaultAzureCredential(),
    ),
    name="ComplianceHostedAgent",
    instructions=COMPLIANCE_INSTRUCTIONS,
    tools=[check_transaction_risk, get_compliance_rules, get_customer_risk_profile],
)


async def handle_responses(request: Request) -> JSONResponse:
    """POST /responses — Foundry Responses API protocol."""
    body = await request.json()
    user_input = body.get("input", "")

    if body.get("stream", False):
        return JSONResponse({"error": "stream=true not supported"}, status_code=400)

    result = await _agent.run(user_input)
    return JSONResponse({"output_text": str(result)})


app = Starlette(routes=[
    Route("/responses", handle_responses, methods=["POST"]),
])

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8088"))
    print(f"Compliance Hosted Agent on http://localhost:{port}/responses")
    uvicorn.run(app, host="0.0.0.0", port=port)