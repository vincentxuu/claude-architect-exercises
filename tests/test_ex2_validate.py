# tests/test_ex2_validate.py
import pytest
from pathlib import Path
from ex2_claude_code.validate import validate_structure, validate_rule_frontmatter

BASE = Path(__file__).parent.parent / "ex2_claude_code"


def test_required_files_exist():
    errors = validate_structure(BASE)
    assert errors == [], f"Structure errors: {errors}"


def test_rule_files_have_valid_frontmatter():
    rules_dir = BASE / ".claude" / "rules"
    for rule_file in rules_dir.glob("*.md"):
        errors = validate_rule_frontmatter(rule_file)
        assert errors == [], f"{rule_file.name}: {errors}"


def test_rule_has_paths_field():
    rules_dir = BASE / ".claude" / "rules"
    for rule_file in rules_dir.glob("*.md"):
        content = rule_file.read_text()
        assert "paths:" in content, f"{rule_file.name} missing 'paths:' in frontmatter"


def test_mcp_json_has_no_hardcoded_secrets():
    mcp_json = (BASE / ".mcp.json").read_text()
    assert "sk-ant-" not in mcp_json
    assert "ghp_" not in mcp_json
    assert "${" in mcp_json  # must use env var expansion
