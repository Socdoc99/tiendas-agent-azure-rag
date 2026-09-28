# Scripts

Scripts are grouped by operational effect:

- **Local development:** `workflow.bat` prepares the venv, runs local checks, and starts the local API. Its Docker build is local and gated by Phase 9.
- **Read-only validation:** `check_sales_view.py`, `check_sale_lines_view.py`, and `check_products_view.py` query SQL Server to compare semantic views with readonly oracles. They require configured tenant/database access; do not run against live data without authorization.
- **Azure diagnostics:** menu option 6 in `workflow.bat` reads resource/deployment state. Option 7 validates and runs Bicep what-if; it does not apply a deployment.
- **Azure writes:** `create_search_index.py` creates or updates an Azure AI Search index. Run only under an explicitly authorized Search task.
- **Ingestion/smoke:** `ingest_document.py` uploads and indexes a document through the running API, changing Blob/Search data. It is not a POS analytics test.

Do not treat diagnostics, what-if, or local Docker build as a deployment. See [deployment boundaries](../docs/DEPLOYMENT.md).
