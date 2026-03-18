"""
Hooks implemented as wrapper functions invoked explicitly in the agentic loop.
These provide DETERMINISTIC guarantees that prompt instructions cannot.

Two hook types:
  run_pre_tool_hook()  — intercept tool calls before execution (business rules)
  run_post_tool_hook() — transform tool results before the model sees them
"""
from datetime import datetime, timezone

REFUND_THRESHOLD = 500.0

# Numeric status codes → human-readable strings
_ORDER_STATUS_MAP = {0: "pending", 1: "delivered", 2: "shipped", 3: "cancelled"}


class HookInterception(Exception):
    """Raised by pre-tool hook when a tool call must be redirected."""
    def __init__(self, redirect_to: str, redirect_inputs: dict, reason: str):
        self.redirect_to = redirect_to
        self.redirect_inputs = redirect_inputs
        self.reason = reason
        super().__init__(reason)


def run_pre_tool_hook(tool_name: str, tool_inputs: dict) -> None:
    """
    Enforce business rules before tool execution.
    Raises HookInterception to redirect the call to a different tool.
    """
    if tool_name == "process_refund":
        amount = tool_inputs.get("amount", 0)
        if amount > REFUND_THRESHOLD:
            raise HookInterception(
                redirect_to="escalate_to_human",
                redirect_inputs={
                    "customer_id": tool_inputs["customer_id"],
                    "order_id": tool_inputs["order_id"],
                    "reason": f"Refund amount ${amount:.2f} exceeds ${REFUND_THRESHOLD:.2f} threshold",
                    "escalation_type": "REFUND_THRESHOLD",
                },
                reason=f"Refund ${amount} > threshold ${REFUND_THRESHOLD}",
            )


def run_post_tool_hook(tool_name: str, result: dict) -> dict:
    """
    Normalize tool results before the model processes them.
    Handles: Unix timestamps → ISO 8601, numeric status codes → strings.
    Errors pass through unchanged.
    """
    if "errorCategory" in result:
        return result  # pass errors through as-is

    result = dict(result)  # shallow copy to avoid mutation

    # Normalize Unix timestamp to ISO 8601
    if "created_at" in result and isinstance(result["created_at"], (int, float)):
        result["created_at"] = datetime.fromtimestamp(
            result["created_at"], tz=timezone.utc
        ).isoformat()

    # Normalize numeric order status codes
    if "status" in result and isinstance(result["status"], int):
        result["status"] = _ORDER_STATUS_MAP.get(result["status"], str(result["status"]))

    return result
