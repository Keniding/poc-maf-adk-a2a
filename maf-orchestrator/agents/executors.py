"""
MAF Workflow Executors for banking orchestration.

Executors shared across 3 workflow patterns:
  - Sequential:   AccountFetch -> ComplianceFetch -> Synthesis
  - Parallel:     [AccountFetchP || ComplianceFetchP] -> ParallelSynthesis  (fan-out + fan-in)
  - Conditional:  QueryRouter -> account-only | compliance-only | full chain  (switch-case)
"""

import httpx
from agent_framework import Executor, WorkflowContext
from agent_framework._workflows._executor import handler


async def _call_a2a(url: str, query: str) -> str:
    """Send a JSON-RPC agent.invoke to an A2A endpoint and return the output text."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{url}/a2a",
                json={
                    "jsonrpc": "2.0",
                    "method": "agent.invoke",
                    "id": 1,
                    "params": {"input": query},
                },
            )
            data = resp.json()
        return data.get("result", {}).get("output", "No response")
    except Exception as exc:
        return f"A2A error ({url}): {exc}"


# ---------------------------------------------------------------------------
# Sequential workflow executors
# input: str  ->  dict{query, account_info}  ->  dict{..., compliance_info}  ->  output
# ---------------------------------------------------------------------------

class AccountFetchExecutor(Executor):
    """Sequential step 1: fetch customer account info from Account Agent."""

    def __init__(self, agent_url: str):
        super().__init__(id="account_fetch")
        self.agent_url = agent_url

    @handler
    async def handle(self, query: str, ctx: WorkflowContext) -> None:
        account_info = await _call_a2a(self.agent_url, query)
        await ctx.send_message({"query": query, "account_info": account_info})


class ComplianceFetchExecutor(Executor):
    """Sequential step 2: fetch compliance risk from Compliance Agent."""

    def __init__(self, agent_url: str):
        super().__init__(id="compliance_fetch")
        self.agent_url = agent_url

    @handler
    async def handle(self, context: dict, ctx: WorkflowContext) -> None:
        compliance_info = await _call_a2a(self.agent_url, context["query"])
        context["compliance_info"] = compliance_info
        await ctx.send_message(context)


class SynthesisExecutor(Executor):
    """Sequential step 3: synthesize account + compliance via MAF Agent (Foundry)."""

    def __init__(self, maf_agent):
        super().__init__(id="synthesis")
        self.maf_agent = maf_agent

    @handler
    async def handle(self, context: dict, ctx: WorkflowContext) -> None:
        prompt = f"""\
Solicitud: {context.get("query", "")}

--- CUENTA (Account Agent) ---
{context.get("account_info", "Sin datos")}

--- COMPLIANCE (Compliance Agent) ---
{context.get("compliance_info", "Sin datos")}

Proporciona un informe bancario integrado: resumen del cliente, estado de cuentas,
evaluacion de riesgo y recomendaciones. Responde en espanol."""

        final_response = await self.maf_agent.run(prompt)
        await ctx.yield_output(str(final_response))


# ---------------------------------------------------------------------------
# Parallel workflow executors  (fan-out + fan-in)
# Both agents receive str directly and run concurrently.
# Fan-in merges their outputs into a list for synthesis.
# ---------------------------------------------------------------------------

class AccountFetchParallelExecutor(Executor):
    """Parallel branch: fetch account info from str query."""

    def __init__(self, agent_url: str):
        super().__init__(id="account_fetch_parallel")
        self.agent_url = agent_url

    @handler
    async def handle(self, query: str, ctx: WorkflowContext) -> None:
        info = await _call_a2a(self.agent_url, query)
        await ctx.send_message({"agent": "account", "query": query, "info": info})


class ComplianceFetchParallelExecutor(Executor):
    """Parallel branch: fetch compliance risk from str query."""

    def __init__(self, agent_url: str):
        super().__init__(id="compliance_fetch_parallel")
        self.agent_url = agent_url

    @handler
    async def handle(self, query: str, ctx: WorkflowContext) -> None:
        info = await _call_a2a(self.agent_url, query)
        await ctx.send_message({"agent": "compliance", "query": query, "info": info})


class ParallelSynthesisExecutor(Executor):
    """Fan-in step: receives list of results from both parallel branches, synthesizes."""

    def __init__(self, maf_agent):
        super().__init__(id="parallel_synthesis")
        self.maf_agent = maf_agent

    @handler
    async def handle(self, results: list, ctx: WorkflowContext) -> None:
        query = ""
        account_info = "Sin datos"
        compliance_info = "Sin datos"

        for item in results:
            query = item.get("query", query)
            if item.get("agent") == "account":
                account_info = item.get("info", account_info)
            elif item.get("agent") == "compliance":
                compliance_info = item.get("info", compliance_info)

        prompt = f"""\
Solicitud: {query}

--- CUENTA (Account Agent, paralelo) ---
{account_info}

--- COMPLIANCE (Compliance Agent, paralelo) ---
{compliance_info}

Proporciona un informe bancario integrado. Responde en espanol."""

        final_response = await self.maf_agent.run(prompt)
        await ctx.yield_output(str(final_response))


# ---------------------------------------------------------------------------
# Conditional workflow executors  (switch-case)
# A router inspects the query and sends it to one of three paths.
# ---------------------------------------------------------------------------

class QueryRouterExecutor(Executor):
    """Switch-case entry point: re-emits the query unchanged for conditional routing."""

    def __init__(self):
        super().__init__(id="query_router")

    @handler
    async def handle(self, query: str, ctx: WorkflowContext) -> None:
        await ctx.send_message(query)


class AccountOnlyExecutor(Executor):
    """Conditional path: account-only analysis (no compliance)."""

    def __init__(self, agent_url: str):
        super().__init__(id="account_only")
        self.agent_url = agent_url

    @handler
    async def handle(self, query: str, ctx: WorkflowContext) -> None:
        info = await _call_a2a(self.agent_url, query)
        await ctx.yield_output(f"[Solo cuenta]\n\n{info}")


class ComplianceOnlyExecutor(Executor):
    """Conditional path: compliance-only analysis (no account data)."""

    def __init__(self, agent_url: str):
        super().__init__(id="compliance_only")
        self.agent_url = agent_url

    @handler
    async def handle(self, query: str, ctx: WorkflowContext) -> None:
        info = await _call_a2a(self.agent_url, query)
        await ctx.yield_output(f"[Solo compliance]\n\n{info}")


class FullAnalysisEntryExecutor(Executor):
    """Conditional path: entry point for full analysis (delegates to sequential chain)."""

    def __init__(self, agent_url: str):
        super().__init__(id="full_analysis_entry")
        self.agent_url = agent_url

    @handler
    async def handle(self, query: str, ctx: WorkflowContext) -> None:
        account_info = await _call_a2a(self.agent_url, query)
        await ctx.send_message({"query": query, "account_info": account_info})