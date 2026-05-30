"""
Provision Account Agent as a Foundry PromptAgent.

This script registers the Account Agent's tools and instructions as a named
PromptAgentDefinition in Microsoft Foundry Agent Service. Run it once to
create the agent definition; then call it from any client using agent_name.

What this demonstrates:
  - How to take an existing local agent (Microsoft Agent / OpenAI tool-calling loop)
    and promote it to a named, versioned agent stored in Foundry.
  - The agent definition (model, instructions, tool schemas) lives in Foundry;
    tool execution still runs locally when called via the Responses API.
  - MAF's FoundryAgent can then connect to it by name (no inline Agent() needed).

Usage:
  cd poc-maf-adk-a2a
  .venv/Scripts/activate
  python foundry-hosted/provision_account_agent.py

Prerequisites:
  - az login (AzureCliCredential)
  - FOUNDRY_PROJECT_ENDPOINT set in maf-orchestrator/.env
  - FOUNDRY_MODEL set (model deployment name in your Foundry project)
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "maf-orchestrator"))

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import FunctionTool, PromptAgentDefinition
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "maf-orchestrator" / ".env")

# Tool schemas for the Account Agent's 4 tools.
# These mirror the definitions in microsoft-agent/agents/tools.py.
# Foundry stores them so any client (MAF, REST, SDK) can invoke the agent.
ACCOUNT_AGENT_TOOLS = [
    FunctionTool(
        name="search_customer",
        description="Search for customers by name, email, or phone number.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Name, email, phone or customer ID"},
            },
            "required": ["query"],
        },
        strict=False,
    ),
    FunctionTool(
        name="get_customer_accounts",
        description="Get all bank accounts and balances for a customer.",
        parameters={
            "type": "object",
            "properties": {
                "customer_id": {"type": "integer", "description": "Customer ID"},
            },
            "required": ["customer_id"],
        },
        strict=False,
    ),
    FunctionTool(
        name="get_account_transactions",
        description="Get recent transactions for an account.",
        parameters={
            "type": "object",
            "properties": {
                "account_id": {"type": "integer", "description": "Account ID"},
                "limit": {"type": "integer", "description": "Max transactions to return (default 10)"},
            },
            "required": ["account_id"],
        },
        strict=False,
    ),
    FunctionTool(
        name="search_products",
        description="Search available banking products by category.",
        parameters={
            "type": "object",
            "properties": {
                "product_type": {"type": "string", "description": "Product category filter (optional)"},
            },
            "required": [],
        },
        strict=False,
    ),
]

ACCOUNT_AGENT_INSTRUCTIONS = """\
Eres un especialista bancario de cuentas para Interbank.

Capacidades:
- Buscar clientes por nombre, email o telefono
- Consultar cuentas y balances de clientes
- Revisar historial de transacciones
- Recomendar productos bancarios

Reglas:
- Siempre identifica primero al cliente con search_customer
- Presenta la informacion de forma clara y organizada
- Si encuentras transacciones marcadas, mencionalas pero no hagas analisis de riesgo
- Se profesional y util
- Responde en espanol
"""

AGENT_NAME = "interbank-account-agent"
AGENT_VERSION = "1.0"


def provision_agent() -> str:
    """
    Create or update the Account Agent definition in Foundry.

    Returns the agent version string.

    Flow:
      AIProjectClient.agents.create_version()
        -> Stores PromptAgentDefinition (model + instructions + tool schemas) in Foundry
        -> Returns agent name + version for future references
    """
    project_endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
    foundry_model = os.getenv("FOUNDRY_MODEL", "gpt-4o-mini")

    print(f"Connecting to Foundry: {project_endpoint}")
    print(f"Model deployment: {foundry_model}")

    project = AIProjectClient(
        endpoint=project_endpoint,
        credential=AzureCliCredential(),
    )

    print(f"\nProvisioning agent '{AGENT_NAME}' v{AGENT_VERSION}...")

    agent = project.agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=foundry_model,
            instructions=ACCOUNT_AGENT_INSTRUCTIONS,
            tools=ACCOUNT_AGENT_TOOLS,
        ),
    )

    print(f"Agent provisioned: name={agent.name}, version={agent.version}")
    print(
        f"\nTo call this agent from any client:\n"
        f"  agent_name  = '{agent.name}'\n"
        f"  agent_version = '{agent.version}'\n"
        f"\nSee use_account_agent_maf.py for MAF FoundryAgent usage."
    )
    return agent.version


if __name__ == "__main__":
    version = provision_agent()
    print(f"\nDone. Agent version: {version}")