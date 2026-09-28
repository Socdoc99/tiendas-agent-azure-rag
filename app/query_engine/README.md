# Logical query engine

**Status: IMPLEMENTED and covered by regression tests.**

The pipeline is:

`logical SQL -> validator -> compiler -> tenant injection -> readonly SQL -> bounded result`

The validator permits one query over exactly one allowlisted semantic view and rejects physical tables, unsafe statements, and unsupported constructs. The compiler injects trusted view SQL and server-side tenant parameters; the database connector uses readonly SQL Server settings. Row count is bounded and truncation is reported.

The goal is to prevent free-form SQL access by the LLM. Do not bypass validation or accept tenant IDs from model arguments. See [semantic model](../../docs/SEMANTIC_MODEL.md) and [security](../../docs/SECURITY.md).
