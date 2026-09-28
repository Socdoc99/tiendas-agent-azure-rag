# Roadmap

| Phase | State | Scope |
|---|---|---|
| 0 | PASS | Preflight |
| 1 | PASS | FastAPI bootstrap |
| 2A | PASS | Existing Azure core infrastructure |
| 2B | PENDING | Container Apps Environment; ARM deployment failed by timeout, Environment still Updating with regional-capacity error |
| Architecture rebaseline | COMPLETE | Customer POS analytics is primary; prototype is migration source; Search RAG is future |
| 3 | PASS (local) | Imported tenant, readonly database, semantic views, query engine, and source regression tests; no live SQL validation |
| 4 | PASS (local) | Imported agent instructions, LangGraph/tool loop, and chat contracts/service; fake-model tests only |
| 5 | PENDING | Replace Foundry runtime with `LLMProvider` / OpenAI `gpt-5-mini` |
| 6 | PENDING | Local SQL end-to-end and tenant isolation validation |
| 7 | PENDING | Guardrails and golden-question evaluation |
| 8 | PENDING | Migrate the customer-facing prototype UI |
| 9 | BLOCKED | Azure Container Apps deployment; require Phases 3–8 green and operational Environment |
| 10 | FUTURE | Application Insights / OpenTelemetry |
| 11 | FUTURE | Document RAG on existing Azure AI Search after SQL-core approval |

Phase 2B blocks only runtime deployment. It does not block local Phases 3–8. Recheck the ARM deployment and Environment before any infrastructure operation. Do not deploy while either is active.

Phase 4 deliberately requires an injected model. Provider construction and runtime model configuration belong to Phase 5; the graph/chat contracts have not called Foundry, OpenAI, or SQL.
