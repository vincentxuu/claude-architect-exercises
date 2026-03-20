# ex2_claude_code/validate.py
"""Validate Claude Code configuration file structure and YAML frontmatter syntax."""
from pathlib import Path
import re
import sys


REQUIRED_FILES = [
    "CLAUDE.md",
    ".claude/rules/react.md",
    ".claude/rules/api.md",
    ".claude/rules/testing.md",
    ".claude/commands/review.md",
    ".claude/commands/extract-types.md",
    ".claude/skills/analyze-codebase.md",
    ".claude/skills/generate-tests.md",
    ".mcp.json",
]


def validate_structure(base: Path) -> list[str]:
    """Check all required config files exist."""
    errors = []
    for rel_path in REQUIRED_FILES:
        if not (base / rel_path).exists():
            errors.append(f"Missing: {rel_path}")
    return errors


def validate_rule_frontmatter(rule_file: Path) -> list[str]:
    """Check that a rule file has valid YAML frontmatter with a 'paths' field."""
    errors = []
    content = rule_file.read_text()
    if not content.startswith("---"):
        errors.append("Missing frontmatter (must start with ---)")
        return errors
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        errors.append("Malformed frontmatter (no closing ---)")
        return errors
    frontmatter = match.group(1)
    if "paths:" not in frontmatter:
        errors.append("Missing 'paths:' field in frontmatter")
    return errors


if __name__ == "__main__":
    base = Path(__file__).parent
    all_errors = validate_structure(base)
    rules_dir = base / ".claude" / "rules"
    for rule_file in rules_dir.glob("*.md"):
        errs = validate_rule_frontmatter(rule_file)
        all_errors.extend([f"{rule_file.name}: {e}" for e in errs])

    if all_errors:
        print("VALIDATION FAILED:")
        for err in all_errors:
            print(f"  ✗ {err}")
        sys.exit(1)
    else:
        print("✓ All Claude Code configuration files are valid")
