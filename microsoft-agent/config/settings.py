"""Microsoft Agent - Configuration."""

import os
from dataclasses import dataclass, field
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

CredentialType = Literal["AzureCliCredential", "ManagedIdentityCredential", "DefaultAzureCredential"]


@dataclass
class Settings:
    """Azure AI Foundry settings."""

    # Azure AI Foundry
    foundry_project_endpoint: str = field(
        default_factory=lambda: os.getenv("FOUNDRY_PROJECT_ENDPOINT", "")
    )
    foundry_model: str = field(
        default_factory=lambda: os.getenv("FOUNDRY_MODEL_DEPLOYMENT_NAME", "gpt-4o")
    )
    foundry_agent_name: str = field(
        default_factory=lambda: os.getenv("FOUNDRY_AGENT_NAME", "account-agent")
    )

    # Auth: API key (simple) or Azure credential (recommended)
    foundry_api_key: str = field(
        default_factory=lambda: os.getenv("FOUNDRY_API_KEY", "")
    )
    credential_type: CredentialType = field(
        default_factory=lambda: os.getenv("AZURE_CREDENTIAL_TYPE", "AzureCliCredential")  # type: ignore[return-value]
    )
    managed_identity_client_id: str = field(
        default_factory=lambda: os.getenv("AZURE_MANAGED_IDENTITY_CLIENT_ID", "")
    )

    # A2A Server
    a2a_port: int = field(
        default_factory=lambda: int(os.getenv("ACCOUNT_A2A_PORT", "8002"))
    )

    @property
    def a2a_url(self) -> str:
        return f"http://localhost:{self.a2a_port}"

    def validate(self):
        if not self.foundry_project_endpoint:
            raise ValueError("FOUNDRY_PROJECT_ENDPOINT is required.")
        if not self.foundry_api_key and self.credential_type == "AzureCliCredential":
            import subprocess
            result = subprocess.run(["az", "account", "show"], capture_output=True)
            if result.returncode != 0:
                raise ValueError(
                    "No FOUNDRY_API_KEY set and Azure CLI is not logged in. "
                    "Run 'az login' or set FOUNDRY_API_KEY in .env"
                )


def get_azure_credential(settings: Settings | None = None):
    """Get Azure credential based on configuration."""
    if settings is None:
        settings = Settings()

    from azure.identity import AzureCliCredential, DefaultAzureCredential, ManagedIdentityCredential

    match settings.credential_type:
        case "AzureCliCredential":
            return AzureCliCredential()
        case "ManagedIdentityCredential":
            kwargs = {}
            if settings.managed_identity_client_id:
                kwargs["client_id"] = settings.managed_identity_client_id
            return ManagedIdentityCredential(**kwargs)
        case "DefaultAzureCredential":
            return DefaultAzureCredential()
        case _:
            raise ValueError(f"Unsupported credential type: {settings.credential_type}")