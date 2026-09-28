from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)


def build_search_index(name: str, dimensions: int) -> SearchIndex:
    if dimensions <= 0:
        raise ValueError("Embedding dimensions must be a positive integer.")

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
        SearchableField(name="document_name", filterable=True),
        SearchableField(name="content"),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            hidden=True,
            stored=False,
            vector_search_dimensions=dimensions,
            vector_search_profile_name="vector-profile",
        ),
        SimpleField(name="content_hash", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="page", type=SearchFieldDataType.Int32, filterable=True),
        SimpleField(name="chunk_number", type=SearchFieldDataType.Int32, filterable=True),
        SearchableField(name="category", filterable=True),
        SearchableField(name="department", filterable=True),
        SimpleField(name="country", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="store_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="language", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="version", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="is_active", type=SearchFieldDataType.Boolean, filterable=True),
        SimpleField(name="source_path", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="source_url", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, filterable=True),
        SimpleField(
            name="allowed_groups",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
        ),
    ]
    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-cosine")],
        profiles=[
            VectorSearchProfile(
                name="vector-profile", algorithm_configuration_name="hnsw-cosine"
            )
        ],
    )
    return SearchIndex(name=name, fields=fields, vector_search=vector_search)
