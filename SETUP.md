# Setup Instructions - Modular Architecture

This POC has been restructured into **separate, independent modules**:

- `microsoft-agent/` - Microsoft Agent Framework with Azure AI Foundry
- `google-agent/` - Google ADK with Google Gemini
- `shared/` - Shared database and resources
- `demo/` - A2A orchestration demonstration

Each module has its own virtual environment, dependencies, and configuration. They communicate via the A2A protocol over HTTP.

## Why Separate Modules?

1. **Dependency Isolation**: Each framework has its own requirements
2. **Easy Presentation**: Clear separation of concerns
3. **Independent Development**: Work on each module separately
4. **Production Ready**: Each can be deployed independently

## Module Overview

| Module | Framework | Environment | Port | Purpose |
|--------|-----------|-------------|------|---------|
| microsoft-agent | Agent Framework 1.7.0 | `.venv` | 8002 | Account queries |
| google-agent | Google ADK 2.1.0 | `.venv-google` | 8001 | Compliance/risk |
| demo | - | Either | - | Orchestration |

## Installation Options

### Recommended: Separate Virtual Environments

Create separate environments for each framework:

**Google ADK Environment:**
```bash
# Create and activate Google environment
uv venv .venv-google
.venv-google\Scripts\activate  # Windows
source .venv-google/bin/activate  # Linux/Mac

# Install dependencies
uv sync
uv pip install -r requirements-google.txt
```

**Microsoft Agent Framework Environment:**
```bash
# Create and activate Microsoft environment (in a new terminal)
uv venv .venv-microsoft
.venv-microsoft\Scripts\activate  # Windows
source .venv-microsoft/bin/activate  # Linux/Mac

# Install dependencies
uv sync
uv pip install --prerelease=allow -r requirements-microsoft.txt
```

### Alternative: Single Environment (Switch as Needed)

If you prefer one environment, switch between frameworks:

**For Google ADK:**
```bash
uv sync
uv pip install -r requirements-google.txt
```

**For Microsoft Agent Framework:**
```bash
uv sync
uv pip install --prerelease=allow -r requirements-microsoft.txt
```

Note: Switching will downgrade/upgrade `a2a-sdk` and may reinstall packages.

## Verification

**Test Google ADK:**
```bash
python -c "import google_adk; from a2a_sdk import A2A; print(f'Google ADK OK, A2A SDK: {a2a_sdk.__version__}')"
```

**Test Microsoft Agent Framework:**
```bash
python -c "import agent_framework; from a2a_sdk import A2A; print(f'Agent Framework OK, A2A SDK: {a2a_sdk.__version__}')"
```

## Project Structure

```
poc-maf-adk-a2a/
├── .venv-google/          # Google ADK environment (optional)
├── .venv-microsoft/       # Microsoft environment (optional)
├── .venv/                 # Default environment
├── requirements-google.txt
├── requirements-microsoft.txt
└── pyproject.toml         # Core shared dependencies
```