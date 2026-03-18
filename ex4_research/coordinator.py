# ex4_research/coordinator.py
"""
Coordinator agent for the hub-and-spoke research pipeline.

Key patterns demonstrated:
  1. Parallel subagent execution via asyncio.gather
  2. Structured error propagation (never suppress)
  3. Context explicitly passed to each subagent
  4. Coverage gap annotation in final output
"""
import asyncio
from ex4_research.context import Finding, ResearchContext
from ex4_research.errors import SubagentResult
from ex4_research.subagents import (
    run_web_search_agent, run_doc_analysis_agent,
    run_synthesis_agent, run_report_agent
)
from shared.utils import console


class CoordinatorAgent:
    async def run_web_search(self, subtopic: str) -> SubagentResult:
        return await run_web_search_agent(subtopic)

    async def run_doc_analysis(self, subtopic: str) -> SubagentResult:
        return await run_doc_analysis_agent(subtopic)

    async def gather_research(self, topic: str) -> ResearchContext:
        """
        Run web search and doc analysis subagents IN PARALLEL via asyncio.gather.
        Aggregate results and annotate coverage gaps.
        """
        ctx = ResearchContext(topic=topic)

        # Parallel execution — both subagents start simultaneously
        web_result, doc_result = await asyncio.gather(
            self.run_web_search(topic),
            self.run_doc_analysis(topic),
        )

        # Process web search results
        if web_result.success:
            ctx.add_findings(web_result.findings)
        else:
            console.print(f"[yellow]Web search failed: {web_result.error.failure_type}[/]")
            ctx.coverage_gaps.append(f"Web: {web_result.error.attempted_query}")

        # Process doc analysis results
        if doc_result.success:
            ctx.add_findings(doc_result.findings)
        else:
            console.print(f"[yellow]Doc analysis failed: {doc_result.error.failure_type}[/]")
            ctx.coverage_gaps.append(f"Docs: {doc_result.error.attempted_query}")

        return ctx

    async def run_research(self, topic: str) -> str:
        """
        Full research pipeline: gather → synthesize → report.
        Returns final report string.
        """
        console.rule(f"[bold blue]Research: {topic}")

        # Phase 1: Parallel data gathering
        ctx = await self.gather_research(topic)
        console.print(f"[green]Gathered {len(ctx.findings)} findings[/]")

        # Phase 2: Synthesis (sequential — needs gathered context)
        synthesis = await run_synthesis_agent(ctx)

        # Phase 3: Report generation
        report = await run_report_agent(synthesis, topic)

        return report
