# START HERE - POC Overview

## Project Structure

This POC demonstrates cross-framework agent communication using the A2A protocol. The project is organized into independent, production-ready modules with real API integrations.

```
poc-maf-adk-a2a/
├── microsoft-agent/    # Microsoft Agent Framework + Azure AI Foundry
├── google-agent/       # Google ADK + Gemini
├── shared/             # SQLite database (shared by both)
├── demo/               # A2A orchestration demo
└── [documentation]
```

## Key Features

- Real Azure + Google API integrations (no simulation)
- Separate modules per framework
- Clean A2A protocol communication
- Production-ready patterns
- Easy to present and demonstrate

## Documentation Guide

| File | Purpose | Read When |
|------|---------|-----------|
| QUICK_START.md | Get running in 5 minutes | You want to run it immediately |
| PROJECT_README.md | Complete architecture overview | You want to understand the system |
| SETUP.md | Detailed setup instructions | You're configuring for first time |
| microsoft-agent/README.md | Microsoft module details | Working on Microsoft agent |
| google-agent/README.md | Google module details | Working on Google agent |
| demo/README.md | Demo guide | Running the orchestration demo |

## Quick Start (5 minutes)

### 1. Configure Environments

**Microsoft Agent:**
```bash
cd microsoft-agent
cp .env.example .env
# Edit .env with Azure AI Foundry details
```

**Google Agent:**
```bash
cd google-agent
cp .env.example .env
# Edit .env with Google API key
```

### 2. Authenticate

```bash
az login  # For Azure
```

### 3. Start A2A Servers

**Terminal 1 - Microsoft Agent:**
```bash
cd microsoft-agent
..\.venv\Scripts\activate
python server.py
```

**Terminal 2 - Google Agent:**
```bash
cd google-agent
..\.venv-google\Scripts\activate
python server.py
# Alternative: adk run google-agent or adk web
```

### 4. Run Demo

**Terminal 3:**
```bash
python demo/orchestrator.py
```

## Architecture Overview

```
DEMO (Orchestrator)
    |
    +--- HTTP/A2A ----> Microsoft Agent (port 8002)
    |                   - Azure AI Foundry + GPT-4o
    |
    +--- HTTP/A2A ----> Google Agent (port 8001)
                        - Gemini Flash

Both agents query: shared/database/banking.db
```

## The Two Agents

### Account Agent (Microsoft)
- Retrieves customer data, balances, transactions
- Uses FoundryAgent v2 (Azure hosted)
- Port: 8002

### Compliance Agent (Google)
- Analyzes risk, detects suspicious patterns
- Uses Google ADK with Gemini (follows official ADK structure)
- Main file: `agent.py` with `root_agent` definition
- Port: 8001
- Supports ADK commands: `adk run` and `adk web`

## Demo Flows

1. **Sequential Flow**: Account -> Compliance -> Combined result
2. **Concurrent Flow**: Both agents execute in parallel
3. **A2A Protocol**: Framework-agnostic communication

## Module Independence

Each module is completely independent:

```
microsoft-agent/
├── agents/          # Agent implementation
├── config/          # Azure configuration
├── server.py        # A2A server
├── .env             # Secrets
└── README.md        # Module documentation

google-agent/
├── agents/          # Agent implementation
├── config/          # Google configuration
├── server.py        # A2A server
├── .env             # Secrets
└── README.md        # Module documentation
```

## For Presentations

1. Show the modular structure
2. Start both A2A servers
3. Display agent cards (A2A protocol)
4. Run orchestrator demo
5. Explain framework-agnostic benefits

## Next Steps

After reading this:

1. Go to QUICK_START.md to get it running
2. Read PROJECT_README.md for complete details
3. Explore each module's README
4. Run the demo and customize it

## Troubleshooting

- Setup issues: See SETUP.md
- Microsoft agent: See microsoft-agent/README.md
- Google agent: See google-agent/README.md
- Demo problems: See demo/README.md

---

Ready to start? Go to QUICK_START.md