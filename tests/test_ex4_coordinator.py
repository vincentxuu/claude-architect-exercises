# tests/test_ex4_coordinator.py
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from ex4_research.coordinator import CoordinatorAgent
from ex4_research.context import Finding, ResearchContext
from ex4_research.errors import SubagentResult, SubagentError


def make_mock_result(findings_data: list) -> SubagentResult:
    findings = [
        Finding(
            claim=f["claim"],
            evidence_excerpt=f["excerpt"],
            source_url=f["url"],
            confidence=f.get("confidence", 0.8),
        )
        for f in findings_data
    ]
    return SubagentResult(success=True, findings=findings)


def make_error_result(failure_type: str, query: str) -> SubagentResult:
    return SubagentResult(
        success=False,
        error=SubagentError(
            failure_type=failure_type,
            attempted_query=query,
            partial_results=[],
            alternatives=["retry with different query"],
        ),
    )


@pytest.mark.asyncio
async def test_coordinator_aggregates_successful_results():
    coordinator = CoordinatorAgent()
    web_result = make_mock_result([{"claim": "AI grew 40%", "excerpt": "...", "url": "https://a.com"}])
    doc_result = make_mock_result([{"claim": "Healthcare AI up", "excerpt": "...", "url": "https://b.com"}])

    with patch.object(coordinator, "run_web_search", new=AsyncMock(return_value=web_result)):
        with patch.object(coordinator, "run_doc_analysis", new=AsyncMock(return_value=doc_result)):
            ctx = await coordinator.gather_research("AI in healthcare")

    assert len(ctx.findings) == 2


@pytest.mark.asyncio
async def test_coordinator_handles_subagent_error():
    coordinator = CoordinatorAgent()
    web_result = make_mock_result([{"claim": "AI grew 40%", "excerpt": "...", "url": "https://a.com"}])
    error_result = make_error_result("timeout", "healthcare AI papers")

    with patch.object(coordinator, "run_web_search", new=AsyncMock(return_value=web_result)):
        with patch.object(coordinator, "run_doc_analysis", new=AsyncMock(return_value=error_result)):
            ctx = await coordinator.gather_research("AI in healthcare")

    # Should still have web findings, with gap noted
    assert len(ctx.findings) >= 1
    assert len(ctx.coverage_gaps) >= 1


@pytest.mark.asyncio
async def test_parallel_execution_runs_concurrently():
    """Both subagents should start before either completes."""
    coordinator = CoordinatorAgent()
    call_log = []

    async def slow_web(*args):
        call_log.append("web_start")
        await asyncio.sleep(0.05)
        call_log.append("web_end")
        return make_mock_result([])

    async def slow_doc(*args):
        call_log.append("doc_start")
        await asyncio.sleep(0.05)
        call_log.append("doc_end")
        return make_mock_result([])

    with patch.object(coordinator, "run_web_search", new=slow_web):
        with patch.object(coordinator, "run_doc_analysis", new=slow_doc):
            await coordinator.gather_research("test topic")

    # Both must have started before either ended (parallel, not sequential)
    web_start = call_log.index("web_start")
    doc_start = call_log.index("doc_start")
    web_end = call_log.index("web_end")
    assert web_start < web_end
    assert doc_start < web_end  # doc started before web ended
