"""
Agentic loop for the customer support agent.

Key patterns demonstrated:
  1. stop_reason-based loop control (tool_use → continue, end_turn → break)
  2. Programmatic gates block downstream tools until prerequisites complete
  3. Hooks intercept calls before/after tool execution
  4. Tool results are appended to conversation history each iteration
"""
import json
from shared.client import get_client, MODEL
from shared.types import make_tool_result
from shared.utils import print_tool_call, print_message
from ex1_agent.tools import (
    get_customer, lookup_order, process_refund, escalate_to_human, TOOL_DEFINITIONS
)
from ex1_agent.hooks import run_pre_tool_hook, run_post_tool_hook, HookInterception

SYSTEM_PROMPT = """You are a customer support agent. Help customers with returns, billing,
and account issues. Always verify the customer's identity first using get_customer before
accessing order information. Be empathetic and efficient."""


class ProgrammaticGateError(Exception):
    """Raised when a tool call is attempted before its prerequisite has completed."""


_TOOL_FN_MAP = {
    "get_customer": get_customer,
    "lookup_order": lookup_order,
    "process_refund": process_refund,
    "escalate_to_human": escalate_to_human,
}

# Tools that require a verified customer_id before they can be called
_REQUIRES_CUSTOMER = {"lookup_order", "process_refund"}


class AgentSession:
    def __init__(self):
        self.verified_customer_id: str | None = None

    def check_gate(self, tool_name: str, tool_inputs: dict) -> None:
        """Programmatic prerequisite gate — blocks tools that require prior verification."""
        if tool_name in _REQUIRES_CUSTOMER and not self.verified_customer_id:
            raise ProgrammaticGateError(
                f"'{tool_name}' requires a verified customer_id from get_customer first. "
                f"Call get_customer with the customer's email before proceeding."
            )

    def _execute_tool(self, tool_name: str, tool_inputs: dict) -> dict:
        """Execute a single tool call with pre/post hooks and gate enforcement."""
        print_tool_call(tool_name, tool_inputs)

        # 1. Programmatic gate check
        self.check_gate(tool_name, tool_inputs)

        # 2. Pre-tool hook (may redirect)
        try:
            run_pre_tool_hook(tool_name, tool_inputs)
        except HookInterception as e:
            print_message("system", f"Hook intercepted → redirecting to {e.redirect_to}: {e.reason}")
            tool_name = e.redirect_to
            tool_inputs = e.redirect_inputs

        # 3. Execute the tool
        fn = _TOOL_FN_MAP[tool_name]
        result = fn(**tool_inputs)

        # 4. Post-tool hook (normalize result)
        result = run_post_tool_hook(tool_name, result)

        # 5. Update session state from successful get_customer
        if tool_name == "get_customer" and "customer_id" in result:
            self.verified_customer_id = result["customer_id"]

        return result

    def _process_tool_calls(self, content_blocks: list) -> list:
        """Process all tool_use blocks in a response, return tool_result blocks."""
        tool_results = []
        for block in content_blocks:
            if block.type != "tool_use":
                continue
            try:
                result = self._execute_tool(block.name, block.input)
                tool_results.append(make_tool_result(block.id, result))
            except ProgrammaticGateError as e:
                tool_results.append(make_tool_result(block.id, None, is_error=True, error_msg=str(e)))
        return tool_results

    def _call_api(self, messages: list):
        client = get_client()
        return client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

    def run(self, messages: list) -> str:
        """Run the agentic loop until stop_reason is 'end_turn'. Returns final text."""
        while True:
            response = self._call_api(messages)

            if response.stop_reason == "end_turn":
                text = next((b.text for b in response.content if b.type == "text"), "")
                return text

            if response.stop_reason == "tool_use":
                # Append assistant response to history
                messages.append({"role": "assistant", "content": response.content})
                # Execute tools and append results
                tool_results = self._process_tool_calls(response.content)
                messages.append({"role": "user", "content": tool_results})
