# ex3_extraction/extractor.py
import json
from shared.client import get_client, MODEL
from ex3_extraction.schema import DocumentExtraction, get_extraction_tool


def extract_document(document_text: str) -> dict:
    """
    Extract structured data from document text using forced tool_use.
    Returns raw dict from the tool_use input block.
    """
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        tools=[get_extraction_tool()],
        tool_choice={"type": "tool", "name": "extract_document"},
        messages=[{"role": "user", "content": f"Extract data from this document:\n\n{document_text}"}],
    )
    # Find the tool_use block
    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_document":
            return block.input
    raise RuntimeError("No tool_use block in response — unexpected API behavior")
