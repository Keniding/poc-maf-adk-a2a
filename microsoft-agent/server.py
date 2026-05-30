"""
A2A Server for Microsoft Account Agent.

Exposes AccountAgent via A2A protocol on port 8002:
- GET  /.well-known/agent.json  -> AgentCard (discovery)
- POST /a2a                     -> JSON-RPC (agent.invoke)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from agents.account_agent import create_account_agent
from config.settings import Settings


def _build_agent_card(settings: Settings) -> dict:
    return {
        "name": "Account Agent",
        "description": "Banking account specialist - queries customer data, balances, and transactions",
        "version": "1.0",
        "url": settings.a2a_url,
        "skills": [
            {"name": "search_customer", "description": "Search customers by name, email, or phone"},
            {"name": "get_customer_accounts", "description": "Get customer accounts and balances"},
            {"name": "get_account_transactions", "description": "Get account transaction history"},
            {"name": "search_products", "description": "Search available banking products"},
        ],
    }


async def create_app():
    """Create A2A Starlette application."""
    settings = Settings()
    agent = await create_account_agent(settings)
    agent_card = _build_agent_card(settings)

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
                output = await agent.run(input_text)
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

    print(f"Starting Microsoft Account Agent on port {settings.a2a_port}")
    print(f"Agent card: {settings.a2a_url}/.well-known/agent.json")
    print(f"A2A endpoint: {settings.a2a_url}/a2a")
    print(f"Model: {settings.foundry_model}")

    config = uvicorn.Config(app, host="0.0.0.0", port=settings.a2a_port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())