# Runbook

## Local startup

1. Create a local virtual environment and install `requirements-dev.txt`.
2. Configure only this checkout's `.env`; never copy the prototype's local file.
3. Set the demo business and establishment server-side. Do not enable queries until tenant validation succeeds.
4. Run `uvicorn app.main:app --reload` after the POS API migration is ready.
5. Use `/health` for process health and `/ready` for dependencies required by the POS runtime. Search must not be a dependency of POS readiness.

## Database checks

- Use the readonly smoke scripts only with approved credentials, an authorized demo tenant, and access to the expected SQL Server.
- Never paste a connection string or secret into chat or logs.
- Validate tenant membership before interpreting business results.
- A 403 from Key Vault or SQL connectivity failure blocks live validation. Do not bypass it with plaintext `.env` secrets.

## Azure deployment

Check current ARM deployment and Container Apps Environment state before infrastructure operations. Do not run Bicep while either is `Running`/`Updating`; require `what-if` before any future deployment. Phase 9 is gated on an operational Environment.

See `IMPLEMENTATION_LOG.md` for current blockers and phase results.
