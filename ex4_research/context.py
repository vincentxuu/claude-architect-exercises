# ex4_research/context.py
from pydantic import BaseModel, field_validator


class Finding(BaseModel):
    claim: str
    evidence_excerpt: str
    source_url: str
    publication_date: str | None = None  # ISO date string; prevents temporal misinterpretation
    confidence: float  # 0.0–1.0

    @field_validator("confidence")
    @classmethod
    def confidence_must_be_valid(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be between 0 and 1, got {v}")
        return v


class ResearchContext(BaseModel):
    topic: str
    findings: list[Finding] = []
    coverage_gaps: list[str] = []  # topics where sources were unavailable

    def add_findings(self, new_findings: list[Finding]) -> None:
        self.findings.extend(new_findings)

    def to_prompt_context(self) -> str:
        """Format findings for injection into a subagent prompt."""
        if not self.findings:
            return "No findings yet."
        lines = [f"Research topic: {self.topic}\n\nFindings:"]
        for i, f in enumerate(self.findings, 1):
            lines.append(
                f"{i}. CLAIM: {f.claim}\n"
                f"   SOURCE: {f.source_url} (date: {f.publication_date or 'unknown'})\n"
                f"   EXCERPT: {f.evidence_excerpt}\n"
                f"   CONFIDENCE: {f.confidence:.0%}"
            )
        if self.coverage_gaps:
            lines.append(f"\nCoverage gaps: {', '.join(self.coverage_gaps)}")
        return "\n".join(lines)
