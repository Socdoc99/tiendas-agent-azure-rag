# Security

## Tenant isolation

- Build immutable `TenantContext` server-side from the approved business and establishment configuration.
- Validate that the configured establishment belongs to the configured business before enabling queries.
- Never accept `business_id` or `establishment_id` from the browser, user prompt, or model tool arguments.
- Inject tenant parameters in trusted SQL after validation. Do not expose tenant IDs in responses or logs.

## SQL boundary

- Connect with ODBC Driver 18, `ApplicationIntent=ReadOnly`, and `readonly=True`.
- Permit one T-SQL `SELECT` over exactly one registered semantic view: `ventas`, `venta_lineas`, or `productos`.
- Reject physical tables and schemas, DDL/DML, multiple statements, external access functions, system metadata access, and unsupported views.
- Use explicit parameter binding for tenant and query values. Limit results with `SQL_MAX_ROWS` (default 200), fetch one extra row, and indicate truncation.
- Do not let current product cost answer historical profit or margin questions.

## Secrets and logs

- Keep `.env`, API keys, SQL passwords, access tokens, and connection strings with values out of Git and logs.
- Read SQL and OpenAI credentials from Azure Key Vault at runtime. Secret names may appear in examples; values must not.
- Never print SQL connection strings, prompts containing business data, query results, PII, secrets, or unnecessary tenant identifiers.
- Expose safe error categories and request IDs, not tracebacks or provider diagnostics.

## Prompt and tool controls

- The model receives only the logical query contract, not physical schema details or tenant values.
- Strictly validate tool arguments and reject extra tenant fields.
- Disable parallel database tool calls and cap each user turn at 10 queries.
- Treat user prompts and retrieved documentation as untrusted. Unsupported business domains must receive a brief, honest limitation.

## Current limits

The local demo tenant is configuration, not production authentication. Production identity must come from TiendasON's existing customer login/session. Microsoft Entra ID is not assumed to be the customer identity system. Document-level RBAC and Azure AI Search are future capabilities.
