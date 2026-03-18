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

---

## Chapter 3: Exercise 2 — Claude Code Configuration

Exercise 2 is different from every other exercise in this repo: it doesn't call the Claude API at all. Instead, it demonstrates how to configure Claude Code — the CLI tool — so it becomes a project-aware collaborator rather than a blank-slate assistant. Well-crafted configuration tells Claude Code which conventions to follow, which files to treat as special, which custom workflows to offer as commands, and which external integrations to load. The difference between an unconfigured and a properly configured Claude Code session is roughly the difference between a contractor who just walked in off the street and one who has read your architecture docs and knows your codebase layout. This chapter covers all five configuration types and what each one is for.

### Configuration files

**CLAUDE.md** is the foundation. It is a Markdown file placed at the root of the project (or any directory Claude Code operates in) and is loaded into context automatically at the start of every session. Unlike rules, CLAUDE.md applies everywhere — there is no path filtering. Use it for things that are always relevant: the project's tech stack, the preferred test framework, the branching strategy, any conventions that apply across every file. This is where you tell Claude Code the basics: "this is a TypeScript monorepo, we use pnpm workspaces, all tests live in `__tests__/` beside the source file they test."

**Rules** (`.claude/rules/*.md`) are path-scoped context injections. Unlike CLAUDE.md, each rule file carries YAML frontmatter that lists the file paths where it applies. Claude Code only injects a rule into context when you are actively working on a file that matches one of its paths. This keeps context lean: your React component conventions don't need to be in context when you're editing a database migration, and your SQL conventions don't need to be in context when you're writing JSX.

A rule file looks like this:

```markdown
---
paths:
  - "src/components/**/*"
  - "src/pages/**/*"
---

# React Component Conventions

- Use functional components only — no class components
- State management: `useState` for local, `useContext` for shared
```

The `paths:` field determines when this rule fires. The glob patterns follow the same syntax as `.gitignore`. When Claude Code is editing `src/components/Button.tsx`, this rule is injected. When it is editing `src/server/db.ts`, it is not. Without the `paths:` field, a rule applies globally — useful for universal constraints but wasteful for framework-specific guidance.

**Commands** (`.claude/commands/*.md`) are user-invocable slash commands that appear in Claude Code's command palette. Each Markdown file in `.claude/commands/` becomes a `/command-name` that users can invoke during a session. The `review.md` command, for instance, runs a structured code quality checklist against the current file or selection — checking for missing tests, unclear variable names, undocumented edge cases, and so on. The `extract-types.md` command takes Python Pydantic models and converts them to TypeScript interfaces, which is useful in projects that have a FastAPI backend paired with a TypeScript frontend. Commands are invoked manually and run once; they are not triggered automatically by file paths.

**Skills** (`.claude/skills/*.md`) are reusable agent definitions. Where commands are one-shot prompts, skills can specify an isolated execution context, a restricted toolset, and an argument hint for the user. A skill file's frontmatter looks like this:

```markdown
---
context: fork
allowed-tools:
  - Read
  - Grep
  - Glob
argument-hint: "path to analyze (default: current directory)"
---

Analyze the codebase at the given path and return a structured summary...
```

Three frontmatter keys matter here. `context: fork` runs the skill in an isolated context — it gets a fresh session that doesn't inherit the main conversation history, and its findings don't pollute the main context window either. This is exactly what you want for a "scan and summarize" skill that might read hundreds of files: the main session stays clean. `allowed-tools` is a whitelist: the `analyze-codebase` skill can only read files with `Read`, `Grep`, and `Glob` — it cannot write, execute, or call external APIs. This is an important safety boundary for read-only analysis tasks. `argument-hint` is a display string shown as a placeholder when the skill is invoked, prompting the user to supply the right kind of input.

**MCP** (`.mcp.json`) registers Model Context Protocol servers that Claude Code will load for this project. MCP servers extend Claude Code with new tools — database clients, API integrations, custom internal services. The `ex2_claude_code/.mcp.json` file registers the GitHub MCP server:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

