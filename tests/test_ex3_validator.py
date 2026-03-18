# tests/test_ex3_validator.py
import pytest
from ex3_extraction.validator import validate_extraction, SemanticValidationError
from ex3_extraction.schema import DocumentExtraction, LineItem


def test_validate_passes_clean_extraction():
    doc = DocumentExtraction(
        vendor_name="Acme",
        document_type="invoice",
        stated_total=100.0,
        calculated_total=100.0,
    )
    validate_extraction(doc)  # should not raise


def test_validate_detects_total_mismatch():
    doc = DocumentExtraction(
        vendor_name="Acme",
        document_type="invoice",
        stated_total=100.0,
        calculated_total=90.0,
        conflict_detected=False,  # model forgot to set this
    )
    with pytest.raises(SemanticValidationError, match="stated_total"):
        validate_extraction(doc)


def test_validate_passes_when_totals_absent():
    # If no totals provided, nothing to conflict
    doc = DocumentExtraction(vendor_name="Acme", document_type="contract")
    validate_extraction(doc)  # should not raise


def test_validate_passes_conflict_flagged_correctly():
    doc = DocumentExtraction(
        vendor_name="Acme",
        document_type="invoice",
        stated_total=100.0,
        calculated_total=90.0,
        conflict_detected=True,  # correctly flagged
    )
    validate_extraction(doc)  # conflict is known, so no error


def test_validate_error_contains_details():
    doc = DocumentExtraction(
        vendor_name="Acme",
        document_type="invoice",
        stated_total=100.0,
        calculated_total=90.0,
    )
    with pytest.raises(SemanticValidationError) as exc_info:
        validate_extraction(doc)
    assert "100.0" in str(exc_info.value)
    assert "90.0" in str(exc_info.value)
