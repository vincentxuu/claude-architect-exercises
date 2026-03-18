# Project Standards

## Code Quality
- All functions must have type hints
- No bare `except:` — always catch specific exception types
- Use `pathlib.Path` instead of `os.path` for file operations
- Prefer f-strings over `.format()` or `%`

## Testing
- Write tests before implementation (TDD)
- Every public function needs at least one test
- Use `pytest.fixture` for shared setup
- Mock external API calls with `unittest.mock.patch`

## Git
- Commits in imperative mood: "Add feature" not "Added feature"
- Each commit should pass all tests
