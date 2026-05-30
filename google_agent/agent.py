"""
ADK Agent - Compliance Agent for AML/KYC risk analysis.

This is the main agent file following Google ADK conventions.
The root_agent defined here enables:
- Running with `adk run google_agent`
- Testing with `adk web` interface
- Exposure via A2A protocol (see server.py)
"""

import sys
from pathlib import Path

# Add paths for local imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir.parent / "shared"))

from google.adk.agents.llm_agent import Agent

from agents.tools import (
    check_transaction_risk,
    get_compliance_rules,
    get_customer_risk_profile,
)
from config.settings import Settings

# Agent instructions
COMPLIANCE_AGENT_INSTRUCTIONS = """\
You are a compliance and anti-money laundering (AML) specialist for Interbank.

Capabilities:
- Analyze customer transaction risk
- Evaluate risk profiles
- Verify AML/KYC compliance rules
- Generate alert reports

Available tools (use EXACTLY these names):
- get_customer_risk_profile(customer_id: int) -> get risk score and account summary
- check_transaction_risk(customer_id: int, days: int) -> analyze recent transactions for AML patterns
- get_compliance_rules(category: str) -> retrieve AML/KYC rules

Rules:
- Always start by calling get_customer_risk_profile with the customer_id
- Then call check_transaction_risk with the customer_id
- If risk_score > 70, mark as HIGH RISK
- If you detect structuring patterns (multiple transactions near $10,000), alert immediately
- Include relevant compliance rules using get_compliance_rules
- Be precise and technical in your reports
- Respond in Spanish
"""


def _get_model():
    """Get model from settings, with fallback."""
    try:
        settings = Settings()
        return settings.google_model
    except Exception:
        # Fallback if .env not configured
        return "gemini-3-flash-preview"


# Root agent definition (required by ADK)
root_agent = Agent(
    model=_get_model(),
    name='compliance_agent',
    description="AML/KYC compliance specialist for banking risk analysis.",
    instruction=COMPLIANCE_AGENT_INSTRUCTIONS,
    tools=[
        get_customer_risk_profile,
        check_transaction_risk,
        get_compliance_rules,
    ],
)