The critical detail is `${GITHUB_TOKEN}`. This is runtime environment variable expansion — when Claude Code starts, it reads `GITHUB_TOKEN` from the shell environment and substitutes it. The actual token value is never stored in `.mcp.json`. This matters because `.mcp.json` is typically committed to version control: if you hardcode a token here, it will be visible in the repository's git history forever. Always use `${ENV_VAR}` syntax for any credentials or secrets in MCP configuration files.

### validate.py

The `validate.py` script in `ex2_claude_code/` is not an API exercise — it is a configuration linter. It checks that all required configuration files are present in the expected locations and that every rule file in `.claude/rules/` has valid YAML frontmatter containing a `paths:` field. A rule file without `paths:` would apply globally and inject framework-specific context even when working on unrelated files, which degrades Claude Code's performance on those files.

Two functions do the work. `validate_structure(base)` walks the `REQUIRED_FILES` list and records any path that doesn't exist on disk. `validate_rule_frontmatter(rule_file)` reads a single rule file and confirms it opens with a `---` block containing a `paths:` key — if either the opening delimiter or the key is missing, the file is flagged as invalid. The CLI entry point ties them together:

```python
if __name__ == "__main__":
    base = Path(__file__).parent
    all_errors = validate_structure(base)          # check required files exist
    rules_dir = base / ".claude" / "rules"
    for rule_file in rules_dir.glob("*.md"):
        errs = validate_rule_frontmatter(rule_file)
        all_errors.extend([f"{rule_file.name}: {e}" for e in errs])
    if all_errors:
        print("VALIDATION FAILED:")
        for err in all_errors:
            print(f"  ✗ {err}")
        sys.exit(1)                                 # non-zero exit for CI integration
    else:
        print("✓ All Claude Code configuration files are valid")
```

```bash
cd /Users/xiaoxu/Projects/claude-architect-exercises
uv run python ex2_claude_code/validate.py
# ✓ All Claude Code configuration files are valid
```

The script exits with code 0 on success and a non-zero code with descriptive output on failure, so it can be integrated into a CI pipeline to enforce configuration hygiene as the project evolves.

---

> **Exam tip:** The three config types serve different purposes: **Rules** are automatic context injection, scoped to file paths — they fire when you're in matching files. **Commands** are user-invoked slash commands that run a specific prompt. **Skills** are reusable agent definitions with their own tool restrictions and context isolation. MCP secrets must use `${ENV_VAR}` expansion — never hardcode tokens.

---

## Chapter 4: Exercise 3 — Structured Data Extraction

Exercise 3 tackles a task that comes up constantly in real-world deployments: extracting structured data from unstructured documents — invoices, contracts, reports, purchase orders. The naive approach is to ask the model to "return JSON," but this is surprisingly fragile. Models may wrap the JSON in explanation text, skip fields they're uncertain about, hallucinate values for fields that aren't in the document, or produce slightly different key names than you specified. Exercise 3 shows a more reliable approach: use `tool_use` with a forced `tool_choice`, combine Pydantic schema validation with semantic validation, implement retry-with-feedback rather than retry-blind, and use the Batch API when processing hundreds of documents at once.

### 4a. Why Tool Use for Extraction?

When you ask a model to "return JSON," you are making a request in natural language. The model interprets that request as best it can and may include preamble ("Here is the extracted JSON:"), post-amble ("Let me know if this looks right"), or produce the JSON inside a Markdown code block. You then have to strip all of that, parse the JSON, and handle a hundred different ways the output can be malformed.

When you force a `tool_use` call, you are not asking — you are constraining. The model's response contains a `tool_use` block with an `input` field that is already a parsed Python dict matching your tool's input schema exactly. No text to strip, no JSON to parse, no ambiguity about whether the braces are in the right place. The output is always a structured object. This is the single most important reliability improvement you can make for extraction tasks.

### 4b. Schema Design (`schema.py`)

The tool's input schema is derived from a Pydantic model. The schema is split into two classes. `LineItem` represents a single line on an invoice:

```python
class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    total: float          # stored separately so the model can report its own arithmetic
```

