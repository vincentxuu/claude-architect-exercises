"""
MCP-style tool implementations for the customer support agent.
Each tool returns structured data or a ToolError-compatible dict.
Descriptions are rich enough to guide reliable tool selection.
"""
import uuid
from datetime import datetime, timezone
from shared.types import ToolError

# --- In-memory fixtures (stand-in for real backend) ---
_CUSTOMERS = {
    "john@example.com": {"customer_id": "C001", "name": "John Doe", "verified": True},
    "jane@example.com": {"customer_id": "C002", "name": "Jane Smith", "verified": True},
}
_ORDERS = {
    "ORD-001": {"order_id": "ORD-001", "customer_id": "C001", "status": "delivered", "amount": 49.99, "created_at": 1700000000},
    "ORD-002": {"order_id": "ORD-002", "customer_id": "C002", "status": "shipped",   "amount": 129.00, "created_at": 1700100000},
    "ORD-003": {"order_id": "ORD-003", "customer_id": "C001", "status": "delivered", "amount": 599.00, "created_at": 1700200000},
}


def get_customer(email: str) -> dict:
    """Look up a verified customer by email address."""
    customer = _CUSTOMERS.get(email)
    if not customer:
        return ToolError(errorCategory="validation", isRetryable=False,
                        message=f"No customer found with email '{email}'").model_dump()
    return customer


def lookup_order(order_id: str) -> dict:
    """Look up order details by order ID. Returns status, amount, and creation timestamp."""
    order = _ORDERS.get(order_id)
    if not order:
        return ToolError(errorCategory="validation", isRetryable=False,
                        message=f"Order '{order_id}' not found").model_dump()
    return order


def process_refund(customer_id: str, order_id: str, amount: float) -> dict:
    """
    Issue a refund for a delivered order. Requires a verified customer_id from get_customer.
    Use for amounts <= $500 only; amounts above threshold must use escalate_to_human.
    amount=0 simulates a transient payment-gateway error for testing.
    """
    if amount == 0.0:
        return ToolError(errorCategory="transient", isRetryable=True,
                        message="Payment gateway timeout. Retry is safe.").model_dump()
    if amount > 500.0:
        return ToolError(errorCategory="business", isRetryable=False,
                        message=f"Refund amount ${amount:.2f} exceeds $500 threshold. Use escalate_to_human.").model_dump()
    return {
        "status": "approved",
        "refund_id": f"REF-{uuid.uuid4().hex[:8].upper()}",
        "customer_id": customer_id,
        "order_id": order_id,
        "refund_amount": amount,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }


def escalate_to_human(customer_id: str, order_id: str, reason: str, escalation_type: str) -> dict:
    """
    Create a human-agent ticket. Use when: refund > $500, policy exception required,
    or customer explicitly requests a human agent. Provide a clear reason and type.
    escalation_type: 'REFUND_THRESHOLD' | 'POLICY_EXCEPTION' | 'CUSTOMER_REQUEST'
    """
    return {
        "status": "escalated",
        "ticket_id": f"TKT-{uuid.uuid4().hex[:6].upper()}",
        "customer_id": customer_id,
        "order_id": order_id,
        "reason": reason,
        "escalation_type": escalation_type,
        "assigned_at": datetime.now(timezone.utc).isoformat(),
    }


# --- Tool definitions for the API ---
TOOL_DEFINITIONS = [
    {
        "name": "get_customer",
        "description": (
            "Look up a customer record by their email address and return their verified customer_id. "
            "ALWAYS call this first before lookup_order or process_refund — customer_id is required "
            "for all subsequent operations. Input: email string. "
            "Returns: customer_id, name, verified boolean. "
            "Error if email not found (non-retryable)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"email": {"type": "string", "description": "Customer email address"}},
            "required": ["email"],
        },
    },
    {
        "name": "lookup_order",
        "description": (
            "Retrieve order details by order ID. Requires a verified customer_id from get_customer first. "
            "Use when customer provides an order number or asks about a specific purchase. "
            "Returns: order_id, status, amount, created_at timestamp. "
            "Do NOT use this to look up customers — use get_customer for that."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string", "description": "Order ID (e.g. ORD-001)"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "process_refund",
        "description": (
            "Issue a refund for a delivered order. ONLY use after get_customer returns a verified customer_id. "
            "ONLY for refund amounts <= $500. For amounts > $500, use escalate_to_human instead. "
            "Input: customer_id (from get_customer), order_id, amount in USD. "
            "Returns refund confirmation on success. May return transient errors (retryable)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "order_id": {"type": "string"},
                "amount": {"type": "number", "description": "Refund amount in USD, must be <= 500"},
            },
            "required": ["customer_id", "order_id", "amount"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": (
            "Create a human-agent support ticket. Use when: (1) refund amount > $500, "
            "(2) customer explicitly asks for a human, (3) policy exception is needed, "
            "(4) issue cannot be resolved with available tools. "
            "Provide a structured reason and escalation_type for the human agent. "
            "escalation_type options: REFUND_THRESHOLD, POLICY_EXCEPTION, CUSTOMER_REQUEST, UNRESOLVABLE"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "order_id": {"type": "string"},
                "reason": {"type": "string", "description": "Clear explanation for the human agent"},
                "escalation_type": {
                    "type": "string",
                    "enum": ["REFUND_THRESHOLD", "POLICY_EXCEPTION", "CUSTOMER_REQUEST", "UNRESOLVABLE"],
                },
            },
            "required": ["customer_id", "order_id", "reason", "escalation_type"],
        },
    },
]
