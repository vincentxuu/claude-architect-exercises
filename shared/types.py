import json
from typing import Any, Literal
from pydantic import BaseModel, field_validator


class ToolError(BaseModel):
    """
    Structures error data within the exercises' internal logic.

    Note: This is distinct from make_tool_result's error_msg parameter.
    ToolError is used for structuring errors in the application code,
    while make_tool_result takes a plain error_msg: str for the API boundary.
    The API expects a string representation of the error.
    """
    errorCategory: Literal["transient", "validation", "permission", "business"]
    isRetryable: bool
    message: str


def make_tool_result(
    tool_use_id: str,
    content: Any,
    is_error: bool = False,
    error_msg: str = "",
) -> dict:
    """
    Build a tool_result block for the messages API.

    Args:
        tool_use_id: The ID of the tool use to respond to.
        content: The content to return. Can be a dict (will be JSON-encoded)
                 or a string (passed through as-is).
        is_error: If True, marks this as an error result and uses error_msg.
        error_msg: Error message string when is_error=True.
                   WARNING: When is_error=False, error_msg is silently discarded.

    Returns:
        A dict conforming to the Anthropic messages API tool_result format.
    """
    if is_error:
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "is_error": True,
            "content": error_msg,
        }
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": json.dumps(content) if not isinstance(content, str) else content,
    }
