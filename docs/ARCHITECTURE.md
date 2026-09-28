# Architecture

The MVP uses a FastAPI service, private Azure Blob Storage, Azure AI Search hybrid retrieval, a configurable OpenAI-compatible LLM provider, Azure Key Vault, and Azure Container Apps.

```text
Browser -> FastAPI -> Azure AI Search -> configured LLM provider
                    -> Blob Storage
                    -> Key Vault (runtime API key)
```

The LLM provider and embedding provider are interfaces so that model services can change without coupling the application to Foundry. The existing Foundry account is outside this application's runtime and is not modified by this project.

The initial application bootstrap exposes health and configuration readiness checks. Document ingestion, search, RAG, UI, and deployment are implemented in later phases; consult `IMPLEMENTATION_LOG.md` for their status.
