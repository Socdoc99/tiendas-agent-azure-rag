from app.services.llm import _remove_invalid_citations, format_context, used_citations


def test_context_maps_only_real_source_identifiers() -> None:
    context, citations = format_context(
        [
            {
                "document_id": "ops-v1",
                "document_name": "Manual.pdf",
                "page": 8,
                "chunk_number": 3,
                "category": "manual",
                "content": "Abrir la tienda.",
            }
        ]
    )

    assert "[S1]" in context
    assert "<contenido no confiable>" in context
    assert used_citations("Se abre asi [S1] [S9]", citations) == [citations[0]]
    assert _remove_invalid_citations("Respuesta [S1] [S9]", context) == "Respuesta [S1]"
