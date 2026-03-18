# Claude Certified Architect – Foundations Exercises

Implementation of all 4 preparation exercises from the Claude Certified Architect exam guide.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in ANTHROPIC_API_KEY in .env
```

## Exercises

| Exercise | Command | Description |
|----------|---------|-------------|
| ex1 | `python -m ex1_agent.main` | Multi-Tool Agent with Escalation |
| ex2 | `python ex2_claude_code/validate.py` | Claude Code Configuration |
| ex3 | `python -m ex3_extraction.main` | Structured Data Extraction |
| ex4 | `python -m ex4_research.main` | Multi-Agent Research Pipeline |

## Tests

```bash
pytest
```