`DocumentExtraction` composes `LineItem` and defines the complete shape of what the model is asked to produce:

```python
class DocumentExtraction(BaseModel):
    document_type: Literal["invoice", "contract", "report", "other"]
    vendor_name: str                          # always required
    total_amount: float | None = None         # nullable — may be absent in document
    line_items: list[LineItem] = []
    issue_date: str | None = None             # nullable
    stated_total: float | None = None
    calculated_total: float | None = None
    conflict_detected: bool = False           # semantic integrity flag
```

The nullable fields — `float | None = None` — are intentional and important. Without them, the model is forced to produce a value even when the document doesn't contain one. The result is hallucination: the model invents a plausible-looking date or amount. With `| None = None`, the model can (and should) return `null` for fields that are genuinely absent from the document, and your application can handle that gracefully.

The `conflict_detected` boolean is a semantic integrity flag. The model is instructed to set it to `true` if the `stated_total` on the document doesn't match the sum of `line_items`. This offloads simple arithmetic verification to the model and surfaces the discrepancy explicitly in the structured output rather than leaving it to downstream logic to detect.

The `required` array in `get_extraction_tool()` is equally deliberate:

```python
"required": ["document_type", "vendor_name", "conflict_detected"],
# total_amount deliberately omitted — nullable fields must not be required
```

Only fields that are always present in any valid document are listed as required. If `total_amount` were required, the model would be forced to hallucinate a value for a contract that has no dollar amounts. Required means "always extract this"; nullable means "extract if present, otherwise null."

### 4c. Forced Extraction (`extractor.py`)

The extractor sends a single API call with two key parameters: `tools` (the extraction tool definition) and `tool_choice` (forced selection):

```python
response = client.messages.create(
    model=MODEL,
    max_tokens=2048,
    tools=[get_extraction_tool()],
    tool_choice={"type": "tool", "name": "extract_document"},  # forced selection
    messages=[{"role": "user", "content": f"Extract data from this document:\n\n{document_text}"}],
)
for block in response.content:
    if block.type == "tool_use" and block.name == "extract_document":
        return block.input  # always a dict matching the schema
```

`tool_choice={"type": "tool", "name": "extract_document"}` tells the API that the model must call this specific tool — not "maybe call a tool" (`auto`), not "call any tool" (`any`), but this exact tool. The response will always contain a `tool_use` block with `name == "extract_document"`. The result is in `block.input`, which is already a Python dict — no JSON decoding, no parsing, no cleanup.

Although the forced `tool_choice` makes a missing `tool_use` block theoretically impossible, `extractor.py` still guards against it explicitly:

```python
    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_document":
            return block.input
    raise RuntimeError("No tool_use block in response — unexpected API behavior")
```

The `RuntimeError` at the end of the loop fires only if the API returns a response with no matching block — a signal of an unexpected API behavior change rather than a recoverable extraction failure. Crashing loudly here is correct: silently returning `None` or an empty dict would let bad data flow through validation and corrupt downstream processing.

### 4d. Semantic Validation + Retry (`validator.py`)

Pydantic schema validation runs automatically when the model's `block.input` is used to construct a `DocumentExtraction` instance. If the model returns a string where a float is expected, Pydantic raises a `ValidationError`. This catches type errors reliably.

Semantic validation goes further: it catches cases where the types are correct but the data is logically inconsistent. The most common example is a total mismatch:

```python
def validate_extraction(doc: DocumentExtraction) -> None:
    if (
        doc.stated_total is not None
        and doc.calculated_total is not None
        and not doc.conflict_detected
        and abs(doc.stated_total - doc.calculated_total) > 0.01  # float tolerance
    ):
        raise SemanticValidationError(
            f"stated_total ({doc.stated_total}) does not match "
            f"calculated_total ({doc.calculated_total}). "
            f"Set conflict_detected=true if this is intentional."
        )
```

The `0.01` tolerance handles floating-point arithmetic drift — $100.00 expressed as `99.999999...` due to floating-point representation should not be treated as a conflict. The function raises `SemanticValidationError` with a precise description of what went wrong.

