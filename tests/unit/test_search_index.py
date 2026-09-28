import pytest

from app.services.search_index import build_search_index


def test_index_has_hybrid_schema_and_configured_vector_size() -> None:
    index = build_search_index("idx-test", 3072)
    fields = {field.name: field for field in index.fields}

    assert fields["id"].key is True
    assert fields["is_active"].filterable is True
    assert fields["content_vector"].vector_search_dimensions == 3072
    assert fields["content_vector"].hidden is True
    assert fields["content_vector"].stored is False
    assert index.vector_search.profiles[0].name == "vector-profile"


def test_index_rejects_invalid_embedding_dimensions() -> None:
    with pytest.raises(ValueError):
        build_search_index("idx-test", 0)
