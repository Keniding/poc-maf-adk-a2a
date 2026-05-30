# Cross-Framework Agent Communication via A2A Protocol

Proof of concept demonstrating interoperability between Microsoft Agent Framework and Google ADK using the Agent-to-Agent (A2A) protocol.

## Overview

This project showcases how agents built on different frameworks can communicate seamlessly through a standardized protocol. It features two independent modules:

- **Microsoft Account Agent**: Customer data queries using Azure AI Foundry
- **Google Compliance Agent**: AML/KYC risk analysis using Gemini

Both agents expose A2A-compliant endpoints and can be orchestrated together despite running in separate environments with incompatible dependencies.

## Project Structure

```
poc-maf-adk-a2a/
├── microsoft-agent/         # Microsoft Agent Framework module
│   ├── agents/              # FoundryAgent v2 implementation
│   ├── config/              # Azure configuration
│   ├── server.py            # A2A server (port 8002)
│   └── README.md
│
├── google-agent/            # Google ADK module
│   ├── agents/              # Google ADK Agent implementation
│   ├── config/              # Google configuration
│   ├── server.py            # A2A server (port 8001)
│   └── README.md
│
├── shared/                  # Shared resources
│   └── database/            # SQLite database
│
└── demo/                    # Orchestration demonstration
    └── orchestrator.py      # Sequential & concurrent flows
```

## Quick Start

### Prerequisites

- Python 3.12+ with virtual environments (.venv and .venv-google)
- Azure CLI (for Microsoft agent)
- Google API key (for Google agent)

### Setup

1. **Configure Microsoft Agent**
   ```bash
   cd microsoft-agent
   cp .env.example .env
   # Edit .env with Azure AI Foundry credentials
   az login
   ```

2. **Configure Google Agent**
   ```bash
   cd google-agent
   cp .env.example .env
   # Edit .env with Google API key
   ```

3. **Start A2A Servers**

   Terminal 1:
   ```bash
   cd microsoft-agent
   ..\.venv\Scripts\activate
   python server.py
   ```

   Terminal 2:
   ```bash
   cd google-agent
   ..\.venv-google\Scripts\activate
   python server.py
   ```

4. **Run Demo**

   Terminal 3:
   ```bash
   python demo/orchestrator.py
   ```

## Architecture

```
Orchestrator
    |
    +---> Microsoft Account Agent (port 8002)
    |     - Framework: Microsoft Agent Framework 1.7.0
    |     - Backend: Azure AI Foundry + GPT-4o
    |     - Capabilities: Customer queries, balances, transactions
    |
    +---> Google Compliance Agent (port 8001)
          - Framework: Google ADK 2.1.0
          - Backend: Gemini Flash
          - Capabilities: Risk analysis, AML/KYC compliance

Communication: HTTP/JSON-RPC via A2A Protocol
Data Source: Shared SQLite database (shared/database/banking.db)
```

## Key Features

- **Production-Ready**: Real API integrations (Azure AI Foundry and Google Gemini)
- **Framework-Agnostic**: Demonstrates interoperability through standardized protocol
- **Modular Design**: Each agent is an independent, deployable unit
- **Scalable Architecture**: Agents can run on separate infrastructure
- **Standard Compliance**: Implements A2A protocol specification

## Documentation

- **START_HERE.md**: Entry point and navigation guide
- **QUICK_START.md**: 5-minute setup guide
- **PROJECT_README.md**: Complete architecture documentation
- **SETUP.md**: Detailed configuration instructions
- **TESTING.md**: Complete testing guide

Each module contains its own README and TESTING.md with specific setup and testing information.

## Use Cases

The demo implements two orchestration patterns:

1. **Sequential Flow**: Account query → Compliance analysis → Combined report
2. **Concurrent Flow**: Both agents execute in parallel for faster response

These patterns demonstrate how to build sophisticated multi-agent systems that leverage specialized capabilities from different frameworks.

## Requirements

### Microsoft Agent Module
- Microsoft Agent Framework 1.7.0
- Azure AI Projects SDK
- Azure CLI authentication

### Google Agent Module
- Google ADK 2.1.0
- Google API key
- Gemini model access

### Demo Orchestrator
- httpx for HTTP client

See individual module README files for complete dependency lists.

## License

This is a proof of concept for demonstration purposes.

## Support

For issues or questions:
- Microsoft Agent: See microsoft-agent/README.md
- Google Agent: See google-agent/README.md
- Demo: See demo/README.md
- Setup: See SETUP.md