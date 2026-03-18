# tests/test_ex1_tools.py
import pytest
from ex1_agent.tools import (
    get_customer, lookup_order, process_refund, escalate_to_human,
    TOOL_DEFINITIONS,
)


def test_get_customer_found():
    result = get_customer("john@example.com")
    assert result["customer_id"] == "C001"
    assert "verified" in result


def test_get_customer_not_found():
    result = get_customer("unknown@example.com")
    assert result["errorCategory"] == "validation"
    assert result["isRetryable"] is False


def test_lookup_order_success():
    result = lookup_order("ORD-001")
    assert result["order_id"] == "ORD-001"
    assert "status" in result


def test_lookup_order_not_found():
    result = lookup_order("ORD-999")
    assert result["errorCategory"] == "validation"


def test_process_refund_success():
    result = process_refund("C001", "ORD-001", 49.99)
    assert result["status"] == "approved"
    assert result["refund_amount"] == 49.99


def test_process_refund_transient_error():
    # amount == 0 triggers simulated transient error
    result = process_refund("C001", "ORD-001", 0.0)
    assert result["errorCategory"] == "transient"
    assert result["isRetryable"] is True


def test_escalate_to_human():
    result = escalate_to_human("C001", "ORD-001", "Refund exceeds threshold", "REFUND_THRESHOLD")
    assert result["status"] == "escalated"
    assert result["ticket_id"].startswith("TKT-")


def test_tool_definitions_have_descriptions():
    for tool in TOOL_DEFINITIONS:
        assert len(tool["description"]) > 50, f"{tool['name']} description too short"
        assert "input_schema" in tool
