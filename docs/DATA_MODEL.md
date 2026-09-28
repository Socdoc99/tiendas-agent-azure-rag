# Data model

## Current POS domain

The operational database is the primary product data source. The trusted semantic views and their grains are documented in [SEMANTIC_MODEL.md](SEMANTIC_MODEL.md). This application must never expose the physical database schema to the model.

## Future document index

Azure AI Search remains provisioned for a later document knowledge capability. Its chunk schema is not part of the POS analytics path. Do not add Search dependencies to the database agent's readiness checks or query flow. The existing index and storage implementation may be retained until the SQL agent is validated and the document phase is explicitly resumed.
