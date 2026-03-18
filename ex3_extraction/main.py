# ex3_extraction/main.py
"""
3 demo documents for Exercise 3:
  1. Complete invoice — all fields present
  2. Contract — many fields absent (should return null, not fabricated)
  3. Invoice with conflicting totals — conflict_detected should be True
"""
from shared.utils import console
from ex3_extraction.extractor import extract_document
from ex3_extraction.schema import DocumentExtraction
from ex3_extraction.validator import validate_extraction, SemanticValidationError, retry_with_feedback

DOCUMENTS = {
    "doc_1_invoice": """
INVOICE #INV-2024-001
Vendor: Acme Supplies Ltd
Date: 2024-03-15

Items:
  Widget A  x2  @ $9.99  = $19.98
  Widget B  x1  @ $29.99 = $29.99

Subtotal: $49.97
Total: $49.97
""",
    "doc_2_contract": """
SERVICE AGREEMENT

This agreement is entered into between TechCorp and ClientCo for ongoing
software maintenance services. Terms and conditions apply as per Schedule A.
Both parties agree to maintain confidentiality.
""",
    "doc_3_conflict": """
INVOICE #INV-2024-002
Vendor: Budget Supplies

Items:
  Part X  x3  @ $10.00 = $30.00
  Part Y  x2  @ $15.00 = $30.00

TOTAL DUE: $55.00
""",
}


def process_document(doc_id: str, text: str) -> None:
    console.rule(f"[bold blue]{doc_id}")
    raw = extract_document(text)
    doc = DocumentExtraction(**raw)

    try:
        validate_extraction(doc)
        console.print("[green]✓ Validation passed[/]")
    except SemanticValidationError as e:
        console.print(f"[yellow]⚠ Semantic error: {e}[/]")
        corrected = retry_with_feedback(text, raw, str(e))
        if corrected:
            doc = DocumentExtraction(**corrected)
            console.print("[green]✓ Corrected after retry[/]")
        else:
            console.print("[red]✗ Max retries exhausted[/]")

    console.print_json(doc.model_dump_json(indent=2))


if __name__ == "__main__":
    for doc_id, text in DOCUMENTS.items():
        process_document(doc_id, text)
