"""Upload and index one local document through the running FastAPI process."""

import argparse
import json
import mimetypes
import sys
from pathlib import Path

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path, help="PDF, DOCX, TXT, or Markdown file")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--metadata", default="{}", help="Document metadata as JSON")
    args = parser.parse_args()
    if not args.file.is_file():
        print("The specified file does not exist.", file=sys.stderr)
        return 2
    try:
        json.loads(args.metadata)
    except json.JSONDecodeError:
        print("Metadata must be valid JSON.", file=sys.stderr)
        return 2

    content_type = mimetypes.guess_type(args.file.name)[0] or "application/octet-stream"
    try:
        with args.file.open("rb") as source, httpx.Client(timeout=300) as client:
            uploaded = client.post(
                f"{args.api_url.rstrip('/')}/api/v1/documents",
                files={"file": (args.file.name, source, content_type)},
                data={"metadata": args.metadata},
            )
            if uploaded.is_error:
                return _print_api_error(uploaded)
            document = uploaded.json()
            indexed = client.post(
                f"{args.api_url.rstrip('/')}/api/v1/documents/{document['document_id']}/index"
            )
            if indexed.is_error:
                return _print_api_error(indexed)
    except httpx.HTTPError as exc:
        print(f"Could not reach the local API: {type(exc).__name__}", file=sys.stderr)
        return 1

    result = indexed.json()
    print(
        f"Document {result['document_id']} indexed; "
        f"status={result['status']}, chunks={result['chunk_count']}."
    )
    return 0


def _print_api_error(response: httpx.Response) -> int:
    try:
        payload = response.json()
        message = payload.get("error", {}).get("message", "Request failed.")
    except (ValueError, AttributeError):
        message = "Request failed."
    print(f"API returned HTTP {response.status_code}: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
