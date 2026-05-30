"""
Account Agent - Microsoft Agent Framework with FoundryAgent v2.

This agent:
- Uses Microsoft Agent Framework with FoundryAgent v2
- Connects to published agent in Azure AI Foundry
- Exposes via A2A protocol for cross-framework communication
- Handles customer queries, accounts, and transactions

FoundryAgent v2:
- Agent definition (instructions, model) hosted in Azure AI Foundry
- Tools implemented locally and provided at runtime
- Server-side execution with local tool callbacks

A2A Protocol:
- AgentCard published at /.well-known/agent.json via A2aAgentExecutor
- Supports streaming responses
- Skills-based capability discovery
- Task queue and executor managed by agent-framework
"""

from agent_framework.foundry import FoundryAgent

from agents.tools import (
    get_account_transactions,
    get_customer_accounts,
    search_customer,
    search_products,
)
from config.settings import Settings, get_azure_credential

ACCOUNT_AGENT_TOOLS = [
    search_customer,
    get_customer_accounts,
    get_account_transactions,
    search_products,
]


async def create_account_agent(settings: Settings | None = None):
    """
    Create Account Agent using FoundryAgent v2.

    This agent will be exposed via A2A protocol through A2aAgentExecutor in server.py.

    FoundryAgent v2 Pattern:
    - Agent definition (instructions, model) published in Azure AI Foundry
    - Tools implemented locally and registered at runtime
    - Server-side LLM execution with local tool callbacks

    A2A Integration:
    - Wrapped by A2aAgentExecutor in server.py
    - AgentCard auto-generated from agent metadata
    - Supports streaming and task cancellation
    - Skills derived from tool definitions

    Args:
        settings: Configuration settings

    Returns:
        FoundryAgent instance ready for A2A exposure
    """
    if settings is None:
        settings = Settings()

    credential = get_azure_credential(settings)

    agent = FoundryAgent(
        project_endpoint=settings.foundry_project_endpoint,
        agent_name=settings.foundry_agent_name,
        agent_version=settings.foundry_agent_version,
        credential=credential,
        tools=ACCOUNT_AGENT_TOOLS,
        description="Banking account specialist for customer queries, balances, and transactions.",
    )

    return agent


async def publish_agent(settings: Settings | None = None):
    """
    Publish Account Agent to Azure AI Foundry.

    Converts local agent definition to PromptAgentDefinition
    and versions it in Foundry for consumption via FoundryAgent v2.

    Args:
        settings: Configuration settings

    Returns:
        Created agent version
    """
    if settings is None:
        settings = Settings()

    from agent_framework import Agent
    from agent_framework.foundry import FoundryChatClient, to_prompt_agent
    from azure.ai.projects.aio import AIProjectClient
    from azure.identity.aio import AzureCliCredential

    INSTRUCTIONS = """\
You are a banking account specialist for Interbank.

Capabilities:
- Search customers by name, email, or phone
- Query customer accounts and balances
- Review transaction history
- Recommend banking products

Rules:
- Always identify the customer first using search_customer
- Present information clearly and organized
- If you find flagged transactions, mention them but do not perform risk analysis (compliance agent handles that)
- Be professional and helpful
- Respond in Spanish
"""

    async with AzureCliCredential() as credential:
        client = FoundryChatClient(
            project_endpoint=settings.foundry_project_endpoint,
            model=settings.foundry_model,
            credential=credential,
        )

        agent = Agent(
            client=client,
            name=settings.foundry_agent_name,
            description="Banking account specialist for customer queries.",
            instructions=INSTRUCTIONS,
            tools=ACCOUNT_AGENT_TOOLS,
            default_options={"temperature": 0.3, "top_p": 0.95},
        )

        definition = to_prompt_agent(agent)

        async with AIProjectClient(
            endpoint=settings.foundry_project_endpoint,
            credential=credential,
        ) as project_client:
            created = await project_client.agents.create_version(
                agent_name=agent.name,
                definition=definition,
                description=agent.description,
            )
            print(f"Published: {created.name} v{created.version}")
            return created


if __name__ == "__main__":
    import asyncio

    # Example: Publish agent to Foundry
    asyncio.run(publish_agent())
