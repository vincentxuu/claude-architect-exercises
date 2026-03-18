---
context: fork
allowed-tools:
  - Read
  - Grep
  - Glob
argument-hint: "path to analyze (default: current directory)"
---

Analyze the codebase at the given path and return a structured summary:

1. **Entry points:** List all `main.py`, `app.py`, CLI entry points
2. **Dependencies:** Key imports and external packages used
3. **Architecture:** High-level structure (layers, modules, patterns)
4. **Test coverage:** What has tests, what doesn't
5. **Complexity hotspots:** Files > 300 lines or functions with many branches

Return a concise markdown summary. Do not include file contents.
