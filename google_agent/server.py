"""
A2A Server for Google Compliance Agent.

Exposes compliance_agent via A2A protocol on port 8001:
- GET  /.well-known/agent.json  -> AgentCard (discovery)
- POST /a2a                     -> JSON-RPC (agent.invoke)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from agent import root_agent
from config.settings import Settings


async def run_agent(runner: InMemoryRunner, user_message: str) -> str:
    """Run agent and collect the final text response."""
    session = await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id="a2a_user",
    )

    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_message)],
    )

    final_text = ""
    async for event in runner.run_async(
        user_id="a2a_user",
        session_id=session.id,
        new_message=content,
    ):
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    final_text += part.text

    return final_text or "No response generated."


async def create_app():
    """Create A2A Starlette application."""
    settings = Settings()

    runner = InMemoryRunner(
        agent=root_agent,
        app_name="compliance_agent",
    )

    agent_card = {
        "name": "Compliance Agent",
        "description": "AML/KYC compliance specialist for banking risk analysis",
        "version": "1.0",
        "url": settings.a2a_url,
        "skills": [
            {"name": "get_customer_risk_profile", "description": "Get customer risk score and profile"},
            {"name": "check_transaction_risk", "description": "Analyze transactions for AML patterns"},
            {"name": "get_compliance_rules", "description": "Get AML/KYC compliance rules"},
        ],
    }

    async def handle_agent_card(request: Request):
        return JSONResponse(agent_card)

    async def handle_a2a(request: Request):
        body = await request.json()
        method = body.get("method")
        params = body.get("params", {})
        req_id = body.get("id", 1)

        if method == "agent.invoke":
            input_text = params.get("input", "")
            try:
                output = await run_agent(runner, input_text)
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"output": output},
                })
            except Exception as e:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": str(e)},
                })

        return JSONResponse({
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method '{method}' not supported"},
        })

    app = Starlette(routes=[
        Route("/.well-known/agent.json", handle_agent_card),
        Route("/a2a", handle_a2a, methods=["POST"]),
    ])

    return app, settings


async def main():
    import uvicorn

    app, settings = await create_app()

    print(f"Starting Google Compliance Agent on port {settings.a2a_port}")
    print(f"Agent card: {settings.a2a_url}/.well-known/agent.json")
    print(f"A2A endpoint: {settings.a2a_url}/a2a")
    print(f"Model: {settings.google_model}")

    config = uvicorn.Config(app, host="0.0.0.0", port=settings.a2a_port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())