import pytest
from shared.types import ToolError, make_tool_result
from shared.client import get_client


def test_tool_error_structure():
    err = ToolError(
        errorCategory="transient",
        isRetryable=True,
        message="Service unavailable"
    )
    assert err.errorCategory == "transient"
    assert err.isRetryable is True


def test_tool_error_invalid_category():
    with pytest.raises(ValueError):
        ToolError(errorCategory="unknown", isRetryable=False, message="x")


def test_make_tool_result_success():
    result = make_tool_result("tool_123", {"customer_id": "C1"})
    assert result["type"] == "tool_result"
    assert result["tool_use_id"] == "tool_123"
    assert result["content"] == '{"customer_id": "C1"}'


def test_make_tool_result_error():
    result = make_tool_result("tool_456", None, is_error=True, error_msg="Failed")
    assert result["is_error"] is True


def test_make_tool_result_string_content():
    result = make_tool_result("tool_789", "already a string")
    assert result["content"] == "already a string"


def test_get_client_returns_singleton(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    # Reset singleton for test isolation
    import shared.client as sc
    sc._client = None
    try:
        c1 = get_client()
        c2 = get_client()
        assert c1 is c2
    finally:
        sc._client = None  # always cleanup
