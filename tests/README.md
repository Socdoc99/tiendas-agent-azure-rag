# Tests

**Status: IMPLEMENTED local unit and regression coverage; external integration/evaluation suites are not yet established.**

- `tests/unit/` contains isolated API, schema, tenant, document, and Search unit tests using fakes/mocks.
- Root `test_sales.py`, `test_sale_lines.py`, `test_products.py`, and `test_query_engine.py` cover semantic/query-engine behavior without connecting to SQL.
- `test_agent_graph.py`, `test_chat_service.py`, and `test_openai_provider.py` cover tool safety, graph behavior, public history, provider injection, and safe failures with fakes.
- Security/regression assertions are embedded in the tenant, query-engine, agent, and API tests; there is no separate security test package yet.
- Live SQL checks are scripts under `scripts/`, not automatic unit tests. OpenAI/Key Vault smoke tests require authorized external credentials. No golden-question evaluation package exists yet.

Run the project suite with `python -m pytest -q`; run lint with `ruff check .`. See [semantic rules](../docs/SEMANTIC_MODEL.md) and [security boundaries](../docs/SECURITY.md).
