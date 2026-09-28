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
| 5 | PASS (local); real smoke BLOCKED BY RBAC | `LLMProvider` / `OpenAIProvider`, configured `gpt-5-mini`; Key Vault secret existence could not be verified |
| 6 | PENDING | Local SQL end-to-end and tenant isolation validation |
| 7 | PENDING | Guardrails and golden-question evaluation |
| 8 | PENDING | Migrate the customer-facing prototype UI |
| 9 | BLOCKED | Azure Container Apps deployment; require Phases 3–8 green and operational Environment |
| 10 | FUTURE | Application Insights / OpenTelemetry |
| 11 | FUTURE | Document RAG on existing Azure AI Search after SQL-core approval |

Phase 2B blocks only runtime deployment. It does not block local Phases 3–8. Recheck the ARM deployment and Environment before any infrastructure operation. Do not deploy while either is active.

Phase 4 graph/chat contracts were validated with injected fakes. Phase 5 now provides the configurable OpenAI provider and no model fallback. Its unit tests do not call OpenAI; Key Vault denied secret metadata/value access, so the real smoke remains blocked.
