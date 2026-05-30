# Google ADK - Compliance Agent

Compliance and AML/KYC agent using Google Agent Development Kit.

This project follows the official Google ADK structure with:
- `agent.py` - Main agent file with `root_agent` definition
- `.env` - API keys and configuration
- `__init__.py` - Package initialization

## Features

- **Google ADK**: Uses Google's agent framework with Gemini models
- **Official ADK Structure**: Compatible with `adk run` and `adk web` commands
- **Risk Analysis**: AML/KYC compliance, transaction monitoring
- **A2A Protocol**: Exposes agent via standardized protocol
- **No Simulation**: Real Google AI integration

## Setup

### 1. Install Dependencies

```bash
# Activate Google environment
..\\.venv-google\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Get Google API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Create or sign in to your Google account
3. Generate an API key
4. Copy the API key

### 3. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` and set your API key:
```env
GOOGLE_API_KEY=your-api-key-here
GOOGLE_MODEL=gemini-flash-latest
COMPLIANCE_A2A_PORT=8001
```

## Running

You can run this agent in multiple ways:

### Option 1: ADK CLI (Development)

Run with the official ADK command-line interface:

```bash
adk run google-agent
```

This provides an interactive chat interface for testing.

### Option 2: ADK Web UI (Development)

Run with the official ADK web interface:

```bash
# From parent directory
adk web --port 8000
```

Then navigate to http://localhost:8000 and select the compliance_agent.

### Option 3: A2A Server (Production)

Run as an A2A server for cross-framework communication:

```bash
python server.py
```

Server runs on port 8001 (configurable via `COMPLIANCE_A2A_PORT`).

Verify the agent card:

```bash
curl http://localhost:8001/.well-known/agent.json
```

## Agent Tools

The agent has access to these tools:

- `get_customer_risk_profile(customer_id)` - Get customer risk score and flags
- `check_transaction_risk(customer_id, days)` - Analyze transactions for patterns
- `get_compliance_rules(category)` - Get AML/KYC compliance rules

All tools query the shared SQLite database at `../shared/database/banking.db`.

## Risk Detection

The agent detects:

- **Structuring**: Multiple transactions between $8,000-$10,000 (avoiding $10k reporting threshold)
- **Large Cash Transactions**: Over $50,000 in cash
- **Flagged Transactions**: Previously marked by the system
- **High Risk Scores**: Customers with risk_score > 70

## Architecture

This project follows the official Google ADK structure:

```
google-agent/
├── agent.py                # Main agent file (root_agent definition)
├── __init__.py             # Package initialization
├── .env                    # API keys and configuration
├── agents/
│   ├── compliance_agent.py # Legacy: Agent factory functions
│   └── tools.py            # Risk analysis tools
├── config/
│   └── settings.py         # Google configuration
├── server.py               # A2A server (for cross-framework communication)
├── requirements.txt
└── README.md
```

The `agent.py` file is the entry point that ADK commands (`adk run`, `adk web`) expect. It defines the `root_agent` following ADK conventions.

## Available Models

- `gemini-flash-latest` - Latest Gemini Flash (recommended)
- `gemini-1.5-pro` - Most capable
- `gemini-1.5-flash` - Fast and efficient

## Production Deployment

For production:

1. Secure API key using secrets management
2. Deploy as containerized service
3. Ensure database connectivity
4. Monitor API usage and costs
5. Consider rate limiting