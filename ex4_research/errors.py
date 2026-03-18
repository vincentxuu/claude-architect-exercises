# ex4_research/errors.py
from typing import Literal
from pydantic import BaseModel


class SubagentError(BaseModel):
    """
    Structured error returned by subagents to the coordinator.
    Never suppress errors — always return partial results and context.
    """
    failure_type: Literal["timeout", "not_found", "parse_error", "rate_limit"]
    attempted_query: str
    partial_results: list          # whatever was found before failure
    alternatives: list[str]        # coordinator recovery suggestions


class SubagentResult(BaseModel):
    """Union type: either findings or an error."""
    success: bool
    findings: list = []
    error: SubagentError | None = None
    coverage_note: str = ""        # e.g., "music industry data unavailable"
