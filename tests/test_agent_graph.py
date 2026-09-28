"""Focused tests for the explicit Issue #9 LangGraph loop."""

import json
import unittest
from datetime import datetime
from typing import get_type_hints
from unittest.mock import Mock, patch
from uuid import UUID
from zoneinfo import ZoneInfo

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from app.agent.graph import (
    MAX_QUERY_DATABASE_ATTEMPTS,
    AgentState,
    EmptyFinalResponseError,
    build_agent_graph,
    run_agent_question,
)
from app.agent.tools import create_query_database_tool
from app.core.config import Settings
from app.query_engine import QueryExecutionError, QueryResult, QueryValidationError
from app.tenant import TenantContext


def _tool_call(sql: str, call_id: str, name: str = "query_database") -> dict:
    return {
        "name": name,
        "args": {"logical_sql": sql},
        "id": call_id,
        "type": "tool_call",
    }


class _BoundModel:
    def __init__(self, parent: "_FakeModel") -> None:
        self.parent = parent

    def invoke(self, messages: list[object]) -> AIMessage:
        return self.parent._invoke(messages, tools_enabled=True)


class _FakeModel:
    def __init__(self, responses: list[AIMessage]) -> None:
        self.responses = responses
        self.calls: list[tuple[bool, list[object]]] = []
        self.bind_kwargs: dict[str, object] = {}
        self.bound_tools: list[object] = []

    def bind_tools(self, tools: list[object], **kwargs: object) -> _BoundModel:
        self.bound_tools = tools
        self.bind_kwargs = kwargs
        return _BoundModel(self)

    def invoke(self, messages: list[object]) -> AIMessage:
        return self._invoke(messages, tools_enabled=False)

    def _invoke(self, messages: list[object], *, tools_enabled: bool) -> AIMessage:
        self.calls.append((tools_enabled, messages))
        return self.responses.pop(0)


class LangGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            sql_server="server",
            sql_database="database",
            sql_username="user",
            business_timezone="America/Bogota",
        )
        self.tenant = TenantContext(
            business_id=UUID("11111111-1111-1111-1111-111111111111"),
            establishment_id=UUID("22222222-2222-2222-2222-222222222222"),
            timezone="America/Bogota",
        )
        self.result = QueryResult(
            columns=["total"], rows=[["1000.00"]], row_count=1, truncated=False
        )

    def _graph(self, model: _FakeModel, executor: object | None = None):
        return build_agent_graph(
            self.settings,
            self.tenant,
            model=model,
            query_executor=executor or Mock(return_value=self.result),
        )

    def test_state_and_graph_have_only_required_concepts(self) -> None:
        state_hints = get_type_hints(AgentState)
        self.assertIn("messages", state_hints)
        self.assertIn("query_count", state_hints)
        graph = self._graph(_FakeModel([AIMessage(content="Hola")]))
        self.assertEqual(
            set(graph.get_graph().nodes),
            {"__start__", "agent", "tools", "__end__"},
        )

    def test_graph_requires_configured_provider_and_does_not_fallback(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "LLM provider must be injected"):
            build_agent_graph(self.settings, self.tenant)

    def test_tool_schema_exposes_only_logical_sql_and_binds_server_context(self) -> None:
        executor = Mock(return_value=self.result)
        tool = create_query_database_tool(
            tenant=self.tenant,
            settings=self.settings,
            query_executor=executor,
        )
        schema = tool.tool_call_schema.model_json_schema()
        self.assertEqual(set(schema["properties"]), {"logical_sql"})
        serialized = json.dumps(schema).lower()
        for forbidden in ("business_id", "establishment_id", "tenant", "settings"):
            self.assertNotIn(forbidden, serialized)

        output = json.loads(tool.invoke({"logical_sql": "SELECT COUNT(*) FROM ventas"}))
        self.assertEqual(output, self.result.model_dump())
        executor.assert_called_once_with(
            "SELECT COUNT(*) FROM ventas",
            tenant=self.tenant,
            settings=self.settings,
        )

    def test_tool_sanitizes_validation_and_execution_errors(self) -> None:
        for error, code in (
            (QueryValidationError("secret SQL"), "query_validation_error"),
            (QueryExecutionError("secret connection"), "query_execution_error"),
        ):
            with self.subTest(code=code):
                tool = create_query_database_tool(
                    tenant=self.tenant,
                    settings=self.settings,
                    query_executor=Mock(side_effect=error),
                )
                output = json.loads(tool.invoke({"logical_sql": "SELECT * FROM ventas"}))
                self.assertEqual(output["error"], code)
                self.assertNotIn("secret", json.dumps(output))

    def test_no_tool_call_ends_and_query_count_starts_at_zero(self) -> None:
        model = _FakeModel([AIMessage(content="¡Hola! ¿En qué te ayudo?")])
        result = run_agent_question(self._graph(model), "Hola")
        self.assertEqual(result.query_count, 0)
        self.assertEqual(len(model.calls), 1)

    def test_loop_recovers_after_sanitized_tool_error(self) -> None:
        invalid = "SELECT * FROM desconocida"
        valid = "SELECT COUNT(*) AS tickets FROM ventas"
        model = _FakeModel(
            [
                AIMessage(content="", tool_calls=[_tool_call(invalid, "call-1")]),
                AIMessage(content="", tool_calls=[_tool_call(valid, "call-2")]),
                AIMessage(content="Tuviste 2 tickets."),
            ]
        )
        executor = Mock(
            side_effect=[
                QueryValidationError("physical SQL and tenant secret"),
                QueryResult(columns=["tickets"], rows=[[2]], row_count=1, truncated=False),
            ]
        )
        result = run_agent_question(self._graph(model, executor), "¿Cuántos tickets?")

        self.assertEqual(result.query_count, 2)
        self.assertEqual(len(executor.call_args_list), 2)
        second_prompt = model.calls[1][1]
        error_message = next(m for m in second_prompt if isinstance(m, ToolMessage))
        error = json.loads(error_message.content)
        self.assertEqual(error["error"], "query_validation_error")
        self.assertNotIn("secret", error_message.content)

    def test_two_queries_can_use_different_views_separately(self) -> None:
        sales_sql = "SELECT SUM(total_facturado) AS total FROM ventas"
        products_sql = "SELECT COUNT(*) AS productos FROM productos"
        model = _FakeModel(
            [
                AIMessage(content="", tool_calls=[_tool_call(sales_sql, "sales")]),
                AIMessage(content="", tool_calls=[_tool_call(products_sql, "products")]),
                AIMessage(content="Vendiste 1000 y tienes 20 productos activos."),
            ]
        )
        executor = Mock(
            side_effect=[
                self.result,
                QueryResult(columns=["productos"], rows=[[20]], row_count=1, truncated=False),
            ]
        )
        result = run_agent_question(self._graph(model, executor), "Ventas y productos")
        self.assertEqual(result.query_count, 2)
        self.assertEqual(
            [attempt.semantic_view for attempt in result.attempts], ["ventas", "productos"]
        )
        self.assertTrue(
            all(" JOIN " not in call.args[0].upper() for call in executor.call_args_list)
        )

    def test_unknown_tool_is_not_executed(self) -> None:
        model = _FakeModel(
            [
                AIMessage(
                    content="",
                    tool_calls=[_tool_call("SELECT * FROM ventas", "bad", "other")],
                ),
                AIMessage(content="No pude consultar."),
            ]
        )
        executor = Mock(return_value=self.result)
        result = run_agent_question(self._graph(model, executor), "Pregunta")
        executor.assert_not_called()
        self.assertEqual(result.query_count, 0)
        tool_message = next(m for m in model.calls[1][1] if isinstance(m, ToolMessage))
        self.assertEqual(json.loads(tool_message.content)["error"], "unsupported_tool")

    def test_hard_limit_never_executes_attempt_eleven(self) -> None:
        calls = [
            AIMessage(
                content="",
                tool_calls=[
                    _tool_call(
                        "SELECT COUNT(*) AS tickets FROM ventas",
                        f"call-{index}",
                    )
                ],
            )
            for index in range(MAX_QUERY_DATABASE_ATTEMPTS)
        ]
        calls.append(AIMessage(content="La evidencia sigue siendo insuficiente."))
        model = _FakeModel(calls)
        executor = Mock(return_value=self.result)
        result = run_agent_question(self._graph(model, executor), "Insiste")

        self.assertEqual(result.query_count, MAX_QUERY_DATABASE_ATTEMPTS)
        self.assertEqual(executor.call_count, MAX_QUERY_DATABASE_ATTEMPTS)
        self.assertEqual([enabled for enabled, _ in model.calls[:-1]], [True] * 10)
        self.assertFalse(model.calls[-1][0])
        final_system = model.calls[-1][1][0]
        self.assertIsInstance(final_system, SystemMessage)
        self.assertIn("límite de consultas", final_system.content)

    def test_multiple_calls_cannot_exceed_remaining_budget(self) -> None:
        model = _FakeModel(
            [
                AIMessage(
                    content="",
                    tool_calls=[
                        _tool_call("SELECT COUNT(*) FROM ventas", f"call-{n}") for n in range(3)
                    ],
                ),
                AIMessage(content="Respuesta final."),
            ]
        )
        executor = Mock(return_value=self.result)
        graph = self._graph(model, executor)
        state = graph.invoke({"messages": [("user", "Pregunta")], "query_count": 9})
        self.assertEqual(state["query_count"], 10)
        executor.assert_called_once()
        tool_errors = [
            json.loads(message.content).get("error")
            for message in state["messages"]
            if isinstance(message, ToolMessage)
        ]
        self.assertEqual(tool_errors, [None, "query_limit_reached", "query_limit_reached"])

    def test_empty_final_answer_fails(self) -> None:
        with self.assertRaises(EmptyFinalResponseError):
            run_agent_question(self._graph(_FakeModel([AIMessage(content="  ")])), "Hola")

    def test_business_datetime_uses_configured_timezone(self) -> None:
        observed: list[ZoneInfo] = []

        class _Datetime:
            @classmethod
            def now(cls, tz: ZoneInfo) -> datetime:
                observed.append(tz)
                return datetime(2026, 9, 15, 12, 30, tzinfo=tz)

        model = _FakeModel([AIMessage(content="Hola")])
        with patch("app.agent.graph.datetime", _Datetime):
            run_agent_question(self._graph(model), "Hola")
        self.assertEqual(observed, [ZoneInfo("America/Bogota")])
        system = model.calls[0][1][0]
        self.assertIn("2026-09-15T12:30:00-05:00", system.content)

    def test_model_is_configured_for_sequential_tool_calls(self) -> None:
        model = _FakeModel([AIMessage(content="Hola")])
        self._graph(model)
        self.assertEqual(model.bind_kwargs["parallel_tool_calls"], False)
        self.assertEqual(model.bind_kwargs["strict"], True)


if __name__ == "__main__":
    unittest.main()
