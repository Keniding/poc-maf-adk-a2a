# POC: Cross-Framework Agent Communication via A2A

**Microsoft Agent Framework + Google ADK** communicating via the **A2A (Agent-to-Agent) Protocol**.

## What This POC Demonstrates

1. **Real agent frameworks** (no simulation)
   - Microsoft Agent Framework with Azure AI Foundry
   - Google ADK with Gemini models

2. **A2A Protocol** for cross-framework communication
   - HTTP/JSON-RPC based
   - Framework-agnostic
   - AgentCard discovery at /.well-known/agent.json
   - Task Queue for execution management
   - AgentExecutor for task lifecycle
   - Streaming support for real-time responses
   - Skills-based capability discovery

3. **Modular architecture** for easy presentation
   - Separate modules per framework
   - Shared database
   - Orchestration demo

## Project Structure

```
poc-maf-adk-a2a/
├── microsoft-agent/         # Microsoft Agent Framework module
│   ├── agents/
│   │   ├── account_agent.py    # FoundryAgent v2 (Azure)
│   │   └── tools.py            # RAG tools (customer data)
│   ├── config/
│   │   └── settings.py         # Azure configuration
│   ├── server.py               # A2A server (port 8002)
│   ├── requirements.txt        # agent-framework==1.7.0
│   ├── .env.example
│   └── README.md
│
├── google-agent/            # Google ADK module
│   ├── agent.py                # Main agent (root_agent) - ADK entry point
│   ├── __init__.py             # Package initialization
│   ├── .env                    # API keys
│   ├── agents/
│   │   ├── compliance_agent.py # Agent factory functions
│   │   └── tools.py            # Risk analysis tools
│   ├── config/
│   │   └── settings.py         # Google configuration
│   ├── server.py               # A2A server (port 8001)
│   ├── requirements.txt        # google-adk[a2a]>=2.1.0
│   ├── .env.example
│   └── README.md
│
├── shared/                  # Shared resources
│   ├── database/
│   │   ├── setup_db.py         # Database initialization
│   │   └── banking.db          # SQLite database
│   └── README.md
│
├── demo/                    # A2A orchestration demo
│   ├── orchestrator.py         # Sequential & concurrent flows
│   ├── requirements.txt        # httpx
│   └── README.md
│
├── .venv/                   # Microsoft environment
├── .venv-google/            # Google environment
├── SETUP.md                 # Detailed setup instructions
└── PROJECT_README.md        # This file
```

## Quick Start

### 1. Setup Virtual Environments

Already configured:
- `.venv` - Microsoft Agent Framework (Python 3.12.6)
- `.venv-google` - Google ADK (Python 3.14.2)

### 2. Configure Environments

**Microsoft Agent (.env in `microsoft-agent/`):**
```env
FOUNDRY_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
FOUNDRY_MODEL_DEPLOYMENT_NAME=gpt-4o
FOUNDRY_AGENT_NAME=account-agent
FOUNDRY_AGENT_VERSION=1.0
AZURE_CREDENTIAL_TYPE=AzureCliCredential
```

**Google Agent (.env in `google-agent/`):**
```env
GOOGLE_API_KEY=your-google-api-key
GOOGLE_MODEL=gemini-2.0-flash-exp
```

### 3. Authenticate

```bash
# Azure (for Microsoft agent)
az login

# Google API key
# Get from: https://aistudio.google.com/apikey
```

### 4. Initialize Database

```bash
cd shared/database
python setup_db.py
```

### 5. Start A2A Servers

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
```

### 6. Run Demo

**Terminal 3:**
```bash
# Install demo dependencies
.venv\Scripts\activate  # or .venv-google
pip install -r demo/requirements.txt

# Run orchestration demo
python demo/orchestrator.py
```

## Architecture

### Agent Communication Flow

```
┌──────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                               │
│                  (demo/orchestrator.py)                       │
└────────────┬──────────────────────────┬──────────────────────┘
             │                          │
             │ HTTP/A2A                 │ HTTP/A2A
             │ (port 8002)              │ (port 8001)
             ▼                          ▼
   ┌──────────────────────┐   ┌──────────────────────┐
   │  MICROSOFT AGENT     │   │   GOOGLE AGENT       │
   │  Account Agent       │   │   Compliance Agent   │
   │                      │   │                      │
   │  FoundryAgent v2     │   │   Google ADK         │
   │  Azure AI Foundry    │   │   Gemini Flash       │
   └──────────┬───────────┘   └─────────┬────────────┘
              │                         │
              └────────┬────────────────┘
                       │
                       ▼
               ┌───────────────┐
               │  SHARED DB    │
               │  banking.db   │
               └───────────────┘
```

### Module Independence

Each module is **completely independent**:
- Own virtual environment
- Own dependencies
- Own configuration
- Own A2A server

They communicate **only via A2A protocol** (HTTP).

## A2A Protocol Details

### What is A2A?

The Agent-to-Agent (A2A) protocol is a standardized communication protocol that enables AI agents built on different frameworks to interact seamlessly.

### Core Components

**AgentCard**
- Published at `/.well-known/agent.json`
- Contains agent metadata: name, description, version
- Lists available skills and capabilities
- Enables automatic discovery and documentation

**Task Queue**
- Server-side task management system
- Queues incoming requests for execution
- Manages concurrent task execution
- Handles task prioritization and cancellation

**AgentExecutor**
- Executes tasks using the underlying agent
- Manages task lifecycle: pending → running → completed/failed
- Supports both synchronous and streaming responses
- Handles errors, timeouts, and cancellation

**JSON-RPC Methods**
- `agent.invoke`: Send message, get complete response
- `agent.stream`: Send message, stream chunks in real-time
- `agent.cancel`: Cancel running task by task_id

### Message/Task Lifecycle

1. Client discovers agent via AgentCard (`GET /.well-known/agent.json`)
2. Client sends message via JSON-RPC (`POST /a2a`)
3. Server creates task in queue (assigns task_id)
4. AgentExecutor picks up task and executes
5. Agent processes using tools and LLM
6. Server returns result (sync) or streams chunks (streaming)
7. Client receives output and can send more messages

### Implementation in This POC

**Microsoft Agent (FoundryAgent v2)**
```python
from agent_framework.a2a import A2aAgentExecutor

