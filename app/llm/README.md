# Model providers

**Status: IMPLEMENTED (provider boundary and OpenAI adapter).**

`base.py` defines `LLMProvider`; `OpenAIProvider` creates the tool-capable chat model from `OPENAI_CHAT_MODEL` and resolves `OPENAI_API_KEY_SECRET_NAME` through Key Vault. The graph accepts an injected provider/model so tests do not call OpenAI.

The configured model is `gpt-5-mini` in `.env.example`; the setting remains environment-configurable. API keys must never be hardcoded, logged, tested with real values, or committed. Provider/configuration failures are controlled; there is no automatic model fallback.

This POS provider is separate from the document-RAG client in `app/services/llm.py`, which remains part of the legacy path.

The target application has no Foundry runtime fallback. The existing Foundry resources and prototype implementation remain untouched for comparison; they are outside this provider path. See [security](../../docs/SECURITY.md) and [architecture](../../docs/ARCHITECTURE.md).
