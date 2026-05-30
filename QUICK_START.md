# Quick Start Guide

Get the POC running in 5 minutes.

## Prerequisites

- Python virtual environments already created (.venv and .venv-google)
- Database already initialized (shared/database/banking.db)
- Need: Azure CLI login
- Need: Google API key

## Step 1: Configure Microsoft Agent (2 minutes)

```bash
cd microsoft-agent
cp .env.example .env
```

Edit .env:
```env
# Get these from your Azure AI Foundry project
FOUNDRY_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
FOUNDRY_MODEL_DEPLOYMENT_NAME=gpt-4o
FOUNDRY_AGENT_NAME=account-agent
AZURE_CREDENTIAL_TYPE=AzureCliCredential
```

Authenticate:
```bash
az login
```

## Step 2: Configure Google Agent (1 minute)

```bash
cd ../google-agent
cp .env.example .env
```

Edit .env:
```env
# Get from: https://aistudio.google.com/apikey
GOOGLE_API_KEY=your-google-api-key-here
GOOGLE_MODEL=gemini-flash-latest
```

## Step 3: Start Servers (1 minute)

**Terminal 1 - Microsoft:**
```bash
cd microsoft-agent
..\.venv\Scripts\activate
python server.py
```

Wait for: `Starting Microsoft Account Agent A2A Server on port 8002`

**Terminal 2 - Google:**
```bash
cd google-agent
..\.venv-google\Scripts\activate
python server.py
```

Wait for: `Starting Google Compliance Agent A2A Server on port 8001`

**Alternative: Test Google Agent with ADK CLI**
```bash
cd google-agent
..\.venv-google\Scripts\activate
adk run google-agent
# or
adk web --port 8000
```

## Step 4: Run Demo (1 minute)

**Terminal 3:**
```bash
# From project root
.venv\Scripts\activate
pip install httpx  # if not installed
python demo/orchestrator.py
```

You should see the orchestrator running health checks and executing both sequential and concurrent flows.

## Verify Setup

### Test Agent Cards

```bash
# Microsoft Agent
curl http://localhost:8002/.well-known/agent.json

# Google Agent
curl http://localhost:8001/.well-known/agent.json
```

Both should return JSON with agent metadata.

### Test Direct Invocation

```bash
# Test Microsoft Agent
curl -X POST http://localhost:8002/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"agent.invoke","params":{"input":"Buscar cliente Maria Garcia"}}'

# Test Google Agent
curl -X POST http://localhost:8001/a2a \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"agent.invoke","params":{"input":"Analizar riesgo del cliente 4"}}'
```

## Troubleshooting

### Microsoft Agent

**Azure authentication failed:**
```bash
az login
az account show  # Verify logged in
```

**Foundry project not found:**
- Verify FOUNDRY_PROJECT_ENDPOINT in .env
- Ensure you have access to the project

### Google Agent

**API key error:**
- Get API key: https://aistudio.google.com/apikey
- Set in google-agent/.env: GOOGLE_API_KEY=...

**Model not found:**
- Try: GOOGLE_MODEL=gemini-1.5-flash

### Demo

**Connection refused:**
- Ensure both servers are running
- Check ports 8001 and 8002

**No response from agent:**
- Check server logs in their terminals
- Verify database exists: shared/database/banking.db

## Next Steps

1. Read PROJECT_README.md for architecture overview
2. Explore each module's README for details
3. Customize demo flows in demo/orchestrator.py
4. Add your own agents or tools

## Quick Commands Reference

```bash
# Microsoft Agent
cd microsoft-agent
..\.venv\Scripts\activate
python server.py

# Google Agent - A2A Server
cd google-agent
..\.venv-google\Scripts\activate
python server.py

# Google Agent - ADK CLI (alternative)
adk run google-agent

# Google Agent - ADK Web UI (alternative)
adk web --port 8000

# Demo
python demo/orchestrator.py

# Database
cd shared/database
python setup_db.py
```