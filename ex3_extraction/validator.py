# ex3_extraction/validator.py
from ex3_extraction.schema import DocumentExtraction


class SemanticValidationError(Exception):
    """Raised when extracted data has semantic inconsistencies."""


def validate_extraction(doc: DocumentExtraction) -> None:
    """
    Validate semantic consistency of extracted data.
    Raises SemanticValidationError with specific details for retry feedback.
    """
    # Check total mismatch only if both values present and conflict not already flagged
    if (
        doc.stated_total is not None
        and doc.calculated_total is not None
        and not doc.conflict_detected
        and abs(doc.stated_total - doc.calculated_total) > 0.01
    ):
        raise SemanticValidationError(
            f"stated_total ({doc.stated_total}) does not match "
            f"calculated_total ({doc.calculated_total}). "
            f"Set conflict_detected=true if this is intentional."
        )


def retry_with_feedback(
    document_text: str,
    failed_extraction: dict,
    validation_error: str,
    max_retries: int = 3,
) -> dict | None:
    """
    Retry extraction by including the specific validation error in the prompt.
    Returns corrected extraction dict or None if max_retries exhausted.
    """
    from shared.client import get_client, MODEL
    from ex3_extraction.schema import get_extraction_tool
    import json

    client = get_client()
    for attempt in range(max_retries):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            tools=[get_extraction_tool()],
            tool_choice={"type": "tool", "name": "extract_document"},
            messages=[{
                "role": "user",
                "content": (
                    f"The previous extraction had a validation error. Please fix it.\n\n"
                    f"ORIGINAL DOCUMENT:\n{document_text}\n\n"
                    f"FAILED EXTRACTION:\n{json.dumps(failed_extraction, indent=2)}\n\n"
                    f"VALIDATION ERROR:\n{validation_error}\n\n"
                    f"Please re-extract with the error corrected."
                )
            }],
        )
        for block in response.content:
            if block.type == "tool_use":
                return block.input
    return None  # exhausted retries
