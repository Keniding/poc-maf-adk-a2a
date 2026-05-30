"""
A2A Server for MAF Orchestrator.

Sequential workflow: AccountAgent → ComplianceAgent → MAF Synthesis (Foundry)
Port 8003.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from agents.orchestrator import create_orchestrator, run_orchestration
from config.settings import Settings


async def create_app():
    settings = Settings()
    workflow = await create_orchestrator(settings)

    agent_card = {
        "name": "MAF Orchestrator",
        "description": "Banking orchestrator using Microsoft Agent Framework — sequential workflow: Account → Compliance → Synthesis",
        "version": "1.0",
        "url": settings.a2a_url,
        "skills": [
            {
                "name": "orchestrate_banking_query",
                "description": "Full banking analysis: account info + AML/KYC compliance + synthesis",
            }
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
            user_query = params.get("input", "")
            try:
                output = await run_orchestration(workflow, user_query)
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"output": output},
                })
            except Exception as exc:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": str(exc)},
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

    print(f"Starting MAF Orchestrator on port {settings.a2a_port}")
    print(f"Agent card: {settings.a2a_url}/.well-known/agent.json")
    print(f"A2A endpoint: {settings.a2a_url}/a2a")
    print(f"Workflow: AccountAgent({settings.account_agent_url}) → ComplianceAgent({settings.compliance_agent_url}) → Foundry({settings.foundry_model})")

    config = uvicorn.Config(app, host="0.0.0.0", port=settings.a2a_port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())