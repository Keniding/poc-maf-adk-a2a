"""Microsoft Agent Framework - Configuration."""

import os
from dataclasses import dataclass, field
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

CredentialType = Literal[
    "AzureCliCredential",
    "ManagedIdentityCredential",
    "DefaultAzureCredential",
]


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
    foundry_agent_version: str = field(
        default_factory=lambda: os.getenv("FOUNDRY_AGENT_VERSION", "1.0")
    )

    # Identity
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


def get_azure_credential(settings: Settings | None = None):
    """Get Azure credential based on configuration."""
    if settings is None:
        settings = Settings()

    from azure.identity import (
        AzureCliCredential,
        DefaultAzureCredential,
        ManagedIdentityCredential,
    )

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
