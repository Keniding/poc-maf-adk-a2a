# A2A Orchestration Demo

Demonstrates cross-framework communication between Microsoft Agent Framework and Google ADK using the A2A protocol.

## What This Demo Shows

1. **Sequential Flow**: Account Agent → Compliance Agent
   - Query customer account info (Microsoft)
   - Analyze compliance risk (Google)
   - Synthesize results

2. **Concurrent Flow**: Both agents in parallel
   - Run both queries simultaneously
   - Combine results for faster response

3. **Health Check**: Verify both servers are running

## Prerequisites

### 1. Start A2A Servers

**Terminal 1 - Microsoft Account Agent:**
```bash
cd microsoft-agent
..\.venv\Scripts\activate
python server.py
```

**Terminal 2 - Google Compliance Agent:**
```bash
cd google-agent
..\.venv-google\Scripts\activate
python server.py
```

### 2. Verify Servers

Both should respond:
```bash
curl http://localhost:8002/.well-known/agent.json  # Microsoft
curl http://localhost:8001/.well-known/agent.json  # Google
```

## Running the Demo

```bash
# From project root
python demo/orchestrator.py
```

## What Happens

### Sequential Flow Example

```
Customer ID: 4 (Jose Fernandez Torres - HIGH RISK)

1. Account Agent (Microsoft):
   - Searches customer by ID
   - Gets account balances
   - Retrieves recent transactions
   - Returns formatted account summary

2. Compliance Agent (Google):
   - Gets customer risk profile (risk_score: 72 - HIGH)
   - Analyzes transactions for patterns
   - Detects flagged transactions
   - Returns compliance report

3. Final Report:
   - Combined view of account + risk
   - Ready for presentation to compliance officer
```

### Concurrent Flow Example

```
Customer ID: 2 (Carlos Rodriguez - MEDIUM RISK)

Both agents run in parallel:
├─ Account Agent: Gets account info
└─ Compliance Agent: Analyzes risk

Results combined instantly - faster than sequential!
```

## A2A Protocol Overview

The Agent-to-Agent (A2A) protocol enables framework-agnostic communication between AI agents.

### Key Components

**1. AgentCard**
- Discovery mechanism at `/.well-known/agent.json`
- Describes agent capabilities, skills, and metadata
- Allows clients to understand what an agent can do

**2. Task Queue**
- Server-side task management
- Handles task creation, execution, and cancellation
- Supports both synchronous and streaming responses

**3. AgentExecutor**
- Executes tasks using the underlying agent
- Manages task lifecycle (pending → running → completed)
- Handles errors and cancellation

**4. JSON-RPC Protocol**
- HTTP-based communication
- Methods: `agent.invoke`, `agent.stream`, `agent.cancel`
- Standard request/response format

### Protocol Benefits

1. **Framework Agnostic**: Microsoft and Google agents communicate seamlessly
2. **HTTP-based**: Simple REST/JSON-RPC protocol
3. **Discoverable**: Agent cards describe capabilities
4. **Scalable**: Each agent runs independently
5. **Polyglot**: Agents can be in different languages/frameworks
6. **Streaming**: Supports real-time response streaming
7. **Skills-based**: Capability discovery through skills metadata

## Message/Task Lifecycle

1. **Client sends message** via `agent.invoke` or `agent.stream`
2. **Server creates task** in task queue (generates task_id)
3. **AgentExecutor processes task** using the underlying agent
4. **Agent executes** using its tools and LLM
5. **Server returns result** (complete response or stream)
6. **Client receives output** and can request more tasks

For streaming responses:
- Server sends chunks as they're generated
- Client can cancel mid-stream using `agent.cancel`
- Useful for long-running analyses

## Architecture

```
┌─────────────────────┐
│   Orchestrator      │
│   (This demo)       │
└──────┬──────────────┘
       │
       ├─── HTTP ───► Microsoft Account Agent (port 8002)
       │               └─ A2aAgentExecutor
       │               └─ FoundryAgent v2
       │               └─ Azure AI Foundry
       │
       └─── HTTP ───► Google Compliance Agent (port 8001)
                       └─ to_a2a() helper
                       └─ Google ADK Agent
                       └─ Gemini models
```

Both agents query the same SQLite database at `../shared/database/banking.db`.

## Testing

### Integration Tests

Run the integration test suite to verify A2A communication:

```bash
python test_integration.py
```

This test suite verifies:
1. Both A2A servers are running and accessible
2. Microsoft Account Agent responds correctly
3. Google Compliance Agent responds correctly
4. Sequential flow works (Account -> Compliance)
5. Concurrent flow works (both agents in parallel)

### Prerequisites for Tests

Both servers must be running:
- Microsoft Agent on port 8002
- Google Agent on port 8001

## Extending the Demo

You can modify `orchestrator.py` to:

- Add more complex flows (e.g., handoff patterns)
- Implement error handling and retries
- Add streaming responses
- Build a web UI on top
- Add more agents to the orchestration

## Troubleshooting

**"Connection refused"**
- Make sure both A2A servers are running
- Check they're on ports 8001 and 8002
- Run health check first

**"No response from agent"**
- Check server logs for errors
- Verify .env files are configured
- Ensure database exists at `shared/database/banking.db`

**"API key error" (Google)**
- Set GOOGLE_API_KEY in `google-agent/.env`
- Get key from https://aistudio.google.com/apikey

**"Azure auth error" (Microsoft)**
- Run `az login` first
- Verify FOUNDRY_PROJECT_ENDPOINT in `microsoft-agent/.env`