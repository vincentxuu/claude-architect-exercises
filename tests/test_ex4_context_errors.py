# tests/test_ex4_context_errors.py
import pytest
from ex4_research.context import Finding, ResearchContext
from ex4_research.errors import SubagentError


def test_finding_requires_source_url():
    f = Finding(
        claim="AI adoption grew 40% in 2023",
        evidence_excerpt="According to the annual report...",
        source_url="https://example.com/report",
        confidence=0.9,
    )
    assert f.publication_date is None  # optional


def test_finding_confidence_range():
    with pytest.raises(Exception):
        Finding(
            claim="x", evidence_excerpt="y",
            source_url="https://example.com", confidence=1.5  # invalid
        )


def test_research_context_merges_findings():
    ctx = ResearchContext(topic="AI in healthcare")
    f1 = Finding(claim="A", evidence_excerpt="E1", source_url="https://s1.com", confidence=0.8)
    f2 = Finding(claim="B", evidence_excerpt="E2", source_url="https://s2.com", confidence=0.7)
    ctx.add_findings([f1, f2])
    assert len(ctx.findings) == 2


def test_subagent_error_structure():
    err = SubagentError(
        failure_type="timeout",
        attempted_query="AI healthcare 2023",
        partial_results=[{"title": "partial result"}],
        alternatives=["retry with shorter query", "use doc analysis instead"],
    )
    assert err.failure_type == "timeout"
    assert len(err.alternatives) == 2


def test_subagent_error_invalid_type():
    with pytest.raises(Exception):
        SubagentError(
            failure_type="network_error",  # invalid
            attempted_query="x",
            partial_results=[],
            alternatives=[],
        )