When validation fails, the retry loop injects that specific error back into the next prompt:

```python
messages=[{
    "role": "user",
    "content": (
        f"The previous extraction had a validation error. Please fix it.\n\n"
        f"ORIGINAL DOCUMENT:\n{document_text}\n\n"
        f"FAILED EXTRACTION:\n{json.dumps(failed_extraction, indent=2)}\n\n"
        f"VALIDATION ERROR:\n{validation_error}\n\n"  # specific error
        f"Please re-extract with the error corrected."
    )
}]
```

The pattern of showing the model the original document, the failed output, and the specific error message is far more effective than a generic "try again." The model can see exactly what it produced, compare it to the original document, and understand precisely what constraint it violated. The loop caps retries at 3 to prevent infinite cycling on genuinely ambiguous documents.

### 4e. Batch API (`batch.py`)

The synchronous extraction API is appropriate when a user is waiting for a result. For offline pipelines — nightly ingestion of hundreds of invoices, bulk processing of a document archive — the Batch API is more appropriate. The trade-offs are:

- 50% cost savings compared to synchronous API calls
- Up to 100,000 requests per batch
- Processing window of up to 24 hours with no SLA guarantee
- Not suitable for any workflow where a user is blocking on the response

Each request in a batch carries a `custom_id` field — a string you control — that correlates requests to responses. Because batches are processed asynchronously, the response order is not guaranteed to match submission order. The `custom_id` is how you pair each result with the document that generated it.

The batch workflow in `batch.py` follows a three-step sequence: `submit_batch()` → `poll_batch()` → `handle_failures()`.

- `submit_batch(documents)` accepts a `{custom_id: document_text}` dict, builds one batch request per document with the forced `tool_choice`, calls `client.messages.batches.create()`, and returns the `batch_id`.
- `poll_batch(batch_id)` loops, calling `client.messages.batches.retrieve()` until `processing_status == "ended"`, then iterates the results and returns a `{custom_id: {"status": ..., "data": ...}}` dict.
- `handle_failures(batch_results, original_docs)` identifies entries where `status == "failed"` and returns a new `{custom_id: document_text}` dict containing only those documents — ready to pass straight back to `submit_batch()` for resubmission.

You resubmit only the failed items, not the entire batch — this keeps retry costs low and avoids reprocessing documents that already succeeded.

```bash
cd /Users/xiaoxu/Projects/claude-architect-exercises
uv run python -m ex3_extraction.main
```

The demo runs against three synthetic documents. The first is a complete invoice with all fields present: vendor name, issue date, line items, and a stated total that matches the sum — `conflict_detected` comes back `false`. The second is a sparse contract with no dollar amounts and no line items: all numeric fields come back as `null`, demonstrating that the model correctly avoids hallucinating values. The third is an invoice where the stated total deliberately doesn't match the sum of line items: `conflict_detected` comes back `true`, and the semantic validator confirms the extraction is internally consistent (it correctly identified the conflict).

---

> **Exam tip:** `tool_choice` has three modes: `{"type": "auto"}` (default — model decides whether to use tools), `{"type": "any"}` (model must use at least one tool), `{"type": "tool", "name": "..."}` (model must use this specific tool). Use the `"tool"` mode when you need guaranteed structured output. The Batch API is ideal for offline pipelines — never use it for user-facing requests that need a response in under 1 minute.

---

## Chapter 5: Exercise 4 — Multi-Agent Research Pipeline

Exercise 4 builds a hub-and-spoke research pipeline. A coordinator agent receives a research topic, dispatches two specialized subagents in parallel — one that searches the web, one that analyzes internal documents — collects both results, hands them to a synthesis agent that merges findings, and finally passes the synthesis to a report agent that writes the final output. The key engineering challenges are not the Claude API calls themselves but everything around them: how to run subagents concurrently without waiting for each one, how to propagate failures without crashing the pipeline, how to pass context between agents without shared mutable state, and how to produce a useful report even when some data sources are unavailable.

### 5a. Context & Error Models

