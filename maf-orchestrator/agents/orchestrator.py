"""
MAF Orchestrator Agent.

Uses Microsoft Agent Framework WorkflowBuilder to orchestrate:
  Account Agent (A2A port 8002) → Compliance Agent (A2A port 8001) → Synthesis (Foundry)
"""

from agent_framework import Agent, WorkflowBuilder
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential

from agents.executors import AccountFetchExecutor, ComplianceFetchExecutor, SynthesisExecutor


INSTRUCTIONS = """\
Eres un orquestador bancario senior para Interbank.
Tu función es sintetizar información de cuentas y evaluaciones de compliance
para proporcionar respuestas integrales y profesionales a los asesores bancarios.
Siempre presenta la información de forma clara, estructurada y accionable.
Responde en español."""


async def create_orchestrator(settings):
    """Create MAF workflow orchestrator."""
    maf_agent = Agent(
        client=FoundryChatClient(
            project_endpoint=settings.foundry_project_endpoint,
            model=settings.foundry_model,
            credential=AzureCliCredential(),
        ),
        name="BankingOrchestrator",
        instructions=INSTRUCTIONS,
    )

    account_exec = AccountFetchExecutor(agent_url=settings.account_agent_url)
    compliance_exec = ComplianceFetchExecutor(agent_url=settings.compliance_agent_url)
    synthesis_exec = SynthesisExecutor(maf_agent=maf_agent)

    workflow = (
        WorkflowBuilder(start_executor=account_exec)
        .add_chain([account_exec, compliance_exec, synthesis_exec])
        .build()
    )

    return workflow


async def run_orchestration(workflow, user_query: str) -> str:
    """Execute the workflow and return final synthesized response."""
    result = await workflow.run(user_query)
    outputs = result.get_outputs()
    return outputs[0] if outputs else "No response generated."