executor = A2aAgentExecutor(
    agent=agent,
    agent_id="account-agent",
    name="Account Agent",
    description="Banking account specialist"
)
app = Starlette(routes=[Mount("/", app=executor.as_asgi())])
```

**Google Agent (Google ADK)**
```python
from google.adk.a2a.utils.agent_to_a2a import to_a2a

agent = Agent(name="compliance_agent", model="gemini-flash-latest", ...)
app = to_a2a(agent, host="localhost", port=8001, protocol="http")
```

The `to_a2a()` helper automatically:
- Generates AgentCard from agent metadata
- Sets up Task Queue and AgentExecutor
- Configures streaming support
- Publishes agent card at /.well-known/agent.json

### Benefits

1. **Framework Independence**: Agents don't need to know about each other's frameworks
2. **Language Agnostic**: Can be implemented in any language with HTTP support
3. **Discoverable**: AgentCards enable automatic capability detection
4. **Streaming**: Real-time responses for long-running tasks
5. **Scalable**: Each agent is an independent service
6. **Production-Ready**: Standard HTTP/JSON means existing infrastructure works

## Agents

### Account Agent (Microsoft)

- **Framework**: Microsoft Agent Framework 1.7.0
- **Type**: FoundryAgent v2 (server-side hosted)
- **Model**: GPT-4o (Azure)
- **Capabilities**:
  - Search customers
  - Get account balances
  - Retrieve transaction history
  - Recommend products
- **Port**: 8002

### Compliance Agent (Google)

- **Framework**: Google ADK 2.1.0
- **Type**: Google ADK Agent (follows official ADK structure)
- **Entry Point**: `agent.py` with `root_agent` definition
- **Model**: Gemini Flash
- **Capabilities**:
  - Analyze risk profiles
  - Detect transaction patterns
  - AML/KYC compliance checks
  - Generate compliance reports
- **Port**: 8001
- **ADK Commands**: `adk run google-agent`, `adk web`

## Demo Flows

### Sequential Flow

1. Query account info → Microsoft Agent
2. Analyze compliance → Google Agent
3. Synthesize results

### Concurrent Flow

1. Query both agents in parallel
2. Combine results
3. Faster response time

## Sample Data

Database includes 5 test customers:

| ID | Name | Risk Score | Use Case |
|----|------|------------|----------|
| 1 | Maria Garcia | 15 (LOW) | Standard customer |
| 2 | Carlos Rodriguez | 45 (MEDIUM) | Structuring pattern |
| 3 | Ana Martinez | 22 (LOW) | Premium customer |
| 4 | Jose Fernandez | 72 (HIGH) | Multiple risk flags |
| 5 | Luis Chen | 18 (LOW) | Corporate customer |

## Presentation Tips

### Show Module Separation

```bash
# Show directory structure
tree -L 2

# Show different environments
.venv\Scripts\python --version          # 3.12.6
.venv-google\Scripts\python --version   # 3.14.2
```

### Live Demo

1. **Start servers** (show in 2 terminals)
2. **Show agent cards**:
   ```bash
   curl http://localhost:8002/.well-known/agent.json
   curl http://localhost:8001/.well-known/agent.json
   ```
3. **Run orchestrator** - shows both flows
4. **Explain A2A protocol** - framework-agnostic communication

### Code Walkthrough

1. **Microsoft Agent** (`microsoft-agent/agents/account_agent.py`)
   - Show FoundryAgent v2 setup
   - Tools implementation

2. **Google Agent** (`google-agent/agents/compliance_agent.py`)
   - Show Google ADK setup
   - to_a2a() helper

3. **Orchestrator** (`demo/orchestrator.py`)
   - HTTP/JSON-RPC calls
   - Parallel execution

## 📚 Documentation

- `SETUP.md` - Detailed setup instructions
- `microsoft-agent/README.md` - Microsoft module docs
- `google-agent/README.md` - Google module docs
- `shared/README.md` - Database schema
- `demo/README.md` - Demo instructions

## Key Takeaways

1. **No simulation** - Real Azure + Google integration
2. **Modular design** - Easy to present and explain
3. **A2A protocol** - Framework-agnostic communication
4. **Production-ready patterns** - Follows best practices
5. **Complete separation** - Different environments, same protocol

## Troubleshooting

See individual module READMEs for specific issues:
- `microsoft-agent/README.md` - Azure authentication, Foundry setup
- `google-agent/README.md` - Google API key, model selection
- `demo/README.md` - Server connectivity, orchestration issues

## Testing

### Quick Test All Modules

```bash
# Test Google Agent
cd google-agent
..\.venv-google\Scripts\activate
python test_all.py

# Test Microsoft Agent
cd microsoft-agent
..\.venv\Scripts\activate
python test_all.py

# Test Integration (requires both servers running)
cd demo
python test_integration.py
```

See `TESTING.md` for complete testing documentation.

## Next Steps

1. Run tests to verify setup:
   ```bash
   # See TESTING.md for details
   ```

2. Publish Microsoft agent to Azure AI Foundry:
   ```bash
   cd microsoft-agent
   python -m agents.account_agent
   ```

3. Test agents individually before orchestration

4. Customize demo flows for your presentation

5. Add more agents or capabilities as needed