---
allowed-tools:
  - Write
argument-hint: "function or class name to test"
---

Generate pytest test cases for the specified function or class.

Requirements:
- Follow AAA pattern (Arrange / Act / Assert)
- Cover: happy path, edge cases, error cases
- Mock all external API calls
- Name tests: `test_<function>_<scenario>`

Write tests to `tests/test_<module_name>.py`. Do not modify existing test files.
