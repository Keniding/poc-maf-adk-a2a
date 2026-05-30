"""Account Agent - Azure AI Foundry with OpenAI tool calling."""

import inspect
import json
from typing import Callable


INSTRUCTIONS = """\
Eres un especialista bancario de cuentas para Interbank.

Capacidades:
- Buscar clientes por nombre, email o teléfono
- Consultar cuentas y balances de clientes
- Revisar historial de transacciones
- Recomendar productos bancarios

Herramientas disponibles (usa EXACTAMENTE estos nombres):
- search_customer(query: str) -> busca clientes por nombre/email/teléfono
- get_customer_accounts(customer_id: int) -> lista cuentas y balances del cliente
- get_account_transactions(account_id: int, limit: int) -> historial de transacciones
- search_products(product_type: str) -> busca productos bancarios disponibles

Reglas:
- Siempre identifica primero al cliente con search_customer
- Presenta la información de forma clara y organizada
- Si encuentras transacciones marcadas, menciónalas pero no hagas análisis de riesgo
- Sé profesional y útil
- Responde en español
"""

_TYPE_MAP = {int: "integer", str: "string", float: "number", bool: "boolean"}


def _func_to_tool_schema(func: Callable) -> dict:
    """Convert a Python function to an OpenAI tool schema."""
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or ""
    description = doc.split("\n")[0] if doc else func.__name__

    properties = {}
    required = []
    for name, param in sig.parameters.items():
        json_type = _TYPE_MAP.get(param.annotation, "string")
        properties[name] = {"type": json_type}
        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


class AccountAgent:
    """Account agent using Azure AI Foundry via OpenAI-compatible API."""

    def __init__(self, openai_client, model: str, tools: list[Callable]):
        self.openai = openai_client
        self.model = model
        self._tool_map = {t.__name__: t for t in tools}
        self._tool_schemas = [_func_to_tool_schema(t) for t in tools]

    async def run(self, user_message: str) -> str:
        """Run agent with tool calling loop."""
        messages = [
            {"role": "system", "content": INSTRUCTIONS},
            {"role": "user", "content": user_message},
        ]

        for _ in range(10):
            response = await self.openai.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self._tool_schemas,
                tool_choice="auto",
            )

            choice = response.choices[0]
            messages.append(choice.message.model_dump(exclude_none=True))

            if choice.finish_reason == "stop":
                return choice.message.content or ""

            if choice.finish_reason == "tool_calls":
                for tool_call in choice.message.tool_calls:
                    func_name = tool_call.function.name
                    func = self._tool_map.get(func_name)
                    if func is None:
                        result = f"Error: tool '{func_name}' not found"
                    else:
                        try:
                            args = json.loads(tool_call.function.arguments)
                            result = func(**args)
                        except Exception as e:
                            result = f"Error executing {func_name}: {e}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result),
                    })

        return "El agente alcanzó el límite de iteraciones."


async def create_account_agent(settings=None):
    """Create AccountAgent connected to Azure AI Foundry."""
    from agents.tools import (
        get_account_transactions,
        get_customer_accounts,
        search_customer,
        search_products,
    )
    from config.settings import Settings

    if settings is None:
        settings = Settings()

    tools = [search_customer, get_customer_accounts, get_account_transactions, search_products]

    base_url = f"{settings.foundry_project_endpoint.rstrip('/')}/openai/v1"

    if settings.foundry_api_key:
        from openai import AsyncOpenAI
        openai_client = AsyncOpenAI(
            api_key=settings.foundry_api_key,
            base_url=base_url,
        )
    else:
        from azure.identity import AzureCliCredential, get_bearer_token_provider
        from openai import AsyncOpenAI
        credential = AzureCliCredential()
        _sync_token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")

        async def async_token_provider() -> str:
            return _sync_token_provider()

        openai_client = AsyncOpenAI(
            api_key=async_token_provider,
            base_url=base_url,
        )

    return AccountAgent(openai_client=openai_client, model=settings.foundry_model, tools=tools)