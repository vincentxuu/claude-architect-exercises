# tests/test_ex1_hooks.py
import pytest
from ex1_agent.hooks import run_post_tool_hook, run_pre_tool_hook, HookInterception


def test_post_hook_normalizes_unix_timestamp():
    result = {"order_id": "ORD-001", "created_at": 1700000000, "status": 1}
    normalized = run_post_tool_hook("lookup_order", result)
    assert normalized["created_at"] == "2023-11-14T22:13:20+00:00"
    assert normalized["status"] == "delivered"  # numeric 1 → string


def test_post_hook_passthrough_for_errors():
    error = {"errorCategory": "transient", "isRetryable": True, "message": "fail"}
    result = run_post_tool_hook("lookup_order", error)
    assert result == error  # errors pass through unchanged


def test_pre_hook_blocks_refund_above_threshold():
    with pytest.raises(HookInterception) as exc_info:
        run_pre_tool_hook("process_refund", {"customer_id": "C001", "order_id": "ORD-003", "amount": 599.0})
    assert exc_info.value.redirect_to == "escalate_to_human"
    assert exc_info.value.redirect_inputs["escalation_type"] == "REFUND_THRESHOLD"


def test_pre_hook_allows_refund_below_threshold():
    # Should not raise
    run_pre_tool_hook("process_refund", {"customer_id": "C001", "order_id": "ORD-001", "amount": 49.99})


def test_pre_hook_passthrough_for_other_tools():
    run_pre_tool_hook("get_customer", {"email": "test@example.com"})
    run_pre_tool_hook("escalate_to_human", {"customer_id": "C1", "order_id": "O1", "reason": "x", "escalation_type": "CUSTOMER_REQUEST"})
