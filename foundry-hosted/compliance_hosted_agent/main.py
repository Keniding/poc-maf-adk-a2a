"""
Compliance Agent - Foundry Hosted Agent.

Deployment: azd provision && azd deploy
Local test: python main.py
  # Non-streaming
  curl -X POST http://localhost:8088/responses \
       -H "Content-Type: application/json" \
       -d '{"input": "Analiza el riesgo del cliente 4", "stream": false}'
  # Streaming
  curl -X POST http://localhost:8088/responses \
       -H "Content-Type: application/json" \
       -d '{"input": "Analiza el riesgo del cliente 4", "stream": true}'
"""

import json
import os
from collections.abc import AsyncIterator

from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from azure.identity import DefaultAzureCredential
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
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


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _stream_agent(user_input: str) -> AsyncIterator[str]:
    """Run agent and wrap the response as SSE events for Foundry streaming protocol.

    FoundryChatClient has a known issue with stream=True (passes dicts where Message
    objects are expected). We run non-streaming internally and emit the complete
    response as a single SSE chunk so the Foundry playground works correctly.
    """
    result = await _agent.run(user_input)
    text = str(result)
    yield _sse("response.output_text.delta", {"delta": text})
    yield _sse("response.completed", {"output_text": text})
    yield "data: [DONE]\n\n"


async def handle_readiness(request: Request) -> JSONResponse:
    """GET /readiness — Foundry health check. Must return HTTP 200."""
    return JSONResponse({"status": "ready"})


async def handle_responses(request: Request) -> StreamingResponse | JSONResponse:
    """POST /responses — Foundry Responses API protocol."""
    body = await request.json()
    user_input = body.get("input", "")

    if body.get("stream", False):
        return StreamingResponse(
            _stream_agent(user_input),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    result = await _agent.run(user_input)
    return JSONResponse({"output_text": str(result)})


app = Starlette(routes=[
    Route("/readiness", handle_readiness, methods=["GET"]),
    Route("/responses", handle_responses, methods=["POST"]),
])

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8088"))
    print(f"Compliance Hosted Agent on http://localhost:{port}/responses")
    uvicorn.run(app, host="0.0.0.0", port=port)