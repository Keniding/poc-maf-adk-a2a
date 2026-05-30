"""
A2A Orchestrator Demo - Cross-Framework Agent Communication.

This demo shows how Microsoft Agent Framework and Google ADK agents
communicate via the A2A protocol.

A2A Client Implementation:
- Discovers agents via AgentCard (GET /.well-known/agent.json)
- Invokes agents via JSON-RPC (POST /a2a with agent.invoke method)
- Supports both sequential and concurrent flows
- Framework-agnostic: works with any A2A-compliant agent

Demo Flows:
1. Sequential: Account Agent → Compliance Agent → Combined report
2. Concurrent: Both agents execute in parallel for faster results

Prerequisites:
1. Both A2A servers must be running:
   - Microsoft Account Agent on port 8002
   - Google Compliance Agent on port 8001

2. Database must be initialized:
   - shared/database/banking.db
"""

import asyncio
import httpx


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
            f"Dame información del cliente {customer_id} y sus cuentas"
        )
        compliance_task = compliance_client.invoke(
            f"Analiza el riesgo del cliente {customer_id}"
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


async def demo_health_check():
    """Check if both A2A servers are running."""
    print("\n" + "=" * 80)
    print("HEALTH CHECK - Verifying A2A Servers")
    print("=" * 80)

    account_client = A2AClient("http://localhost:8002")
    compliance_client = A2AClient("http://localhost:8001")

    try:
        # Check account agent
        try:
            account_card = await account_client.get_agent_card()
            print(f"\n✓ Account Agent (port 8002): RUNNING")
            print(f"  Name: {account_card['name']}")
            print(f"  Description: {account_card['description']}")
        except Exception as e:
            print(f"\n✗ Account Agent (port 8002): NOT RUNNING")
            print(f"  Error: {e}")
            print("\n  Start with: cd microsoft-agent && python server.py")
            return False

        # Check compliance agent
        try:
            compliance_card = await compliance_client.get_agent_card()
            print(f"\n✓ Compliance Agent (port 8001): RUNNING")
            print(f"  Name: {compliance_card['name']}")
            print(f"  Description: {compliance_card['description']}")
        except Exception as e:
            print(f"\n✗ Compliance Agent (port 8001): NOT RUNNING")
            print(f"  Error: {e}")
            print("\n  Start with: cd google-agent && python server.py")
            return False

        print("\n" + "=" * 80)
        print("✓ All A2A servers are running")
        return True

    finally:
        await account_client.close()
        await compliance_client.close()


async def main():
    """Run demo flows."""
    print("\n" + "=" * 80)
    print("A2A ORCHESTRATION DEMO")
    print("Cross-Framework Agent Communication")
    print("Microsoft Agent Framework ↔ Google ADK")
    print("=" * 80)

    # Health check first
    servers_running = await demo_health_check()

    if not servers_running:
        print("\n⚠️  Please start both A2A servers before running demos")
        return

    # Run demos
    print("\n\nRunning demos...")

    # Demo 1: Sequential
    await demo_sequential_flow()

    # Wait a bit
    await asyncio.sleep(2)

    # Demo 2: Concurrent
    await demo_concurrent_flow()

    print("\n\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())