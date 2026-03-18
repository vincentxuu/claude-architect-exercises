# Claude Certified Architect Exercises — Complete Tutorial

> A complete walkthrough of all 4 exercises covering the core Claude API patterns tested in the Claude Certified Architect certification. Each chapter explains the *why* behind the design, not just the *what*.

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/), an Anthropic API key, Git

---

## Chapter 0: Prerequisites & Setup

### Installing uv

This monorepo uses [uv](https://docs.astral.sh/uv/) as its package manager. uv is a fast, modern Python tool that handles virtual environments and dependency locking in a single command. If you don't have it yet, install it with:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart your shell (or run `source ~/.zshrc`) so the `uv` command is available.

### Clone and install

```bash
git clone https://github.com/your-org/claude-architect-exercises.git
cd claude-architect-exercises

uv sync                    # creates .venv and installs all dependencies
cp .env.example .env       # copy the environment template
```

Open `.env` in your editor and fill in your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-...
```

The `.env.example` file also contains a `GITHUB_TOKEN` slot used by Exercise 4's research pipeline. Leave it blank for now; you can add it when you reach that chapter.

### Verify the install

Run the full test suite to confirm everything is wired up correctly:

```bash
uv run pytest
```

You should see **49 passed** at the end. If any tests fail, double-check that `ANTHROPIC_API_KEY` is set in your `.env` and that `uv sync` completed without errors.

### Repo structure

```
claude-architect-exercises/
├── shared/          # Shared client, types, and console utilities
├── ex1_agent/       # Exercise 1: agentic loop with tool use
├── ex2_claude_code/ # Exercise 2: Claude Code configuration files
├── ex3_extraction/  # Exercise 3: structured data extraction
├── ex4_research/    # Exercise 4: multi-agent research pipeline
└── tests/           # pytest test suite (49 tests)
```

Each exercise directory is a self-contained Python package (`__init__.py` present) that imports from `shared/`. The `tests/` directory mirrors this layout: one test file per source module. All exercises share the same virtual environment managed by uv and the same `pyproject.toml` at the repo root.

---

## Chapter 1: Shared Infrastructure (`shared/`)

Before any exercise can call Claude, the monorepo needs three shared utilities: a type for structured errors, a function that serializes tool results into the format the API expects, and a singleton Anthropic client. These live in `shared/` and are built once so every exercise can import them without duplication.

The three files are:

- `shared/types.py` — `ToolError` model and `make_tool_result()` helper
- `shared/client.py` — lazy singleton Anthropic client and model constant
- `shared/utils.py` — Rich-formatted console helpers for demos

### `shared/types.py` — Classifying errors and building tool results

When a tool fails, you have two choices: return a generic error string, or return a structured object that tells the model (and your own application logic) *why* it failed and whether it makes sense to try again. This repo takes the structured approach.

`ToolError` is a Pydantic model that carries exactly this information:

```python
class ToolError(BaseModel):
    errorCategory: Literal["transient", "validation", "permission", "business"]
    isRetryable: bool
    message: str
```

The four categories cover every failure mode you will encounter in real Claude integrations:

- **transient** — a temporary infrastructure hiccup (network timeout, 529 overload). Retrying is safe and usually succeeds.
- **validation** — the caller passed bad input (missing required field, wrong type). Retrying with the same inputs will always fail; the model needs to generate different arguments.
- **permission** — an authentication or authorization failure (invalid API key, insufficient scope). Retrying won't help until the credential problem is fixed.
- **business** — the operation is technically valid but violates a policy rule (e.g. requesting a refund above the allowed limit). This is a logic-level rejection, not an infrastructure problem.

`isRetryable` makes the retry decision machine-readable, so an agentic loop can inspect it programmatically rather than pattern-matching on error strings.

Once your application logic decides what happened, it hands the result back to Claude via `make_tool_result()`:

```python
def make_tool_result(
    tool_use_id: str,
    content: Any,
    is_error: bool = False,
    error_msg: str = "",
) -> dict:
    if is_error:
        return {
            "type": "tool_result",    # required by the messages API
            "tool_use_id": tool_use_id,
            "is_error": True,
            "content": error_msg,     # plain string, not JSON
        }
    return {
        "type": "tool_result",        # required by the messages API
        "tool_use_id": tool_use_id,
        "content": json.dumps(content) if not isinstance(content, str) else content,
    }
```

The function handles two cases. For a successful result, it JSON-encodes any dict or list (the API expects a string here) while passing plain strings through unchanged. For an error result, it sets `is_error: true` and puts the error message directly in `content` — no JSON encoding, because the model reads this as a human-readable explanation of what went wrong.

The `tool_use_id` field is critical: it must exactly match the `id` field from the `tool_use` block Claude sent in the previous turn. Without this link, the API cannot pair your result with the tool call that triggered it.

### `shared/client.py` — Lazy singleton client

Every exercises imports `get_client()` to obtain the Anthropic SDK client. The implementation is deliberately minimal:

```python
_client: Anthropic | None = None

MODEL = "claude-sonnet-4-6"  # pinned model used across all exercises

def get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY not set")  # explicit, not silent
        _client = Anthropic(api_key=api_key)
    return _client
```

Two design decisions are worth noting. First, the singleton pattern: `_client` is created only on the first call and reused on every subsequent call. In an agentic loop that fires dozens of API calls, this avoids the overhead of re-instantiating the SDK object (which reads environment variables and sets up HTTP connection pools) on every iteration.

Second, the explicit `EnvironmentError` on a missing API key. The alternative — letting the Anthropic client silently initialize with `None` and fail later — produces a cryptic authentication error that is hard to trace back to a missing `.env` entry. Failing fast with a clear message is far easier to debug, especially when onboarding to a new codebase.

The `MODEL` constant pins `claude-sonnet-4-6` for all exercises. Centralizing this in one place means you can swap models across the entire repo by changing a single line.

### `shared/utils.py` — Console output helpers

The demo scripts (`main.py` files in each exercise) use three helper functions from `shared/utils.py` to produce readable terminal output via the [Rich](https://github.com/Textualize/rich) library:

- `print_message(role, content)` — renders a colored panel labelled with the role (cyan for `assistant`, green for `user`).
- `print_tool_call(tool_name, inputs)` — renders a yellow panel with the tool name and syntax-highlighted JSON of the input arguments.
- `print_error(msg)` — prints a bold red `ERROR:` prefix with the message.

These are presentation utilities only — none of the exercise logic depends on them, and the test suite doesn't call them. They exist purely to make the demo runs easier to follow in the terminal.

---

> **Exam tip:** `tool_result` blocks must include three fields: `type: "tool_result"`, `tool_use_id` (matching the tool_use block's `id`), and `content`. Use `is_error: true` when a tool fails — this tells the model the tool failed so it can recover gracefully, rather than assuming the empty content is a valid result.
