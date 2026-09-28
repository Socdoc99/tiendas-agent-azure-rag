"""Explicit LangGraph agent/tools loop for Issue #9."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError

from app.agent.instructions import AGENT_INSTRUCTIONS
from app.agent.tools import LogicalQueryInput, QueryExecutor, create_query_database_tool
from app.core.config import Settings
from app.llm import LLMProvider
from app.query_engine import query_database
from app.query_engine.validator import validate_logical_sql
from app.tenant import TenantContext

MAX_QUERY_DATABASE_ATTEMPTS = 10
_LIMIT_INSTRUCTION = (
    "Ya alcanzaste el límite de consultas. No puedes consultar más datos. "
    "Responde usando únicamente la evidencia disponible y sé explícito si no alcanza."
)


class AgentState(MessagesState):
    """Serializable conversational state suitable for future hosting."""

    query_count: int


class AgentGraphError(RuntimeError):
    """Base class for safe graph orchestration errors."""


class EmptyFinalResponseError(AgentGraphError):
    """Raised when the graph finishes without natural-language text."""


@dataclass(frozen=True)
class QueryAttempt:
    """Diagnostic evidence from one model-requested query."""

    logical_sql: str | None
    semantic_view: str | None
    output: dict[str, Any]


@dataclass(frozen=True)
class AgentRunResult:
    """High-level result of one isolated user question."""

    final_answer: str
    query_count: int
    attempts: tuple[QueryAttempt, ...]


def _business_context(settings: Settings) -> str:
    try:
        current = datetime.now(ZoneInfo(settings.business_timezone))
    except Exception as error:
        raise AgentGraphError("BUSINESS_TIMEZONE is invalid.") from error
    return f"Fecha/hora actual del negocio:\n{current.isoformat()}"


def _tool_error(code: str, message: str) -> str:
    return json.dumps({"error": code, "message": message}, ensure_ascii=False)


def _message_text(message: BaseMessage) -> str:
    if isinstance(message.content, str):
        return message.content.strip()
    parts: list[str] = []
    for block in message.content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and isinstance(block.get("text"), str):
            parts.append(block["text"])
    return "\n".join(parts).strip()


def build_agent_graph(
    settings: Settings,
    tenant: TenantContext,
    model: Any | None = None,
    provider: LLMProvider | None = None,
    query_executor: QueryExecutor = query_database,
) -> CompiledStateGraph:
    """Build the two-node graph with a hard per-question query budget."""

    if model is not None and provider is not None:
        raise AgentGraphError("Pass either a model or a provider, not both.")

    if model is None:
        if provider is None:
            raise AgentGraphError("An LLM provider must be injected into the agent graph.")
        try:
            model = provider.get_chat_model()
        except Exception as error:
            raise AgentGraphError("The model provider could not be initialized.") from error

    tool = create_query_database_tool(
        tenant=tenant,
        settings=settings,
        query_executor=query_executor,
    )
    try:
        model_with_tools = model.bind_tools(
            [tool],
            strict=True,
            parallel_tool_calls=False,
        )
    except Exception as error:
        raise AgentGraphError("The model does not support the required tool contract.") from error

    def agent_node(state: AgentState) -> dict[str, list[AIMessage]]:
        query_count = min(
            max(int(state.get("query_count", 0)), 0),
            MAX_QUERY_DATABASE_ATTEMPTS,
        )
        instructions = f"{AGENT_INSTRUCTIONS}\n\n{_business_context(settings)}"
        active_model = model_with_tools
        if query_count >= MAX_QUERY_DATABASE_ATTEMPTS:
            instructions = f"{instructions}\n\n{_LIMIT_INSTRUCTION}"
            active_model = model
        try:
            response = active_model.invoke(
                [SystemMessage(content=instructions), *state["messages"]]
            )
        except Exception as error:
            raise AgentGraphError("The model provider request failed.") from error
        if not isinstance(response, AIMessage):
            raise AgentGraphError("The model did not return an AIMessage.")
        return {"messages": [response]}

    def tools_node(state: AgentState) -> dict[str, object]:
        last = state["messages"][-1]
        if not isinstance(last, AIMessage):
            raise AgentGraphError("The tools node requires a final AIMessage.")

        count = min(
            max(int(state.get("query_count", 0)), 0),
            MAX_QUERY_DATABASE_ATTEMPTS,
        )
        outputs: list[ToolMessage] = []
        for index, call in enumerate(last.tool_calls):
            name = call.get("name")
            call_id = str(call.get("id") or f"invalid-call-{index}")
            if name != "query_database":
                content = _tool_error(
                    "unsupported_tool",
                    "Only query_database is available.",
                )
            elif count >= MAX_QUERY_DATABASE_ATTEMPTS:
                content = _tool_error(
                    "query_limit_reached",
                    "The query limit for this question was reached.",
                )
            else:
                count += 1
                try:
                    arguments = LogicalQueryInput.model_validate(call.get("args", {}))
                    content = tool.invoke(arguments.model_dump())
                except ValidationError:
                    content = _tool_error(
                        "invalid_tool_arguments",
                        "The query_database arguments were rejected.",
                    )
            outputs.append(
                ToolMessage(
                    content=content,
                    tool_call_id=call_id,
                    name=str(name or "unknown"),
                )
            )
        return {"messages": outputs, "query_count": count}

    def route_after_agent(state: AgentState) -> Literal["tools", "__end__"]:
        last = state["messages"][-1]
        if (
            isinstance(last, AIMessage)
            and last.tool_calls
            and int(state.get("query_count", 0)) < MAX_QUERY_DATABASE_ATTEMPTS
        ):
            return "tools"
        return END

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tools_node)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route_after_agent)
    builder.add_edge("tools", "agent")
    graph = builder.compile()
    if provider is not None:
        graph._tiendason_llm_provider = provider
    return graph


def close_agent_graph(graph: CompiledStateGraph) -> None:
    """Close a provider client explicitly attached to this graph, if any."""

    provider = getattr(graph, "_tiendason_llm_provider", None)
    if provider is not None:
        provider.close()
        graph._tiendason_llm_provider = None


def _query_attempts(messages: list[BaseMessage]) -> tuple[QueryAttempt, ...]:
    calls: dict[str, dict[str, Any]] = {}
    attempts: list[QueryAttempt] = []
    for message in messages:
        if isinstance(message, AIMessage):
            for call in message.tool_calls:
                if call.get("name") == "query_database" and call.get("id"):
                    calls[str(call["id"])] = call
        elif isinstance(message, ToolMessage) and message.tool_call_id in calls:
            call = calls[message.tool_call_id]
            logical_sql = call.get("args", {}).get("logical_sql")
            view = None
            if isinstance(logical_sql, str):
                try:
                    view = validate_logical_sql(logical_sql).semantic_view
                except Exception:
                    pass
            try:
                output = json.loads(_message_text(message))
            except (json.JSONDecodeError, TypeError):
                output = {"error": "invalid_tool_output"}
            attempts.append(
                QueryAttempt(
                    logical_sql=logical_sql if isinstance(logical_sql, str) else None,
                    semantic_view=view,
                    output=output,
                )
            )
    return tuple(attempts)


def run_agent_question(
    graph: CompiledStateGraph,
    question: str,
) -> AgentRunResult:
    """Run a fresh question and return its final answer plus safe diagnostics."""

    return run_agent_turn(graph, question, history=[])


def run_agent_turn(
    graph: CompiledStateGraph,
    question: str,
    history: Sequence[HumanMessage | AIMessage] | None = None,
) -> AgentRunResult:
    """Run one question with public Human/AI history and a fresh query budget."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")

    public_history = list(history) if history is not None else []
    for message in public_history:
        if not isinstance(message, (HumanMessage, AIMessage)):
            raise ValueError("history must contain only HumanMessage and AIMessage")
        if isinstance(message, AIMessage) and message.tool_calls:
            raise ValueError("history must not contain tool calls")

    state = graph.invoke(
        {
            "messages": [*public_history, HumanMessage(content=question.strip())],
            "query_count": 0,
        }
    )
    messages = state["messages"]
    final = messages[-1]
    if not isinstance(final, AIMessage) or final.tool_calls:
        raise EmptyFinalResponseError("The graph returned no final AI response.")
    final_answer = _message_text(final)
    if not final_answer:
        raise EmptyFinalResponseError("The model returned an empty final response.")
    query_count = int(state.get("query_count", 0))
    if not 0 <= query_count <= MAX_QUERY_DATABASE_ATTEMPTS:
        raise AgentGraphError("The graph returned an invalid query_count.")
    return AgentRunResult(
        final_answer=final_answer,
        query_count=query_count,
        attempts=_query_attempts(messages),
    )
