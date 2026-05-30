"""MAF Orchestrator settings."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


class Settings:
    def __init__(self):
        self.foundry_project_endpoint: str = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
        self.foundry_model: str = os.getenv("FOUNDRY_MODEL", os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME", "gpt-4o-mini"))
        self.account_agent_url: str = os.getenv("ACCOUNT_AGENT_URL", "http://localhost:8002")
        self.compliance_agent_url: str = os.getenv("COMPLIANCE_AGENT_URL", "http://localhost:8001")
        self.a2a_port: int = int(os.getenv("MAF_ORCHESTRATOR_PORT", "8003"))
        self.a2a_url: str = os.getenv("MAF_ORCHESTRATOR_URL", f"http://localhost:{self.a2a_port}")