Before looking at how subagents communicate failures, it is worth examining what a successful finding looks like. The `Finding` model is the atomic unit of research output:

```python
class Finding(BaseModel):
    claim: str
    evidence_excerpt: str
    source_url: str                              # mandatory source attribution
    publication_date: str | None = None          # ISO date; None prevents temporal misinterpretation
    confidence: float                            # 0.0–1.0

    @field_validator("confidence")
    @classmethod
    def confidence_must_be_valid(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be between 0 and 1, got {v}")
        return v
```

Every finding carries mandatory source attribution (`source_url`, `publication_date`) so the synthesis agent can cite sources and readers can verify claims. The `confidence` field has an explicit Pydantic `@field_validator` that rejects any value outside the 0–1 range at construction time, preventing bad data from ever entering `ResearchContext`.

`ResearchContext` acts as a mutable accumulator for the pipeline's findings. Its `add_findings(new_findings)` method appends a list of `Finding` objects to the internal `findings` list. The coordinator calls it once per successful subagent result — first with the web search findings, then with the document analysis findings — building up a single unified list before passing the context to the synthesis agent. This design keeps accumulation logic in one place rather than scattered across the coordinator method.

The first design decision is how subagents communicate results back to the coordinator. A naive approach would have each subagent function either return findings or raise an exception. This forces the coordinator to wrap every call in try/except, which makes parallel execution awkward and makes failure modes implicit rather than documented.

Exercise 4 takes a different approach: subagents always return a typed `SubagentResult`, regardless of success or failure:

```python
class SubagentResult(BaseModel):
    success: bool
    findings: list = []
    error: SubagentError | None = None   # structured, not opaque
    coverage_note: str = ""
```

The coordinator always receives a value. It inspects `success` to decide what to do. There is no exception to catch, no hidden failure mode. The `error` field, when present, is not an opaque string — it is a `SubagentError`:

```python
class SubagentError(BaseModel):
    failure_type: Literal["timeout", "not_found", "parse_error", "rate_limit"]
    attempted_query: str
    partial_results: list       # what was found before failure
    alternatives: list[str]     # recovery suggestions
```

`failure_type` as a `Literal` means the coordinator can match on the value programmatically — `if error.failure_type == "rate_limit": schedule_retry()`. `partial_results` carries whatever the subagent managed to find before it failed, so a partial web search isn't a total loss. `alternatives` gives the coordinator concrete options: try a different query, use a fallback source, or simply annotate the gap. This is structured error propagation — failures are first-class citizens in the type system, not exceptional cases to be caught and suppressed.

### 5b. Parallel Execution (`coordinator.py`)

The coordinator's central method is `gather_research()`, which starts both subagents simultaneously using `asyncio.gather`:

```python
async def gather_research(self, topic: str) -> ResearchContext:
    ctx = ResearchContext(topic=topic)

    # Both subagents start simultaneously
    web_result, doc_result = await asyncio.gather(
        self.run_web_search(topic),
        self.run_doc_analysis(topic),
    )

    if web_result.success:
        ctx.add_findings(web_result.findings)
    else:
        ctx.coverage_gaps.append(f"Web: {web_result.error.attempted_query}")

    if doc_result.success:
        ctx.add_findings(doc_result.findings)
    else:
        ctx.coverage_gaps.append(f"Docs: {doc_result.error.attempted_query}")

    return ctx
```

`asyncio.gather` submits both coroutines to the event loop at the same time. If each subagent takes 3 seconds to complete, `gather` returns after approximately 3 seconds — not 6. This is the correct tool for independent tasks: run them concurrently, wait for all of them, then process results. Compare this to awaiting each coroutine sequentially, which would incur the full sum of all latencies.

When a subagent fails, the failure is added to `coverage_gaps` rather than raised. This is a deliberate architectural choice: a partial result with documented gaps is more useful than a crash. The final report will include a section noting what data sources were unavailable and what queries were attempted — the reader can assess how complete the research is. Suppressing the failure silently, by contrast, would produce a report that appears authoritative but is secretly missing a data source.

### 5c. Explicit Context Passing

