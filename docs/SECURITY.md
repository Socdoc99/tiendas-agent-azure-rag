# Security

- Keep `.env`, API keys, access tokens, and connection strings with values out of Git.
- Store runtime API keys in Azure Key Vault and use managed identity for Azure services.
- Keep document storage private.
- Do not log prompts, document bodies, vectors, authorization headers, or secrets.
- Validate file type, file size, question length, and metadata before processing.
- Treat retrieved document text as untrusted input and never let it override system instructions.

The current bootstrap logs request identifiers, route, status, latency, and error type. Azure identity and service access are wired in later phases.
