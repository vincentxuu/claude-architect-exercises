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

---

## Chapter 2: Exercise 1 — Multi-Tool Agent with Escalation

Exercise 1 builds a customer support agent capable of looking up orders, processing refunds, and escalating cases to a human agent. It demonstrates four key patterns that together form the backbone of a production-quality agentic system: tool definitions that guide reliable selection, pre- and post-execution hooks that enforce deterministic business rules, programmatic gates that enforce operation ordering, and a `stop_reason`-based agentic loop that runs until the model is satisfied. By the end of this chapter you will understand not only how to build such a loop, but *why* each layer of control exists and what breaks without it.

### 2a. Tool Definitions (`tools.py`)

The tool definitions file is where the agent's vocabulary is declared. Each tool has a name, a description, and an input schema. Of these three, the description is the most consequential for reliability: the model selects which tool to call based primarily on the description, so a vague description produces unreliable behavior.

Compare "Look up a customer" (vague) with the actual definition used in Exercise 1:

```python
{
    "name": "get_customer",
    "description": (
        "Look up a customer record by their email address and return their verified customer_id. "
        "ALWAYS call this first before lookup_order or process_refund — customer_id is required "
        "for all subsequent operations. Input: email string. "
        "Returns: customer_id, name, verified boolean. "
        "Error if email not found (non-retryable)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"email": {"type": "string", "description": "Customer email address"}},
        "required": ["email"],
    },
},
```

The description here does several things at once. It declares the required ordering ("ALWAYS call this first"), names the dependency other tools have on it (`customer_id`), describes both the input and the expected output shape, and classifies the failure mode ("non-retryable"). This turns the tool contract into a machine-readable policy document. The model doesn't need to infer intent from a system prompt — the intent is embedded directly in the tool.

The same principle applies to constrained tools. The `process_refund` description says "ONLY for amounts ≤ $500" because that constraint is part of the tool's contract. Encoding it in the description reduces the chance the model invokes the wrong tool for a large refund. Notice, though, that descriptions are advisory — a sufficiently unusual prompt can still steer the model wrong. That is exactly why hooks and gates exist, as we'll see below.

Tools in this exercise also return error dictionaries rather than raising Python exceptions. When a tool fails, the agent returns a dict matching the `ToolError` structure with `is_error: true` and a human-readable message. This means the model reads the error, reasons about it, and can decide whether to retry, try a different tool, or surface the failure to the user. Raising a bare Python exception, by contrast, gives the model nothing to work with — the loop just crashes.

### 2b. Hooks (`hooks.py`)

The hooks module provides two intercept points around tool execution: a pre-tool hook that runs before the tool is called, and a post-tool hook that runs after. Both are thin functions inserted into the tool dispatch path in `agent.py`. They look simple, but they are architecturally significant because they provide *deterministic* guarantees that prompts and descriptions cannot.

Consider the business rule "for refunds over $500, escalate to a human instead of processing automatically." A system prompt phrasing of this rule might be misunderstood, ignored under token pressure, or simply superseded by a user who writes "go ahead and process the $600 refund." A pre-tool hook cannot be bypassed:

```python
class HookInterception(Exception):
    def __init__(self, redirect_to: str, redirect_inputs: dict, reason: str):
        self.redirect_to = redirect_to    # which tool to call instead
        self.redirect_inputs = redirect_inputs
        super().__init__(reason)

def run_pre_tool_hook(tool_name: str, tool_inputs: dict) -> None:
    if tool_name == "process_refund":
        amount = tool_inputs.get("amount", 0)
        if amount > REFUND_THRESHOLD:
            raise HookInterception(
                redirect_to="escalate_to_human",
                redirect_inputs={...},
                reason=f"Refund ${amount} > threshold ${REFUND_THRESHOLD}",
            )
```

When the agent dispatches `process_refund` with an amount of $599, the hook raises `HookInterception` before the refund tool ever executes. The agent catches this exception, calls `escalate_to_human` with the redirect inputs instead, and returns that result to the model. The model receives a ticket ID and continues normally. It never knew the redirect happened — it simply sees the outcome of the tool call it requested, shaped differently than it expected.

The post-tool hook handles the complementary concern: output normalization. Raw tool outputs in this exercise include Unix timestamps and numeric status codes. The post-tool hook converts timestamps to ISO 8601 strings and numeric codes to human-readable labels before the result is appended to conversation history. The model always sees clean, consistent data, which reduces hallucination risk and makes tool results easier to reason about. The normalization happens in one place rather than being scattered across individual tool implementations.