Each subagent receives exactly the context it needs through its parameters. There is no global state, no shared memory, no implicit inheritance from the coordinator's internal variables. A subagent function signature looks like `run_doc_analysis(topic: str, prior_context: str | None = None)` — everything is passed in explicitly.

The `ResearchContext` object accumulates findings from all subagents and can serialize itself into a formatted string for injection into the next agent's prompt:

```python
def to_prompt_context(self) -> str:
    lines = [f"Research topic: {self.topic}\n\nFindings:"]
    for i, f in enumerate(self.findings, 1):
        lines.append(
            f"{i}. CLAIM: {f.claim}\n"
            f"   SOURCE: {f.source_url} (date: {f.publication_date or 'unknown'})\n"
            f"   EXCERPT: {f.evidence_excerpt}\n"
            f"   CONFIDENCE: {f.confidence:.0%}"
        )
    return "\n".join(lines)
```

The synthesis agent receives this string as part of its system or user prompt. It knows every finding that was collected, the source URL and publication date for each one, the supporting excerpt, and a confidence score. It doesn't need access to any Python objects — just the serialized representation. This is what makes the synthesis and report agents independently testable: you can call them with a manually crafted context string and verify their output without running the full pipeline.

```bash
cd /Users/xiaoxu/Projects/claude-architect-exercises
uv run python -m ex4_research.main
```

The demo runs two scenarios. The first uses a broad AI topic — both the web search and document analysis subagents return findings, the synthesis agent merges them, and the report agent produces a structured report with sources cited. The second uses a narrow quantum computing / pharmaceutical topic where both subagents return `not_found` errors — the final output is a report that contains a coverage gaps section explaining which queries were attempted and came up empty, rather than a crash or a fabricated report.

---

> **Exam tip:** Use `asyncio.gather` when subagents are independent — it runs them concurrently and collects all results before proceeding. Coordinator agents should annotate failures as coverage gaps rather than raising exceptions — a report with documented limitations is more useful than a crash. Never suppress a `SubagentError` silently; always surface it somehow, even if just as a note in the final output.

---

## Chapter 6: Patterns Reference

The following table summarizes every Claude API and Claude Code pattern covered in this tutorial. Use it as a quick reference when preparing for the exam or revisiting a specific technique. Each row links a named pattern to the file that implements it and describes what the pattern achieves.

| Pattern | File | What It Does | Exam Relevance |
|---------|------|-------------|----------------|
| tool_use loop | `ex1_agent/agent.py` | `while True` / `stop_reason` control flow | Core agentic pattern |
| Programmatic gate | `ex1_agent/agent.py` | Block tools until prerequisite met | Safety / ordering |
| Pre-tool hook | `ex1_agent/hooks.py` | Intercept + redirect before execution | Deterministic enforcement |
| Post-tool hook | `ex1_agent/hooks.py` | Normalize results before model sees them | Data transformation |
| Structured tool error | `ex1_agent/tools.py` | Return ToolError dict instead of raising | Graceful agent recovery |
| Path-scoped rules | `ex2_claude_code/.claude/rules/` | Claude Code context injection | Claude Code config |
| Forced tool_use | `ex3_extraction/extractor.py` | `tool_choice={"type":"tool"}` | Guaranteed structured output |
| Semantic validation | `ex3_extraction/validator.py` | Catch model reasoning errors post-extraction | Output quality |
| Retry with feedback | `ex3_extraction/validator.py` | Inject specific error into next prompt | Iterative correction |
| Batch API | `ex3_extraction/batch.py` | Async bulk, 50% cost, 24h window | Cost optimization |
| asyncio.gather | `ex4_research/coordinator.py` | Parallel subagent execution | Performance |
| Structured error propagation | `ex4_research/errors.py` | `SubagentResult` union type | Fault tolerance |
| Explicit context passing | `ex4_research/subagents.py` | No implicit state inheritance | Testability |
| Hub-and-spoke | `ex4_research/coordinator.py` | Central coordinator, focused subagents | Architecture |

---

*Tutorial complete. Run `uv run pytest` to verify all 49 tests pass.*
