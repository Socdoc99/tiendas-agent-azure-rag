# Data model

Each indexed record represents one document chunk. The schema includes a stable chunk ID, document ID and name, text, content hash, page and chunk order, business metadata, active version flag, source location, creation time, and allowed groups for future document-level authorization.

The Azure AI Search index name is configured as `AZURE_SEARCH_INDEX`; the initial sandbox value is `idx-tiendas-knowledge-v1`. Embedding vector dimensions come from `EMBEDDING_DIMENSIONS` and must match the configured embedding model.
