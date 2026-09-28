# Runbook

## Local startup

1. Create a Python virtual environment and install `requirements-dev.txt`.
2. Copy `.env.example` to `.env` and configure the required service endpoints and model names.
3. Run `uvicorn app.main:app --reload`.
4. Check `/health` for process health and `/ready` for required configuration.

## Current operational state

Only the bootstrap API is implemented at this point. Azure Search, Blob, Key Vault, ingestion, and LLM checks will be added by their implementation phases. See `IMPLEMENTATION_LOG.md` for completed phases and blockers.
