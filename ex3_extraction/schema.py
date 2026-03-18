# ex3_extraction/schema.py
from typing import Literal
from pydantic import BaseModel


class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total: float


class DocumentExtraction(BaseModel):
    # Document classification
    document_type: Literal["invoice", "contract", "report", "other"]
    other_detail: str | None = None  # used when document_type == "other"

    # Core fields
    vendor_name: str
    total_amount: float | None = None   # nullable: document may not contain this
    line_items: list[LineItem] = []
    issue_date: str | None = None       # nullable: may be absent

    # Semantic validation fields
    stated_total: float | None = None      # total as written in the document
    calculated_total: float | None = None  # sum of line items
    conflict_detected: bool = False        # True if stated != calculated


def get_extraction_tool() -> dict:
    """Return the Claude tool definition for structured document extraction."""
    return {
        "name": "extract_document",
        "description": (
            "Extract structured data from an unstructured document. "
            "Set fields to null if the information is not present in the document — "
            "do NOT fabricate values. Set conflict_detected=true if stated_total "
            "does not match the sum of line_items."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "document_type": {
                    "type": "string",
                    "enum": ["invoice", "contract", "report", "other"],
                    "description": "Classification of the document type",
                },
                "other_detail": {
                    "type": "string",
                    "description": "Specific type description when document_type is 'other'",
                },
                "vendor_name": {"type": "string", "description": "Name of the vendor or issuing party"},
                "total_amount": {
                    "type": ["number", "null"],
                    "description": "Total amount in the document, or null if not present",
                },
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "quantity": {"type": "number"},
                            "unit_price": {"type": "number"},
                            "total": {"type": "number"},
                        },
                        "required": ["description", "quantity", "unit_price", "total"],
                    },
                },
                "issue_date": {
                    "type": ["string", "null"],
                    "description": "Document date in ISO format, or null if not present",
                },
                "stated_total": {"type": ["number", "null"]},
                "calculated_total": {"type": ["number", "null"]},
                "conflict_detected": {"type": "boolean"},
            },
            "required": ["document_type", "vendor_name", "conflict_detected"],
        },
    }
