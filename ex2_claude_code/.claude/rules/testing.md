---
paths:
  - "**/*.test.*"
  - "**/*.spec.*"
  - "**/tests/**"
---

# Testing Conventions

- Test names: `test_<function>_<scenario>` (e.g., `test_get_customer_not_found`)
- Use AAA pattern: Arrange / Act / Assert with blank lines between sections
- One assertion per test where possible; group related assertions with comment
- Mock at the boundary: mock external calls, not internal helpers
- Use `pytest.raises(ExceptionType, match="pattern")` for error assertions
- Fixtures in `conftest.py`, not inside test files
