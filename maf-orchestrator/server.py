"""
A2A Server for MAF Orchestrator.

Exposes 3 workflow patterns on port 8003.
Pass "workflow_type" in params to select the pattern:
  - "sequential"   (default) add_chain: account -> compliance -> synthesis
  - "parallel"     fan-out + fan-in: [account || compliance] -> synthesis
  - "conditional"  switch-case: routes by keyword -> account-only | compliance-only | full
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from agents.orchestrator import (
    create_conditional_workflow,
    create_parallel_workflow,
    create_sequential_workflow,
    run_orchestration,
)
from config.settings import Settings


async def create_app():
    settings = Settings()

    workflows = {
        "sequential":  await create_sequential_workflow(settings),
        "parallel":    await create_parallel_workflow(settings),
        "conditional": await create_conditional_workflow(settings),
    }

    agent_card = {
        "name": "MAF Orchestrator",
        "description": (
            "Banking orchestrator using Microsoft Agent Framework WorkflowBuilder. "
            "Supports 3 patterns: sequential (add_chain), "
            "parallel (fan-out + fan-in), conditional (switch-case)."
        ),
        "version": "1.0",
        "url": settings.a2a_url,
        "skills": [
            {
                "name": "orchestrate_sequential",
                "description": "add_chain: account -> compliance -> Foundry synthesis",
            },
            {
                "name": "orchestrate_parallel",
                "description": "fan-out + fan-in: account || compliance -> Foundry synthesis",
            },
            {
                "name": "orchestrate_conditional",
                "description": "switch-case: routes by keyword to account-only, compliance-only, or full analysis",
            },
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
            workflow_type = params.get("workflow_type", "sequential")

            workflow = workflows.get(workflow_type)
            if workflow is None:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": f"Unknown workflow_type '{workflow_type}'. Valid: sequential, parallel, conditional",
                    },
                })

            try:
                output = await run_orchestration(workflow, user_query)
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"output": output, "workflow_type": workflow_type},
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
    print(f"Workflows available: sequential | parallel | conditional")
    print(f"  Account Agent:    {settings.account_agent_url}")
    print(f"  Compliance Agent: {settings.compliance_agent_url}")
    print(f"  Foundry model:    {settings.foundry_model}")

    config = uvicorn.Config(app, host="0.0.0.0", port=settings.a2a_port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())