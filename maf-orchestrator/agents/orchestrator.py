"""
MAF Orchestrator - 3 workflow patterns using WorkflowBuilder.

Patterns:
  1. sequential  - add_chain: account -> compliance -> synthesis (Foundry)
  2. parallel    - fan_out + fan_in: [account || compliance] -> synthesis (Foundry)
  3. conditional - switch_case: route by query keyword -> account-only | compliance-only | full
"""

from agent_framework import Agent, WorkflowBuilder
from agent_framework._workflows._edge import Case, Default
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

from agents.executors import (
    AccountFetchExecutor,
    AccountFetchParallelExecutor,
    AccountOnlyExecutor,
    ComplianceFetchExecutor,
    ComplianceFetchParallelExecutor,
    ComplianceOnlyExecutor,
    FullAnalysisEntryExecutor,
    ParallelSynthesisExecutor,
    QueryRouterExecutor,
    SynthesisExecutor,
)


INSTRUCTIONS = """\
Eres un orquestador bancario senior para Interbank.
Tu funcion es sintetizar informacion de cuentas y evaluaciones de compliance
para proporcionar respuestas integrales y profesionales a los asesores bancarios.
Siempre presenta la informacion de forma clara, estructurada y accionable.
Responde en espanol."""


def _make_agent(settings) -> Agent:
    return Agent(
        client=FoundryChatClient(
            project_endpoint=settings.foundry_project_endpoint,
            model=settings.foundry_model,
            credential=AzureCliCredential(),
        ),
        name="BankingOrchestrator",
        instructions=INSTRUCTIONS,
    )


async def create_sequential_workflow(settings):
    """
    Pattern 1: add_chain (sequential).

    account_fetch -> compliance_fetch -> synthesis
    Each step waits for the previous one to complete.
    The compliance step receives the account result to provide context.
    """
    maf_agent = _make_agent(settings)
    account_exec = AccountFetchExecutor(agent_url=settings.account_agent_url)
    compliance_exec = ComplianceFetchExecutor(agent_url=settings.compliance_agent_url)
    synthesis_exec = SynthesisExecutor(maf_agent=maf_agent)

    return (
        WorkflowBuilder(start_executor=account_exec)
        .add_chain([account_exec, compliance_exec, synthesis_exec])
        .build()
    )


async def create_parallel_workflow(settings):
    """
    Pattern 2: fan_out + fan_in (parallel).

    account_parallel --|
                       |--> parallel_synthesis
    compliance_parallel|

    Both agents receive the same query simultaneously.
    Synthesis waits until both branches complete (fan-in).
    """
    maf_agent = _make_agent(settings)
    account_exec = AccountFetchParallelExecutor(agent_url=settings.account_agent_url)
    compliance_exec = ComplianceFetchParallelExecutor(agent_url=settings.compliance_agent_url)
    synthesis_exec = ParallelSynthesisExecutor(maf_agent=maf_agent)

    router = QueryRouterExecutor()

    return (
        WorkflowBuilder(start_executor=router)
        .add_fan_out_edges(router, [account_exec, compliance_exec])
        .add_fan_in_edges([account_exec, compliance_exec], synthesis_exec)
        .build()
    )


async def create_conditional_workflow(settings):
    """
    Pattern 3: switch_case (conditional routing).

    query_router --> [cuenta|account|saldo]  --> account_only  (yields directly)
                 --> [riesgo|aml|compliance]  --> compliance_only (yields directly)
                 --> default                  --> full_analysis_entry -> compliance -> synthesis

    The router sends the query to one of three paths based on keywords.
    """
    maf_agent = _make_agent(settings)
    router = QueryRouterExecutor()
    account_only = AccountOnlyExecutor(agent_url=settings.account_agent_url)
    compliance_only = ComplianceOnlyExecutor(agent_url=settings.compliance_agent_url)
    full_entry = FullAnalysisEntryExecutor(agent_url=settings.account_agent_url)
    compliance_full = ComplianceFetchExecutor(agent_url=settings.compliance_agent_url)
    synthesis = SynthesisExecutor(maf_agent=maf_agent)

    def is_account_only(query: str) -> bool:
        keywords = {"cuenta", "saldo", "account", "balance", "transaccion", "deposito", "retiro"}
        q = query.lower()
        return any(k in q for k in keywords) and not any(
            k in q for k in {"riesgo", "aml", "compliance", "fraude", "kyc"}
        )

    def is_compliance_only(query: str) -> bool:
        keywords = {"riesgo", "aml", "compliance", "fraude", "kyc", "lavado", "sospechoso"}
        return any(k in query.lower() for k in keywords) and not any(
            k in query.lower() for k in {"cuenta", "saldo", "balance", "transaccion"}
        )

    return (
        WorkflowBuilder(start_executor=router)
        .add_switch_case_edge_group(
            router,
            [
                Case(condition=is_account_only, target=account_only),
                Case(condition=is_compliance_only, target=compliance_only),
                Default(target=full_entry),
            ],
        )
        .add_chain([full_entry, compliance_full, synthesis])
        .build()
    )


async def run_orchestration(workflow, user_query: str) -> str:
    """Execute any workflow and return the final output."""
    result = await workflow.run(user_query)
    outputs = result.get_outputs()
    return outputs[0] if outputs else "No response generated."


# Backward-compatible alias
create_orchestrator = create_sequential_workflow