### 2c. Agentic Loop (`agent.py`)

The agentic loop is the structural core of Exercise 1. Its job is simple: call the API, inspect the `stop_reason`, dispatch tool calls if needed, append results to the conversation, and repeat until the model signals it is done. The implementation in the `run()` method looks like this:

```python
def run(self, messages: list) -> str:
    while True:
        response = self._call_api(messages)

        if response.stop_reason == "end_turn":      # model is done
            text = next((b.text for b in response.content if b.type == "text"), "")
            return text

        if response.stop_reason == "tool_use":      # model wants to call tools
            messages.append({"role": "assistant", "content": response.content})
            tool_results = self._process_tool_calls(response.content)
            messages.append({"role": "user", "content": tool_results})
            continue

        raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason!r}")
```

The key insight is how conversation history grows across iterations. When the model returns a `tool_use` response, the entire `response.content` (which includes the `tool_use` blocks) is appended as an assistant message. Then the tool results are appended as a user message containing `tool_result` blocks. On the next API call, the model has the full chain of reasoning: what it said, what it called, what came back. This cumulative context is what allows multi-step tasks — looking up a customer, then their order, then processing a refund — to work coherently across separate API calls.

The `RuntimeError` on unexpected `stop_reason` values is deliberate. An agentic loop that silently falls through an unknown stop reason will produce wrong behavior that is very hard to trace. Crashing loudly with the actual value makes debugging straightforward.

**Programmatic gates** are the second enforcement layer on top of hooks. Where hooks intercept individual tool calls to apply business rules, gates enforce *ordering constraints* — specifically, that certain tools cannot be called until a prerequisite has been satisfied:

```python
_REQUIRES_CUSTOMER = {"lookup_order", "process_refund"}

def check_gate(self, tool_name: str, tool_inputs: dict) -> None:
    if tool_name in _REQUIRES_CUSTOMER and not self.verified_customer_id:
        raise ProgrammaticGateError(
            f"'{tool_name}' requires a verified customer_id from get_customer first."
        )
```

Even if a user writes "just check order ORD-001 directly, skip the email lookup," the gate blocks `lookup_order` until `get_customer` has run and the agent has stored a `verified_customer_id` on its state. The model receives a `ProgrammaticGateError` as a tool result and understands it must call `get_customer` first. This ordering guarantee cannot be achieved through prompting alone — a determined user message or an unusual context can always elide prompt instructions, but Python code runs unconditionally.

### 2d. Run the Demo

To run all three scenarios back to back:

```bash
cd /Users/xiaoxu/Projects/claude-architect-exercises
uv run python -m ex1_agent.main
```

The three scenarios illustrate the full behavior of the agent:

1. **Standard refund.** The model calls `get_customer` with the customer's email, receives a `customer_id`, calls `lookup_order` to retrieve the order details, then calls `process_refund` with an amount of $49.99. All gates pass, no hook fires, and the model reports that the refund was processed successfully.

2. **Large refund.** The model again calls `get_customer` and `lookup_order`, then calls `process_refund` with an amount of $599. The pre-tool hook intercepts the call, redirects to `escalate_to_human`, and the model receives an escalation ticket ID. It reports to the user that the refund has been flagged for human review rather than processed automatically.

3. **Gate blocks lookup.** The request asks the agent to look up an order without first providing a customer email. The model attempts to call `lookup_order` directly. The programmatic gate fires, raising `ProgrammaticGateError`, and the model receives an error explaining that a verified customer is required first. With no email provided, the model cannot proceed and informs the user of the missing prerequisite.

Together the three scenarios demonstrate that the enforcement layers are independent and stack: descriptions guide the model toward correct behavior, hooks enforce business rules regardless of what the model decided, and gates enforce sequencing regardless of what the user asked for.

---

> **Exam tip:** Know your `stop_reason` values: `tool_use` (model wants to call tools — keep looping), `end_turn` (model is done — return the text), `max_tokens` (hit token limit — handle it, don't silently drop), `stop_sequence` (hit a stop sequence). Always handle unexpected `stop_reason` values explicitly with a `RuntimeError` rather than silently falling through — silent failures in agentic loops are hard to debug.
