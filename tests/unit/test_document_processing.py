from io import BytesIO

import pytest
from pypdf import PdfWriter

from app.core.exceptions import UnsupportedScannedDocumentError
from app.services.document_processing import PageText, extract_pages, split_pages


def test_text_extraction_normalizes_whitespace() -> None:
    pages = extract_pages(b"  Uno\t dos  \r\n\r\n Tres\n", "txt")

    assert len(pages) == 1
    assert pages[0].page is None
    assert pages[0].text == "Uno dos\nTres"


def test_chunking_is_stable_and_preserves_page_numbers() -> None:
    page = PageText(page=7, text="operacion " * 1000)

    first = split_pages([page], document_id="manual", version="v1", chunk_size=100, overlap=20)
    second = split_pages([page], document_id="manual", version="v1", chunk_size=100, overlap=20)

    assert len(first) > 1
    assert [chunk.content_hash for chunk in first] == [chunk.content_hash for chunk in second]
    assert all(chunk.page == 7 for chunk in first)
    assert [chunk.chunk_number for chunk in first] == list(range(len(first)))


def test_scanned_pdf_without_text_layer_is_rejected() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    output = BytesIO()
    writer.write(output)

    with pytest.raises(UnsupportedScannedDocumentError):
        extract_pages(output.getvalue(), "pdf")
