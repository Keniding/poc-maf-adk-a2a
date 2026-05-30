"""
A2A Server for Google Compliance Agent.

This server exposes the Google ADK Agent via A2A protocol on port 8001.

A2A Protocol Implementation:
- Uses to_a2a() helper from google.adk.a2a.utils
- Automatically generates AgentCard at /.well-known/agent.json
- Supports JSON-RPC methods: agent.invoke, agent.stream, agent.cancel
- Creates task queue and executor automatically
- Enables cross-framework communication with any A2A client

Architecture:
- Google ADK Agent executes locally with Gemini models
- to_a2a() helper wraps agent and creates Starlette ASGI app
- All A2A protocol components auto-configured
- Tools executed locally when called by agent
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))

import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a

from agent import root_agent
from config.settings import Settings


def main():
    """Run A2A server."""
    settings = Settings()
    settings.validate()

    # Create A2A app using Google ADK's to_a2a() helper
    # This automatically:
    # - Generates AgentCard at /.well-known/agent.json
    # - Sets up task queue and executor
    # - Configures streaming support
    # - Publishes skills from agent tools
    app = to_a2a(
        root_agent,
        host="localhost",
        port=settings.a2a_port,
        protocol="http",
    )

    print(f"Starting Google Compliance Agent A2A Server on port {settings.a2a_port}")
    print(f"Agent card: http://localhost:{settings.a2a_port}/.well-known/agent.json")
    print(f"Using model: {settings.google_model}")
    print(f"\nADK commands available:")
    print(f"  adk run google_agent")
    print(f"  adk web --port 8000")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.a2a_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()