"""
Compliance Agent - Google ADK for AML/KYC risk analysis.

This agent:
- Uses Google ADK (Agent Development Kit)
- Exposes via A2A protocol for cross-framework communication
- Analyzes suspicious transactions and generates compliance reports

A2A Protocol:
- AgentCard published at /.well-known/agent.json
- Supports streaming responses
- Skills-based capability discovery
"""

from google.adk.agents.llm_agent import Agent

from agents.tools import (
    check_transaction_risk,
    get_compliance_rules,
    get_customer_risk_profile,
)
from config.settings import Settings

COMPLIANCE_AGENT_INSTRUCTIONS = """\
You are a compliance and anti-money laundering (AML) specialist for Interbank.

Capabilities:
- Analyze customer transaction risk
- Evaluate risk profiles
- Verify AML/KYC compliance rules
- Generate alert reports

Rules:
- Always start by getting the customer risk profile using get_customer_risk_profile
- Then check transactions for potential alerts using check_transaction_risk
- If risk_score > 70, mark as HIGH RISK
- If you detect structuring patterns (multiple transactions near $10,000), alert immediately
- Include relevant compliance rules in your analysis using get_compliance_rules
- Be precise and technical in your reports
- Respond in Spanish
"""


def create_compliance_agent(settings: Settings | None = None):
    """
    Create Compliance Agent using Google ADK.

    This agent will be exposed via A2A protocol with:
    - AgentCard at /.well-known/agent.json
    - Streaming support
    - Skills discovery

    Args:
        settings: Configuration settings

    Returns:
        Google ADK Agent instance configured for A2A
    """
    if settings is None:
        settings = Settings()

    settings.validate()

    # Create agent with ADK
    # The to_a2a() helper will automatically:
    # 1. Generate AgentCard with skills
    # 2. Set up task queue and executor
    # 3. Configure streaming support
    # 4. Publish agent card at /.well-known/agent.json
    agent = Agent(
        name="compliance_agent",
        model=settings.google_model,
        description="AML/KYC compliance specialist for banking risk analysis.",
        instruction=COMPLIANCE_AGENT_INSTRUCTIONS,
        tools=[
            check_transaction_risk,
            get_compliance_rules,
            get_customer_risk_profile,
        ],
    )

    return agent


def create_compliance_agent_a2a_app(settings: Settings | None = None):
    """
    Create A2A Starlette application that exposes the Compliance Agent.

    Uses to_a2a() from Google ADK to auto-generate the AgentCard
    and mount the complete A2A server.

    Args:
        settings: Configuration settings

    Returns:
        Starlette application
    """
    if settings is None:
        settings = Settings()

    settings.validate()

    from google.adk.a2a.utils.agent_to_a2a import to_a2a

    agent = create_compliance_agent(settings)

    app = to_a2a(
        agent,
        host="localhost",
        port=settings.a2a_port,
        protocol="http",
    )

    return app