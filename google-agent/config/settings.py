"""Google ADK Agent - Configuration."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Google ADK settings."""

    # Google AI
    google_api_key: str = field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY", "")
    )
    google_model: str = field(
        default_factory=lambda: os.getenv("GOOGLE_MODEL", "gemini-flash-latest")
    )

    # A2A Server
    a2a_port: int = field(
        default_factory=lambda: int(os.getenv("COMPLIANCE_A2A_PORT", "8001"))
    )

    @property
    def a2a_url(self) -> str:
        return f"http://localhost:{self.a2a_port}"

    def validate(self):
        """Validate required settings."""
        if not self.google_api_key:
            raise ValueError(
                "GOOGLE_API_KEY is required. "
                "Get your API key from https://aistudio.google.com/apikey"
            )