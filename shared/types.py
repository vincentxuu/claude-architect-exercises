import json
from typing import Any, Literal
from pydantic import BaseModel, field_validator


class ToolError(BaseModel):
    errorCategory: Literal["transient", "validation", "permission", "business"]
    isRetryable: bool
    message: str


def make_tool_result(
    tool_use_id: str,
    content: Any,
    is_error: bool = False,
    error_msg: str = "",
) -> dict:
    """Build a tool_result block for the messages API."""
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
