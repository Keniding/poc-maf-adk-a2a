"""
MAF Workflow Executors for banking orchestration.

Sequential workflow: AccountFetch → ComplianceFetch → Synthesis
"""

import httpx
from agent_framework import Executor, WorkflowContext
from agent_framework._workflows._executor import handler


class AccountFetchExecutor(Executor):
    """Step 1: Call Account Agent via A2A to get customer info."""

    def __init__(self, agent_url: str):
        super().__init__(id="account_fetch")
        self.agent_url = agent_url

    @handler
    async def handle(self, query: str, ctx: WorkflowContext) -> None:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.agent_url}/a2a",
                    json={
                        "jsonrpc": "2.0",
                        "method": "agent.invoke",
                        "id": 1,
                        "params": {"input": query},
                    },
                )
                data = resp.json()
            account_info = data.get("result", {}).get("output", "No account info available")
        except Exception as exc:
            account_info = f"Account Agent error: {exc}"

        await ctx.send_message({"query": query, "account_info": account_info})


class ComplianceFetchExecutor(Executor):
    """Step 2: Call Compliance Agent via A2A to assess risk."""

    def __init__(self, agent_url: str):
        super().__init__(id="compliance_fetch")
        self.agent_url = agent_url

    @handler
    async def handle(self, context: dict, ctx: WorkflowContext) -> None:
        query = context["query"]
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.agent_url}/a2a",
                    json={
                        "jsonrpc": "2.0",
                        "method": "agent.invoke",
                        "id": 1,
                        "params": {"input": query},
                    },
                )
                data = resp.json()
            compliance_info = data.get("result", {}).get("output", "No compliance info available")
        except Exception as exc:
            compliance_info = f"Compliance Agent error: {exc}"

        context["compliance_info"] = compliance_info
        await ctx.send_message(context)


class SynthesisExecutor(Executor):
    """Step 3: Use MAF Agent (Foundry) to synthesize account + compliance info."""

    def __init__(self, maf_agent):
        super().__init__(id="synthesis")
        self.maf_agent = maf_agent

    @handler
    async def handle(self, context: dict, ctx: WorkflowContext) -> None:
        query = context.get("query", "")
        account_info = context.get("account_info", "No data")
        compliance_info = context.get("compliance_info", "No data")

        synthesis_prompt = f"""\
Solicitud del usuario: {query}

--- INFORMACIÓN DE CUENTA (Account Agent) ---
{account_info}

--- EVALUACIÓN DE COMPLIANCE (Compliance Agent) ---
{compliance_info}

Proporciona una respuesta bancaria integrada y profesional combinando ambas perspectivas.
Incluye: resumen del cliente, estado de cuentas, evaluación de riesgo y recomendaciones.
Responde en español."""

        final_response = await self.maf_agent.run(synthesis_prompt)
        await ctx.yield_output(str(final_response))