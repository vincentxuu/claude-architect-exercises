# ex4_research/main.py
"""
2 demo topics for Exercise 4:
  1. Broad topic — demonstrates parallel search + synthesis
  2. Narrow topic — demonstrates coverage gap annotation
"""
import asyncio
from shared.utils import console
from ex4_research.coordinator import CoordinatorAgent


async def main():
    coordinator = CoordinatorAgent()

    console.rule("[bold magenta]Demo 1: AI Adoption Trends")
    report1 = await coordinator.run_research("impact of AI on healthcare and productivity")
    console.print(report1)

    console.rule("[bold magenta]Demo 2: Narrow Topic (will show coverage gaps)")
    report2 = await coordinator.run_research("quantum computing in pharmaceutical synthesis")
    console.print(report2)


if __name__ == "__main__":
    asyncio.run(main())
