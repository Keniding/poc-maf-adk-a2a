"""
A2A Server for Microsoft Account Agent.

This server exposes the FoundryAgent v2 via A2A protocol on port 8002.

A2A Protocol Implementation:
- Uses A2aAgentExecutor from agent-framework
- Publishes AgentCard at /.well-known/agent.json
- Supports JSON-RPC methods: agent.invoke, agent.stream, agent.cancel
- Manages task queue and lifecycle automatically
- Enables cross-framework communication with any A2A client

Architecture:
- FoundryAgent connects to Azure AI Foundry for LLM execution
- Local tools registered and executed when called by remote agent
- A2aAgentExecutor wraps agent and handles A2A protocol
- Starlette ASGI app serves HTTP/JSON-RPC endpoints
"""

import asyncio
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

from agent_framework.a2a import A2aAgentExecutor
from starlette.applications import Starlette
from starlette.routing import Mount

from agents.account_agent import create_account_agent
from config.settings import Settings


async def create_app():
    """Create A2A server application."""
    settings = Settings()

    # Create agent
    agent = await create_account_agent(settings)

    # Create A2A executor
    executor = A2aAgentExecutor(
        agent=agent,
        agent_id="account-agent",
        name="Account Agent",
        description="Banking account specialist - queries customer data, balances, and transactions",
    )

    # Create Starlette app with A2A routes
    app = Starlette(
        routes=[
            Mount("/", app=executor.as_asgi()),
        ],
    )

    return app, settings


async def main():
    """Run A2A server."""
    import uvicorn

    app, settings = await create_app()

    print(f"Starting Microsoft Account Agent A2A Server on port {settings.a2a_port}")
    print(f"Agent card: http://localhost:{settings.a2a_port}/.well-known/agent.json")

    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=settings.a2a_port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())