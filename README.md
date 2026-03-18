# Claude Certified Architect – Foundations Exercises

Production-quality implementations of all 4 preparation exercises from the Claude Certified Architect exam guide, demonstrating core Claude API patterns: agentic loops, Claude Code configuration, structured extraction, and multi-agent orchestration.

## Setup

```bash
uv sync
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
```

## Exercises

| Exercise | Run | Pattern |
|----------|-----|---------|
| ex1 | `uv run python -m ex1_agent.main` | Agentic loop, programmatic gates, pre/post hooks |
| ex2 | `uv run python ex2_claude_code/validate.py` | Claude Code configuration (rules, commands, skills, MCP) |
| ex3 | `uv run python -m ex3_extraction.main` | Forced tool_use, semantic validation, batch API |
| ex4 | `uv run python -m ex4_research.main` | Multi-agent orchestration with asyncio.gather |

## Tests

```bash
uv run pytest
```

## Tutorials

- 🇺🇸 [English Tutorial](docs/tutorial-en.md) — Complete walkthrough of all patterns
- 🇹🇼 [繁體中文教學](docs/tutorial-zh.md) — 完整的 Claude API patterns 教學
