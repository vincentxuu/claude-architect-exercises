import pytest
from unittest.mock import MagicMock, patch
from ex1_agent.agent import AgentSession, ProgrammaticGateError


def make_mock_response(stop_reason: str, tool_name: str = None, tool_id: str = "t1", tool_inputs: dict = None):
    """Helper to build a mock Anthropic response."""
    response = MagicMock()
    response.stop_reason = stop_reason
    if stop_reason == "tool_use":
        block = MagicMock()
        block.type = "tool_use"
        block.id = tool_id
        block.name = tool_name
        block.input = tool_inputs or {}
        response.content = [block]
    else:
        block = MagicMock()
        block.type = "text"
        block.text = "Done."
        response.content = [block]
    return response


def test_gate_blocks_lookup_order_without_customer():
    session = AgentSession()
    with pytest.raises(ProgrammaticGateError, match="get_customer"):
        session.check_gate("lookup_order", {})


def test_gate_blocks_process_refund_without_customer():
    session = AgentSession()
    with pytest.raises(ProgrammaticGateError):
        session.check_gate("process_refund", {})


def test_gate_allows_lookup_order_after_customer_verified():
    session = AgentSession()
    session.verified_customer_id = "C001"
    # Should not raise
    session.check_gate("lookup_order", {})


def test_gate_allows_get_customer_without_prior_context():
    session = AgentSession()
    session.check_gate("get_customer", {"email": "test@example.com"})


def test_loop_terminates_on_end_turn():
    session = AgentSession()
    end_response = make_mock_response("end_turn")

    with patch.object(session, "_call_api", return_value=end_response):
        messages = [{"role": "user", "content": "Hello"}]
        result = session.run(messages)

    assert result == "Done."


def test_loop_executes_tool_then_terminates():
    session = AgentSession()
    tool_response = make_mock_response("tool_use", "get_customer", tool_inputs={"email": "john@example.com"})
    end_response = make_mock_response("end_turn")

    responses = iter([tool_response, end_response])
    with patch.object(session, "_call_api", side_effect=lambda msgs: next(responses)):
        messages = [{"role": "user", "content": "Who is john@example.com?"}]
        result = session.run(messages)

    assert result == "Done."
    assert session.verified_customer_id == "C001"


def test_loop_raises_on_unexpected_stop_reason():
    session = AgentSession()
    bad_response = MagicMock()
    bad_response.stop_reason = "max_tokens"
    bad_response.content = []

    with patch.object(session, "_call_api", return_value=bad_response):
        with pytest.raises(RuntimeError, match="max_tokens"):
            session.run([{"role": "user", "content": "Hello"}])
