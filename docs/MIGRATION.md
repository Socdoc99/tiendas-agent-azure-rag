# Migration plan

## Rebaseline

The product is customer-facing TiendasON business analytics. The validated `Agente IA TiendasON` prototype is the implementation source. Its working tree is read-only during migration; do not transfer Git history, `.git`, `.env`, secrets, or old Azure resources.

The target runtime is SQL-first. Import the tenant, database, semantic views, and guarded query engine before migrating orchestration. Then move the agent/chat, replace the Foundry model runtime with a provider abstraction, validate SQL behavior, add evaluation, and migrate the customer UI. Only after those gates pass can Container Apps deployment begin.

Azure AI Search and Blob remain provisioned, but document RAG is a future capability. Preserve the existing RAG implementation until the SQL replacement is functional and covered by equivalent tests; keep it out of the POS path.

## Phase order

1. **Phase 3 — TiendasON domain:** migrate `tenant.py`, `database/`, `semantic/`, `query_engine/`, and source regression tests. Adapt only imports and secret handling needed by the target repository.
2. **Phase 4 — Agent and chat:** migrate instructions, tools, graph, chat service/store, and public contracts with mocks.
3. **Phase 5 — Model provider:** introduce `LLMProvider` and OpenAI API provider using the approved `gpt-5-mini`; retrieve the key from Key Vault. Keep Foundry code until tests pass.
4. **Phase 6 — Local SQL E2E:** validate readonly queries, tenant isolation, and business questions using authorized configuration.
5. **Phase 7 — Guardrails/evaluation:** golden questions, unsupported-domain refusals, prompt-injection, tenant-tampering, and query-budget tests.
6. **Phase 8 — Customer UI:** migrate the prototype's vanilla JS/CSS/Jinja2 experience.
7. **Phase 9 — Container Apps:** gated by Phases 3–8 and an operational existing Environment.
8. **Phase 10 — Observability.**
9. **Phase 11 — Document RAG**, only after SQL core approval.

## Git workflow

Work only on `develop`, make small Conventional Commits, run focused tests then the applicable suite and lint, inspect diffs, update `IMPLEMENTATION_LOG.md`, and push `origin/develop` when appropriate. Do not merge to or develop on `main`.
