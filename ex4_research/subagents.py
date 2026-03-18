# ex4_research/subagents.py
"""
Subagent implementations for the research pipeline.
Web search is MOCKED (fixture data) — focused on orchestration patterns.
Each subagent receives its full context in the prompt (no implicit inheritance).
"""
from shared.client import get_client, MODEL
from ex4_research.context import Finding, ResearchContext
from ex4_research.errors import SubagentResult, SubagentError

# Mock web search results (fixture data)
_WEB_SEARCH_FIXTURES = {
    "ai": [
        {"claim": "Global AI market grew 38% in 2023", "evidence_excerpt": "Annual market analysis shows AI adoption accelerating", "source_url": "https://example.com/ai-report-2023", "publication_date": "2023-11-01", "confidence": 0.9},
        {"claim": "Healthcare AI reduced diagnostic errors by 22%", "evidence_excerpt": "Clinical trials across 40 hospitals demonstrated error reduction", "source_url": "https://example.com/healthcare-ai", "publication_date": "2023-08-15", "confidence": 0.85},
    ],
    "creative": [
        {"claim": "AI image generation market reached $1.2B in 2023", "evidence_excerpt": "Generative AI tools saw explosive adoption in design workflows", "source_url": "https://example.com/creative-ai", "publication_date": "2023-12-01", "confidence": 0.8},
    ],
}

_DOC_ANALYSIS_FIXTURES = {
    "ai": [
        {"claim": "AI adoption requires significant data infrastructure investment", "evidence_excerpt": "Organizations report 18-24 month implementation timelines", "source_url": "https://example.com/whitepaper-ai-infra", "publication_date": "2023-06-01", "confidence": 0.75},
    ],
}


async def run_web_search_agent(subtopic: str, prior_context: str = "") -> SubagentResult:
    """
    Web search subagent. Context passed explicitly in prompt — not inherited.
    Returns structured findings with source attribution.
    """
    key = next((k for k in _WEB_SEARCH_FIXTURES if k in subtopic.lower()), None)
    if not key:
        return SubagentResult(
            success=False,
            error=SubagentError(
                failure_type="not_found",
                attempted_query=subtopic,
                partial_results=[],
                alternatives=["Try more specific query", "Use doc analysis instead"],
            ),
        )
    raw_findings = _WEB_SEARCH_FIXTURES[key]
    findings = [Finding(**f) for f in raw_findings]
    return SubagentResult(success=True, findings=findings)


async def run_doc_analysis_agent(subtopic: str, documents: list[str] | None = None) -> SubagentResult:
    """
    Document analysis subagent. Analyzes provided documents or uses fixtures.
    """
    key = next((k for k in _DOC_ANALYSIS_FIXTURES if k in subtopic.lower()), None)
    if not key:
        return SubagentResult(
            success=False,
            error=SubagentError(
                failure_type="not_found",
                attempted_query=subtopic,
                partial_results=[],
                alternatives=["Expand search terms"],
            ),
            coverage_note=f"No documents found for: {subtopic}",
        )
    findings = [Finding(**f) for f in _DOC_ANALYSIS_FIXTURES[key]]
    return SubagentResult(success=True, findings=findings)


async def run_synthesis_agent(context: ResearchContext) -> str:
    """
    Synthesis subagent. Combines findings into a structured summary.
    Preserves source attribution and flags conflicts.
    """
    client = get_client()
    prompt = (
        f"You are a research synthesis agent. Based on these research findings, "
        f"write a structured summary that:\n"
        f"1. Groups related findings\n"
        f"2. Preserves source attribution for each claim\n"
        f"3. Explicitly notes coverage gaps\n"
        f"4. Distinguishes well-established findings from contested ones\n\n"
        f"{context.to_prompt_context()}"
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


async def run_report_agent(synthesis: str, topic: str) -> str:
    """
    Report generation subagent. Formats synthesis into a final cited report.
    """
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": (
                f"Generate a professional research report on '{topic}' from this synthesis:\n\n"
                f"{synthesis}\n\n"
                f"Format: Executive Summary, Key Findings (with citations), Coverage Limitations."
            )
        }],
    )
    return response.content[0].text
