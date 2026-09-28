from app.services.search import _build_filter


def test_filter_always_requires_active_documents_and_escapes_strings() -> None:
    expression = _build_filter(
        {"country": "CO", "store_id": "Norte's", "category": None, "unknown": "ignored"}
    )

    assert expression == "is_active eq true and country eq 'CO' and store_id eq 'Norte''s'"
