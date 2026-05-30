"""
A2A Orchestrator Demo - Cross-Framework Agent Communication.

Demo Flows:
1. Sequential: Account Agent → Compliance Agent → Combined report
2. Concurrent: Both agents in parallel
3. MAF Workflow: WorkflowBuilder (Account → Compliance → Synthesis) run directly — no extra server needed

Prerequisites:
  - Microsoft Account Agent on port 8002
  - Google Compliance Agent on port 8001
  - shared/database/banking.db initialized
"""

import asyncio
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent / "maf-orchestrator"))


class A2AClient:
    """
    Simple A2A protocol client.

    Implements the client-side of the Agent-to-Agent protocol:
    - Agent discovery via AgentCard
    - Task invocation via JSON-RPC
    - Framework-agnostic communication
    """

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def get_agent_card(self):
        """
        Get agent card from A2A server.

        AgentCard Discovery:
        - GET /.well-known/agent.json
        - Returns agent metadata, skills, and capabilities
        - Enables automatic documentation and capability detection
        """
        response = await self.client.get(f"{self.base_url}/.well-known/agent.json")
        return response.json()

    async def invoke(self, input_text: str):
        """
        Invoke agent via A2A protocol.

        JSON-RPC agent.invoke method:
        - Sends message to agent
        - Server creates task in queue
        - AgentExecutor processes task
        - Returns complete response when done

        For streaming responses, use agent.stream method instead.
        For cancellation, use agent.cancel method with task_id.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "agent.invoke",
            "params": {
                "input": input_text,
            },
        }

        response = await self.client.post(
            f"{self.base_url}/a2a",
            json=payload,
        )
        return response.json()

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def demo_sequential_flow():
    """
    Demo: Sequential flow - Account Agent → Compliance Agent.

    1. Query customer account info (Microsoft agent)
    2. Analyze compliance risk (Google agent)
    3. Synthesize final response
    """
    print("\n" + "=" * 80)
    print("DEMO: Sequential Flow - Account → Compliance")
    print("=" * 80)

    customer_id = 4  # Jose Fernandez Torres (HIGH RISK)

    # Initialize A2A clients
    account_client = A2AClient("http://localhost:8002")
    compliance_client = A2AClient("http://localhost:8001")

    try:
        # Step 1: Get agent cards
        print("\n[1] Getting agent cards...")
        account_card = await account_client.get_agent_card()
        compliance_card = await compliance_client.get_agent_card()

        print(f"  ✓ Account Agent: {account_card['name']}")
        print(f"  ✓ Compliance Agent: {compliance_card['name']}")

        # Step 2: Query account information
        print(f"\n[2] Querying account information for customer {customer_id}...")
        account_query = f"Dame la información completa del cliente {customer_id}, incluyendo cuentas y últimas transacciones"

        account_response = await account_client.invoke(account_query)
        account_result = account_response.get("result", {}).get("output", "No response")

        print(f"\n  Account Agent Response:")
        print(f"  {account_result[:300]}...")

        # Step 3: Analyze compliance risk
        print(f"\n[3] Analyzing compliance risk for customer {customer_id}...")
        compliance_query = f"Analiza el riesgo AML/KYC del cliente {customer_id}. Revisa su perfil de riesgo y transacciones recientes."

        compliance_response = await compliance_client.invoke(compliance_query)
        compliance_result = compliance_response.get("result", {}).get("output", "No response")

        print(f"\n  Compliance Agent Response:")
        print(f"  {compliance_result[:300]}...")

        # Step 4: Synthesize final response
        print("\n[4] Final Synthesis:")
        print("-" * 80)
        print(f"\nCUSTOMER ANALYSIS REPORT - ID {customer_id}")
        print("\n--- ACCOUNT INFORMATION ---")
        print(account_result)
        print("\n--- COMPLIANCE ANALYSIS ---")
        print(compliance_result)
        print("\n" + "=" * 80)

    finally:
        await account_client.close()
        await compliance_client.close()


async def demo_concurrent_flow():
    """
    Demo: Concurrent flow - Both agents in parallel.

    1. Query account info AND compliance risk simultaneously
    2. Combine results
    """
    print("\n" + "=" * 80)
    print("DEMO: Concurrent Flow - Account || Compliance")
    print("=" * 80)

    customer_id = 2  # Carlos Rodriguez Perez (MEDIUM RISK - structuring pattern)

    account_client = A2AClient("http://localhost:8002")
    compliance_client = A2AClient("http://localhost:8001")

    try:
        print(f"\n[1] Querying both agents concurrently for customer {customer_id}...")

        # Run both queries in parallel
        account_task = account_client.invoke(
            f"Busca al cliente con ID {customer_id} y muéstrame sus cuentas y transacciones"
        )
        compliance_task = compliance_client.invoke(
            f"Analiza el riesgo AML/KYC del cliente con ID {customer_id}"
        )

        # Wait for both
        account_response, compliance_response = await asyncio.gather(
            account_task, compliance_task
        )

        account_result = account_response.get("result", {}).get("output", "No response")
        compliance_result = compliance_response.get("result", {}).get("output", "No response")

        print("\n[2] Results:")
        print("-" * 80)
        print("\n--- ACCOUNT INFO (Microsoft Agent) ---")
        print(account_result)
        print("\n--- RISK ANALYSIS (Google Agent) ---")
        print(compliance_result)
        print("\n" + "=" * 80)

    finally:
        await account_client.close()
        await compliance_client.close()


async def demo_maf_workflows():
    """
    Demo: 3 MAF WorkflowBuilder patterns run directly (no port 8003 needed).

    Pattern 1 - Sequential (add_chain):
      AccountFetch -> ComplianceFetch -> Synthesis

    Pattern 2 - Parallel (fan-out + fan-in):
      [AccountFetchParallel || ComplianceFetchParallel] -> ParallelSynthesis

    Pattern 3 - Conditional (switch-case):
      QueryRouter -> account-only | compliance-only | full chain
    """
    from agents.orchestrator import (
        create_sequential_workflow,
        create_parallel_workflow,
        create_conditional_workflow,
        run_orchestration,
    )
    from config.settings import Settings

    settings = Settings()

    # --- Pattern 1: Sequential ---
    print("\n" + "=" * 80)
    print("DEMO MAF [1/3]: Sequential (add_chain)")
    print("  AccountFetch -> ComplianceFetch -> Synthesis (Foundry)")
    print("=" * 80)
    workflow = await create_sequential_workflow(settings)
    query = "Dame el analisis completo del cliente con ID 1: cuentas, transacciones y riesgo AML"
    print(f"\nQuery: {query}")
    print("\nEjecutando workflow...")
    result = await run_orchestration(workflow, query)
    print("\nOutput:")
    print("-" * 80)
    print(result[:800] + ("..." if len(result) > 800 else ""))
    print("=" * 80)

    # --- Pattern 2: Parallel ---
    print("\n" + "=" * 80)
    print("DEMO MAF [2/3]: Parallel (fan-out + fan-in)")
    print("  [AccountFetch || ComplianceFetch] -> ParallelSynthesis (Foundry)")
    print("=" * 80)
    workflow = await create_parallel_workflow(settings)
    query = "Analiza al cliente con ID 2: estado de cuentas y evaluacion de riesgo AML"
    print(f"\nQuery: {query}")
    print("\nEjecutando workflow (ambos agentes en paralelo)...")
    result = await run_orchestration(workflow, query)
    print("\nOutput:")
    print("-" * 80)
    print(result[:800] + ("..." if len(result) > 800 else ""))
    print("=" * 80)

    # --- Pattern 3: Conditional ---
    print("\n" + "=" * 80)
    print("DEMO MAF [3/3]: Conditional (switch-case)")
    print("  QueryRouter -> cuenta-only | compliance-only | full analysis")
    print("=" * 80)
    workflow = await create_conditional_workflow(settings)

    cases = [
        ("cuenta solo",      "Muestra las cuentas y saldo del cliente con ID 3"),
        ("compliance solo",  "Analiza el riesgo AML y compliance del cliente con ID 4"),
        ("analisis completo","Dame informacion del cliente con ID 1"),
    ]

    for case_name, q in cases:
        print(f"\n  -- Caso: {case_name} --")
        print(f"  Query: {q}")
        result = await run_orchestration(workflow, q)
        print(f"  Output (primeras 300 chars): {result[:300]}...")

    print("\n" + "=" * 80)


async def demo_health_check():
    """Check which A2A servers are running."""
    print("\n" + "=" * 80)
    print("HEALTH CHECK - Verifying A2A Servers")
    print("=" * 80)

    servers = {
        "Account Agent":    ("http://localhost:8002", "cd microsoft-agent && python server.py"),
        "Compliance Agent": ("http://localhost:8001", "C:\\Users\\User\\miniconda3\\python.exe google_agent/server.py"),
    }

    running = {}
    for name, (url, cmd) in servers.items():
        client = A2AClient(url)
        try:
            card = await client.get_agent_card()
            print(f"\n✓ {name} ({url.split(':')[-1]}): RUNNING — {card['name']}")
            running[name] = True
        except Exception:
            print(f"\n✗ {name} ({url.split(':')[-1]}): NOT RUNNING")
            print(f"  Start: {cmd}")
            running[name] = False
        finally:
            await client.close()

    print("\n" + "=" * 80)
    core_ready = running.get("Account Agent") and running.get("Compliance Agent")
    return running, core_ready


async def main():
    """Run demo flows."""
    print("\n" + "=" * 80)
    print("A2A ORCHESTRATION DEMO")
    print("Microsoft Agent Framework ↔ Google ADK ↔ MAF Workflow")
    print("=" * 80)

    running, core_ready = await demo_health_check()

    if not core_ready:
        print("\n⚠  Please start Account Agent and Compliance Agent first")
        return

    await demo_sequential_flow()
    await asyncio.sleep(1)

    await demo_concurrent_flow()
    await asyncio.sleep(1)

    await demo_maf_workflows()

    print("\n\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())