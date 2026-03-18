# tests/test_ex3_schema.py
import pytest
from ex3_extraction.schema import DocumentExtraction, LineItem, get_extraction_tool


def test_line_item_valid():
    item = LineItem(description="Widget A", quantity=2, unit_price=9.99, total=19.98)
    assert item.total == 19.98


def test_extraction_nullable_fields_default_none():
    doc = DocumentExtraction(vendor_name="Acme", document_type="invoice")
    assert doc.total_amount is None
    assert doc.issue_date is None
    assert doc.conflict_detected is False


def test_extraction_other_type_requires_detail():
    doc = DocumentExtraction(
        vendor_name="Acme",
        document_type="other",
        other_detail="purchase order",
    )
    assert doc.other_detail == "purchase order"


def test_extraction_conflict_detection():
    doc = DocumentExtraction(
        vendor_name="Acme",
        document_type="invoice",
        stated_total=100.0,
        calculated_total=90.0,
        conflict_detected=True,
    )
    assert doc.conflict_detected is True


def test_get_extraction_tool_schema():
    tool = get_extraction_tool()
    assert tool["name"] == "extract_document"
    assert "input_schema" in tool
    # vendor_name is required
    assert "vendor_name" in tool["input_schema"]["required"]
    # total_amount is NOT required (nullable)
    assert "total_amount" not in tool["input_schema"].get("required", [])
