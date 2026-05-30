"""Google ADK Compliance Agent - AML/KYC risk analysis."""

import sys
from pathlib import Path

# Add paths for local imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir.parent / "shared"))

try:
    from agent import root_agent
    __all__ = ["root_agent"]
except ImportError:
    # Fallback if running from different context
    __all__ = []