"""
Use the provisioned Foundry Account Agent via MAF FoundryAgent.

After running provision_account_agent.py, the Account Agent definition lives
in Foundry. This script shows two ways to call it:

  1. MAF FoundryAgent — same run() interface as the inline Agent used in the
     existing maf-orchestrator workflow. Drop-in replacement.

  2. Foundry Responses API (direct) — shows the lower-level call using
     openai.responses.create() with an agent_reference.

Key point: the tool execution (SQLite queries) still runs locally here.
Foundry stores the agent definition; we handle tool calls in the loop.

Prerequisites:
  - provision_account_agent.py must have been run first
  - az login (AzureCliCredential)
  - FOUNDRY_PROJECT_ENDPOINT in maf-orchestrator/.env

Usage:
  cd poc-maf-adk-a2a
  .venv/Scripts/activate
  python foundry-hosted/use_account_agent_maf.py
"""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "microsoft-agent"))
sys.path.insert(0, str(Path(__file__).parent.parent / "maf-orchestrator"))

from azure.identity import AzureCliCredential
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "maf-orchestrator" / ".env")

# Tool implementations (same functions used by the local agent)
from agents.tools import (
    get_account_transactions,
    get_customer_accounts,
    search_customer,
    search_products,
)

AGENT_NAME = "interbank-account-agent"
AGENT_VERSION = "1.0"


# ---------------------------------------------------------------------------
# Option 1: MAF FoundryAgent (recommended for MAF-based workflows)
# ---------------------------------------------------------------------------

async def demo_maf_foundry_agent():
    """
    Call the Foundry-registered agent using MAF's FoundryAgent.

    FoundryAgent connects to the agent definition stored in Foundry by name.
    - agent_version identifies the PromptAgent version.
    - tools receives the local Python functions; MAF handles the tool-call loop.
    - Same .run() interface as the inline Agent() used in maf-orchestrator.

    This can replace the AccountFetchExecutor's _call_a2a() call with a direct
    FoundryAgent call — no A2A HTTP hop needed.
    """
    from agent_framework.foundry import FoundryAgent

    print("\n--- Option 1: MAF FoundryAgent ---")
    project_endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]

    agent = FoundryAgent(
        project_endpoint=project_endpoint,
        agent_name=AGENT_NAME,
        agent_version=AGENT_VERSION,
        credential=AzureCliCredential(),
        tools=[search_customer, get_customer_accounts, get_account_transactions, search_products],
    )

    query = "Dame las cuentas y ultimas transacciones del cliente con ID 1"
    print(f"Query: {query}")
    result = await agent.run(query)
    print(f"Response:\n{result}")


# ---------------------------------------------------------------------------
# Option 2: Direct Responses API call (framework-agnostic)
# ---------------------------------------------------------------------------

def _execute_tool(name: str, arguments: str) -> str:
    """Execute a tool call by name with JSON-serialized arguments."""
    tool_map = {
        "search_customer": search_customer,
        "get_customer_accounts": get_customer_accounts,
        "get_account_transactions": get_account_transactions,
        "search_products": search_products,
    }
    func = tool_map.get(name)
    if func is None:
        return f"Error: tool '{name}' not found"
    try:
        args = json.loads(arguments)
        return str(func(**args))
    except Exception as exc:
        return f"Error executing {name}: {exc}"


def demo_responses_api():
    """
    Call the Foundry-registered agent via the Responses API directly.

    This is the lower-level pattern — useful when you need framework-agnostic
    access or want to inspect tool calls step by step.

    The Responses API supports multi-turn by chaining previous_response_id.
    Tool calls must be handled in a client-side loop (same as OpenAI function calling).
    """
    from azure.ai.projects import AIProjectClient

    print("\n--- Option 2: Foundry Responses API (direct) ---")
    project_endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]

    project = AIProjectClient(
        endpoint=project_endpoint,
        credential=AzureCliCredential(),
    )
    openai = project.get_openai_client()

    query = "Busca al cliente con ID 2 y muestra sus cuentas"
    print(f"Query: {query}")

    # Agentic loop: keep processing until no more tool calls
    response = openai.responses.create(
        extra_body={
            "agent_reference": {
                "name": AGENT_NAME,
                "type": "agent_reference",
            }
        },
        input=query,
    )

    # Handle tool calls if present
    while response.status == "requires_action" or any(
        getattr(item, "type", None) == "function_call" for item in (response.output or [])
    ):
        tool_outputs = []
        for item in response.output or []:
            if getattr(item, "type", None) == "function_call":
                print(f"  [Tool call] {item.name}({item.arguments})")
                output = _execute_tool(item.name, item.arguments)
                tool_outputs.append({
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": output,
                })

        if not tool_outputs:
            break

        # Submit tool outputs and continue
        response = openai.responses.create(
            extra_body={
                "agent_reference": {
                    "name": AGENT_NAME,
                    "type": "agent_reference",
                }
            },
            previous_response_id=response.id,
            input=tool_outputs,
        )

    print(f"Response:\n{response.output_text}")


async def main():
    print("=" * 70)
    print("Account Agent via Foundry — demonstration")
    print("Agent definition stored in Foundry, tools executed locally")
    print("=" * 70)

    await demo_maf_foundry_agent()
    print()
    demo_responses_api()


if __name__ == "__main__":
    asyncio.run(main())