# Microsoft Agent Framework - Account Agent

Account agent using Microsoft Agent Framework with FoundryAgent v2.

## Features

- **FoundryAgent v2**: Connects to published agent in Azure AI Foundry
- **RAG over SQLite**: Customer data, accounts, transactions
- **A2A Protocol**: Exposes agent via standardized protocol
- **No Simulation**: Real Azure AI Foundry integration

## Setup

### 1. Install Dependencies

```bash
# Activate Microsoft environment
..\\.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Azure

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:
- `FOUNDRY_PROJECT_ENDPOINT`: Your Azure AI Foundry project URL
- `FOUNDRY_MODEL_DEPLOYMENT_NAME`: Model deployment (e.g., gpt-4o)
- `FOUNDRY_AGENT_NAME`: Agent name in Foundry
- `AZURE_CREDENTIAL_TYPE`: AzureCliCredential (local) or ManagedIdentityCredential (prod)

### 3. Authenticate with Azure

```bash
az login
```

### 4. Publish Agent to Foundry (First Time)

```bash
python -m agents.account_agent
```

This publishes the agent definition to Azure AI Foundry.

## Running

### Start A2A Server

```bash
python server.py
```

Server runs on port 8002 (configurable via `ACCOUNT_A2A_PORT`).

### Verify Agent Card

```bash
curl http://localhost:8002/.well-known/agent.json
```

## Agent Tools

The agent has access to these tools:

- `search_customer(query)` - Search customers by name, email, phone
- `get_customer_accounts(customer_id)` - Get all accounts for a customer
- `get_account_transactions(account_id, limit)` - Get recent transactions
- `search_products(product_type)` - Search banking products

All tools query the shared SQLite database at `../shared/database/banking.db`.

## Architecture

```
microsoft-agent/
├── agents/
│   ├── account_agent.py    # FoundryAgent v2 definition
│   └── tools.py            # RAG tools (SQLite queries)
├── config/
│   └── settings.py         # Azure configuration
├── server.py               # A2A server
├── requirements.txt
├── .env.example
└── README.md
```

## Production Deployment

For production on Azure:

1. Use Managed Identity:
```env
AZURE_CREDENTIAL_TYPE=ManagedIdentityCredential
AZURE_MANAGED_IDENTITY_CLIENT_ID=your-client-id
```

2. Deploy as Azure Container Instance or App Service
3. Ensure database is accessible (Azure SQL or mounted volume)