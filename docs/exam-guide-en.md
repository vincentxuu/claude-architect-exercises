# Claude Certified Architect – Foundations: Exam Study Guide

> A structured study companion for the Claude Certified Architect – Foundations certification exam. Use this alongside the [hands-on tutorial](tutorial-en.md) and the official Exam Guide PDF for complete preparation.

**Chinese version:** [docs/exam-guide-zh.md](exam-guide-zh.md)

---

## Exam Overview

### What This Exam Tests
- Validates practical judgment about tradeoffs when building production solutions with Claude
- Tests across: Claude Code, Claude Agent SDK, Claude API, and MCP
- Grounded in realistic scenarios from actual customer use cases

### Format & Scoring
- All multiple choice (1 correct + 3 distractors)
- No penalty for guessing — answer everything
- Scaled score: 100–1,000; passing score: 720
- Pass/fail designation

### Target Candidate
- Solution architects designing & implementing production apps with Claude
- 6+ months practical experience with Claude APIs, Agent SDK, Claude Code, MCP
- Hands-on experience with: agentic applications, CLAUDE.md configuration, MCP tool/resource design, structured output engineering, context window management, CI/CD integration, escalation/reliability decisions

---

## Content Domains at a Glance

| Domain | Weight | Core Focus | Tutorial Chapters |
|--------|--------|------------|-------------------|
| 1. Agentic Architecture & Orchestration | 27% | Agentic loops, multi-agent coordination, hooks, gates, session management | Ch 1–2, Ch 5 |
| 2. Tool Design & MCP Integration | 18% | Tool descriptions, structured errors, tool distribution, MCP config, built-in tools | Ch 1–2, Ch 3 |
| 3. Claude Code Configuration & Workflows | 20% | CLAUDE.md, rules, commands, skills, MCP, plan mode, CI/CD | Ch 3 |
| 4. Prompt Engineering & Structured Output | 20% | Explicit criteria, few-shot, tool_use schemas, validation/retry, batch API, multi-pass review | Ch 4 |
| 5. Context Management & Reliability | 15% | Context preservation, escalation, error propagation, large codebase exploration, human review, provenance | Ch 5 |

---

## Exam Scenarios

The exam presents 4 scenarios (randomly chosen from 6). Each scenario frames a set of questions around a realistic production context.

### Scenario 1: Customer Support Resolution Agent
- Building a customer support agent with Claude Agent SDK
- MCP tools: `get_customer`, `lookup_order`, `process_refund`, `escalate_to_human`
- Target: 80%+ first-contact resolution with proper escalation
- **Domains tested:** 1, 2, 5
- **Tutorial connection:** Exercise 1 (ex1_agent) directly implements this scenario

### Scenario 2: Code Generation with Claude Code
- Using Claude Code for code generation, refactoring, debugging, documentation
- Custom slash commands, CLAUDE.md configurations, plan mode vs direct execution
- **Domains tested:** 3, 5
- **Tutorial connection:** Exercise 2 (ex2_claude_code) covers all config types

### Scenario 3: Multi-Agent Research System
- Coordinator agent → web search + document analysis subagents → synthesis → report
- Hub-and-spoke architecture with parallel subagent execution
- **Domains tested:** 1, 2, 5
- **Tutorial connection:** Exercise 4 (ex4_research) implements this pipeline

### Scenario 4: Developer Productivity with Claude
- Agent SDK-based tools for exploring codebases, understanding legacy systems, generating boilerplate
- Built-in tools (Read, Write, Bash, Grep, Glob) + MCP servers
- **Domains tested:** 2, 3, 1

### Scenario 5: Claude Code for Continuous Integration
- Claude Code in CI/CD pipeline: automated code reviews, test generation, PR feedback
- Prompts that provide actionable feedback and minimize false positives
- **Domains tested:** 3, 4

### Scenario 6: Structured Data Extraction
- Extracting structured data from unstructured documents using JSON schemas
- Edge case handling, downstream system integration
- **Domains tested:** 4, 5
- **Tutorial connection:** Exercise 3 (ex3_extraction) directly implements this scenario

---

## Domain 1: Agentic Architecture & Orchestration (27%)

*This is the highest-weighted domain. Master it.*

### 1.1 Agentic Loop Design
**Key concepts:**
- The agentic loop lifecycle: send request → inspect `stop_reason` → dispatch tools → append results → repeat
- `stop_reason` values: `"tool_use"` (keep looping), `"end_turn"` (done), `"max_tokens"` (hit limit — handle it!), `"stop_sequence"`
- Tool results are appended to conversation history so the model can reason about what happened
- **Anti-patterns to avoid:** parsing natural language signals for loop termination, arbitrary iteration caps as primary stopping mechanism, checking assistant text for completion indicators

**Tutorial reference:** `ex1_agent/agent.py` — the `run()` method implements the canonical `while True` / `stop_reason` pattern

### 1.2 Multi-Agent Coordination (Coordinator-Subagent)
**Key concepts:**
- Hub-and-spoke: coordinator manages all inter-subagent communication, error handling, information routing
- Subagents have **isolated context** — they do NOT inherit the coordinator's conversation history
- Coordinator responsibilities: task decomposition, delegation, result aggregation, deciding which subagents to invoke
- **Risk:** overly narrow task decomposition → incomplete coverage (e.g., "creative industries" decomposed only into visual arts, missing music/writing/film)

**Tutorial reference:** `ex4_research/coordinator.py` — `gather_research()` with `asyncio.gather`

### 1.3 Subagent Invocation & Context Passing
**Key concepts:**
- `Task` tool spawns subagents; coordinator's `allowedTools` must include `"Task"`
- Subagent context must be **explicitly provided** in the prompt — no automatic inheritance
- `AgentDefinition` configuration: descriptions, system prompts, tool restrictions per subagent type
- `fork_session` for exploring divergent approaches from a shared baseline
- Spawn parallel subagents by emitting multiple `Task` tool calls in a single response

**Tutorial reference:** `ex4_research/subagents.py` — explicit parameter passing, no shared state

### 1.4 Enforcement & Handoff Patterns
**Key concepts:**
- **Programmatic enforcement** (hooks, prerequisite gates) vs **prompt-based guidance** — use programmatic when deterministic compliance is required (e.g., identity verification before financial operations)
- Pre-tool hooks: intercept and redirect before execution (e.g., block refunds > $500 → escalate)
- Programmatic gates: block downstream tools until prerequisites met (e.g., `process_refund` blocked until `get_customer` returns verified ID)
- Structured handoff summaries for escalation: customer ID, root cause, refund amount, recommended action

**Tutorial reference:** `ex1_agent/hooks.py` (HookInterception, pre/post hooks), `ex1_agent/agent.py` (ProgrammaticGateError)

### 1.5 Agent SDK Hooks
**Key concepts:**
- `PostToolUse` hooks: intercept tool results for transformation before model processes them (normalize timestamps, status codes)
- Hook patterns that enforce compliance rules (blocking policy-violating actions)
- Hooks provide **deterministic guarantees**; prompt instructions provide **probabilistic compliance**
- Choose hooks when business rules require guaranteed compliance

**Tutorial reference:** `ex1_agent/hooks.py` — `run_post_tool_hook()` normalizes Unix timestamps to ISO 8601

### 1.6 Task Decomposition Strategies
**Key concepts:**
- Fixed sequential pipelines (prompt chaining) vs dynamic adaptive decomposition
- Prompt chaining: analyze each file individually → cross-file integration pass
- Adaptive plans: generate subtasks based on what's discovered at each step
- Split large code reviews into per-file local passes + cross-file integration pass to avoid attention dilution

### 1.7 Session Management
**Key concepts:**
- `--resume <session-name>` to continue named sessions
- `fork_session` for parallel exploration branches
- Starting fresh with structured summary is more reliable than resuming with stale tool results
- When resuming, inform the agent about specific file changes for targeted re-analysis

---

## Domain 2: Tool Design & MCP Integration (18%)

### 2.1 Tool Interface Design
**Key concepts:**
- Tool descriptions are the **primary mechanism** LLMs use for tool selection — minimal descriptions → unreliable selection
- Include: input formats, example queries, edge cases, boundary explanations in descriptions
- Ambiguous/overlapping descriptions cause misrouting (e.g., `analyze_content` vs `analyze_document` with near-identical descriptions)
- System prompt keyword-sensitive instructions can create unintended tool associations

**Fix strategies:** Rename tools to eliminate overlap, split generic tools into purpose-specific ones with defined I/O contracts

**Tutorial reference:** `ex1_agent/tools.py` — compare the detailed `get_customer` description vs a vague "Look up a customer"

### 2.2 Structured Error Responses for MCP Tools
**Key concepts:**
- MCP `isError` flag for communicating failures back to the agent
- Error categories: transient (timeout), validation (bad input), business (policy violation), permission
- **Why uniform errors are bad:** "Operation failed" prevents appropriate recovery decisions
- Distinguish: access failures (needing retry) vs valid empty results (successful query, no matches)

**Tutorial reference:** `shared/types.py` — `ToolError` with `errorCategory`, `isRetryable`, `message`

### 2.3 Tool Distribution & tool_choice
**Key concepts:**
- Too many tools (18 instead of 4-5) degrades selection reliability
- Agents with tools outside their specialization tend to misuse them
- Scoped tool access: give each agent only tools for its role
- `tool_choice` options: `"auto"` (model decides), `"any"` (must use a tool), `{"type": "tool", "name": "..."}` (must use this specific tool)
- Forced selection for guaranteed structured output; `"any"` when multiple extraction schemas exist

**Tutorial reference:** `ex3_extraction/extractor.py` — forced `tool_choice` for extraction

### 2.4 MCP Server Integration
**Key concepts:**
- Project-level `.mcp.json` for shared team tooling; user-level `~/.claude.json` for personal/experimental
- Environment variable expansion: `${GITHUB_TOKEN}` — **never hardcode secrets**
- Tools from all configured MCP servers are discovered at connection time
- MCP resources: expose content catalogs (issue summaries, documentation hierarchies, database schemas) to reduce exploratory tool calls
- Prefer existing community MCP servers over custom implementations for standard integrations

**Tutorial reference:** `ex2_claude_code/.mcp.json` — GitHub MCP server with `${GITHUB_TOKEN}`

### 2.5 Built-in Tools Selection
**Key concepts:**
- **Grep:** content search (function names, error messages, import statements)
- **Glob:** file path pattern matching (find files by name or extension)
- **Read/Write:** full file operations; **Edit:** targeted modifications using unique text matching
- When Edit fails (non-unique match): use Read + Write as fallback
- Build codebase understanding incrementally: Grep → find entry points → Read to follow imports and trace flows

---

## Domain 3: Claude Code Configuration & Workflows (20%)

### 3.1 CLAUDE.md Hierarchy
**Key concepts:**
- Three levels: user (`~/.claude/CLAUDE.md`), project (`.claude/CLAUDE.md` or root `CLAUDE.md`), directory (subdirectory `CLAUDE.md`)
- User-level = personal only, not shared via version control
- `@import` syntax for referencing external files to keep CLAUDE.md modular
- `.claude/rules/` directory for topic-specific rule files as alternative to monolithic CLAUDE.md

**Tutorial reference:** `ex2_claude_code/CLAUDE.md` and the configuration hierarchy explanation in Ch 3

### 3.2 Custom Commands & Skills
**Key concepts:**
- **Commands** (`.claude/commands/`): project-scoped, shared via version control, user-invoked slash commands
- **Skills** (`.claude/skills/`): reusable agent definitions with frontmatter
  - `context: fork` — isolated execution context, doesn't pollute main session
  - `allowed-tools` — whitelist restricting tool access (safety boundary)
  - `argument-hint` — placeholder prompting user for input
- Personal commands: `~/.claude/commands/` (not shared)
- Personal skill variants: `~/.claude/skills/` with different names to avoid affecting teammates
- Choose skills (on-demand) vs CLAUDE.md (always-loaded) based on whether context is universal or task-specific

### 3.3 Path-Specific Rules
**Key concepts:**
- `.claude/rules/` files with YAML frontmatter `paths:` field containing glob patterns
- Rules load only when editing matching files → reduces irrelevant context and token usage
- Advantage over directory-level CLAUDE.md: rules with glob patterns work for conventions spanning multiple directories (e.g., `**/*.test.tsx` for all test files)

**Tutorial reference:** `ex2_claude_code/.claude/rules/` — React component conventions scoped to `src/components/**/*`

### 3.4 Plan Mode vs Direct Execution
**Key concepts:**
- **Plan mode:** complex tasks, large-scale changes, multiple valid approaches, architectural decisions, multi-file modifications
- **Direct execution:** simple, well-scoped changes (single-file bug fix, adding a validation check)
- Plan mode enables safe exploration before committing to changes
- Use Explore subagent for verbose discovery to preserve main context
- Can combine: plan mode for investigation → direct execution for implementation

### 3.5 Iterative Refinement
**Key concepts:**
- Concrete input/output examples are most effective when prose descriptions are interpreted inconsistently
- Test-driven iteration: write tests first → share failures → guide improvement
- Interview pattern: have Claude ask questions to surface considerations the developer didn't anticipate
- When to provide all issues in one message (interacting problems) vs fix sequentially (independent problems)

### 3.6 CI/CD Integration
**Key concepts:**
- `-p` (or `--print`) flag for non-interactive mode in automated pipelines
- `--output-format json` + `--json-schema` for structured CI output
- CLAUDE.md provides project context (testing standards, review criteria) to CI-invoked Claude Code
- Session context isolation: same session that generated code is less effective at reviewing it — use independent review instance
- Include prior review findings when re-running reviews to avoid duplicate comments

---

## Domain 4: Prompt Engineering & Structured Output (20%)

### 4.1 Explicit Criteria for Precision
**Key concepts:**
- Explicit criteria > vague instructions: "flag comments only when claimed behavior contradicts actual code" vs "check that comments are accurate"
- General instructions like "be conservative" or "only report high-confidence findings" fail to improve precision
- High false positive rates in one category undermine confidence in accurate categories
- Write specific review criteria defining what to report (bugs, security) vs skip (minor style, local patterns)

### 4.2 Few-Shot Prompting
**Key concepts:**
- Most effective technique for consistently formatted, actionable output when detailed instructions alone fail
- Show reasoning for ambiguous cases (why one action chosen over alternatives)
- Enable generalization to novel patterns, not just matching pre-specified cases
- Reduce hallucination in extraction tasks (informal measurements, varied document structures)
- Use 2-4 targeted examples for ambiguous scenarios

### 4.3 Structured Output via tool_use + JSON Schemas
**Key concepts:**
- `tool_use` with JSON schemas = most reliable approach for guaranteed schema-compliant output (eliminates JSON syntax errors)
- `tool_choice: "auto"` (may return text), `"any"` (must call a tool), `{"type": "tool", "name": "..."}` (must call specific tool)
- Strict JSON schemas eliminate syntax errors but NOT semantic errors (values in wrong fields, totals that don't sum)
- Schema design: required vs optional fields, enum with `"other"` + detail string pattern, nullable fields to prevent hallucination

**Tutorial reference:** `ex3_extraction/schema.py` — `DocumentExtraction` with nullable fields, `conflict_detected` flag

### 4.4 Validation, Retry, and Feedback Loops
**Key concepts:**
- Retry-with-error-feedback: append specific validation errors to retry prompt to guide correction
- Retries are ineffective when information is simply absent from source (vs format/structural errors)
- `detected_pattern` field in findings enables systematic analysis of false positive dismissal patterns
- Semantic validation: "calculated_total" alongside "stated_total" to flag discrepancies

**Tutorial reference:** `ex3_extraction/validator.py` — semantic validation + retry loop with specific error injection

### 4.5 Batch Processing
**Key concepts:**
- Message Batches API: 50% cost savings, up to 24-hour processing window, no latency SLA
- Appropriate for: overnight reports, weekly audits, nightly test generation
- NOT appropriate for: blocking workflows (pre-merge checks)
- No multi-turn tool calling within a single batch request
- `custom_id` for correlating request/response pairs
- Resubmit only failed items (identified by `custom_id`), not entire batch

**Tutorial reference:** `ex3_extraction/batch.py` — submit → poll → handle_failures workflow

### 4.6 Multi-Instance & Multi-Pass Review
**Key concepts:**
- Self-review limitation: model retains reasoning context, less likely to question own decisions
- Independent review instances (without prior reasoning) catch more subtle issues
- Multi-pass for large reviews: per-file local analysis + cross-file integration pass
- Verification passes with model self-reported confidence for calibrated routing

---

## Domain 5: Context Management & Reliability (15%)

### 5.1 Context Preservation
**Key concepts:**
- Progressive summarization risks: condensing numbers, dates, percentages into vague summaries
- "Lost in the middle" effect: models reliably process beginning and end of long inputs, may omit middle
- Tool results accumulate tokens disproportionately to relevance (40+ fields when only 5 needed)
- Extract transactional facts into persistent "case facts" block, outside summarized history
- Place key findings at beginning of aggregated inputs; organize with explicit section headers

### 5.2 Escalation & Ambiguity Resolution
**Key concepts:**
- Escalation triggers: customer requests for human, policy exceptions/gaps, inability to make progress
- NOT just complex cases — honor explicit customer requests immediately
- Sentiment-based escalation and self-reported confidence are unreliable proxies for case complexity
- Multiple customer matches → request clarification, don't select by heuristic
- Add explicit escalation criteria with few-shot examples to system prompt

### 5.3 Error Propagation in Multi-Agent Systems
**Key concepts:**
- Structured error context (failure type, attempted query, partial results, alternatives) enables intelligent coordinator recovery
- Distinguish access failures (timeout → retry decision) from valid empty results (no matches)
- Generic error statuses hide valuable context from coordinator
- Anti-patterns: silently suppressing errors (returning empty as success) OR terminating entire workflow on single failure
- Subagents should implement local recovery for transient failures, propagate only unresolvable errors

**Tutorial reference:** `ex4_research/errors.py` — `SubagentResult` with `SubagentError`

### 5.4 Large Codebase Exploration
**Key concepts:**
- Context degradation in extended sessions: models reference "typical patterns" instead of specific classes
- Scratchpad files for persisting key findings across context boundaries
- Subagent delegation for verbose exploration; main agent maintains high-level coordination
- Structured state persistence for crash recovery: agents export state to known location, coordinator loads manifest on resume
- Use `/compact` to reduce context usage during verbose exploration sessions

### 5.5 Human Review & Confidence Calibration
**Key concepts:**
- Aggregate accuracy (97%) may mask poor performance on specific document types or fields
- Stratified random sampling for measuring error rates in high-confidence extractions
- Field-level confidence scores calibrated using labeled validation sets
- Validate accuracy by document type AND field segment before automating high-confidence extractions
- Route low-confidence or ambiguous extractions to human review

### 5.6 Information Provenance in Multi-Source Synthesis
**Key concepts:**
- Source attribution lost during summarization when claim-source mappings aren't preserved
- Synthesis agent must preserve and merge claim-source mappings
- Conflicting statistics from credible sources: annotate conflicts with attribution, don't arbitrarily select one
- Require publication/collection dates to prevent temporal misinterpretation
- Different content types rendered differently: financial data as tables, news as prose, technical findings as structured lists

**Tutorial reference:** `ex4_research/context.py` — `ResearchContext.to_prompt_context()` preserves source URLs and dates

---

## Sample Questions Analysis

### Q1: Agent skips `get_customer` 12% of the time → misidentified accounts
**Answer: A** — Programmatic prerequisite gate. When tool sequence is critical (identity verification before financial operations), programmatic enforcement provides deterministic guarantees. Prompt-based approaches (B, C) are probabilistic. Routing classifier (D) addresses tool availability, not ordering.

### Q2: Agent calls `get_customer` instead of `lookup_order` for order queries
**Answer: B** — Expand tool descriptions with input formats, example queries, boundaries. Tool descriptions are the primary mechanism for selection. Low-effort, high-leverage fix. Few-shot examples (A) add tokens without fixing root cause. Routing layer (C) is over-engineered. Consolidation (D) is valid but disproportionate effort.

### Q3: Agent escalates simple cases, handles complex ones autonomously (55% resolution vs 80% target)
**Answer: A** — Add explicit escalation criteria with few-shot examples showing when to escalate vs resolve. Addresses unclear decision boundaries. Self-reported confidence (B) is poorly calibrated. Separate classifier (C) requires labeled data/ML infrastructure. Sentiment (D) doesn't correlate with case complexity.

### Q4: Where to create `/review` command shared across team?
**Answer: A** — `.claude/commands/` in the project repository. Version-controlled, automatically available. `~/.claude/commands/` (B) is personal only. CLAUDE.md (C) is for instructions, not commands. `.claude/config.json` with `commands` array (D) doesn't exist.

### Q5: Monolith → microservices restructuring approach?
**Answer: A** — Enter plan mode. Complex tasks with multiple valid approaches and architectural decisions need exploration before committing. Direct execution (B) risks costly rework. Comprehensive upfront instructions (C) assume you know the structure. Reactive plan mode (D) ignores that complexity is already known.

### Q6: Different conventions for React/API/DB/tests spread across directories?
**Answer: A** — `.claude/rules/` with YAML frontmatter glob patterns. Automatically applies conventions by file path regardless of location. Root CLAUDE.md (B) relies on inference. Skills (C) require manual invocation. Subdirectory CLAUDE.md (D) can't handle files spread across many directories.

### Q7: Research on "AI in creative industries" covers only visual arts
**Answer: B** — Coordinator's task decomposition too narrow. Decomposed into only visual arts subtasks, omitting music/writing/film. Subagents executed correctly within their assigned scope. The problem is WHAT they were assigned, not HOW they executed.

### Q8: Web search subagent times out — best error propagation?
**Answer: A** — Return structured error context (failure type, attempted query, partial results, alternatives). Enables intelligent coordinator recovery. Generic status (B) hides context. Suppressing as success (C) produces incomplete output silently. Terminating workflow (D) is unnecessarily destructive.

### Q9: Synthesis agent needs fact verification, adding 2-3 round trips (40% latency increase)
**Answer: A** — Give synthesis agent a scoped `verify_fact` tool for simple lookups (85% of cases), complex verifications still go through coordinator. Least privilege principle. Batching (B) creates blocking dependencies. Full web search tools (C) violates separation of concerns. Proactive caching (D) can't predict verification needs.

### Q10: CI pipeline hangs waiting for interactive input
**Answer: A** — Use `-p` flag: `claude -p "Analyze this pull request for security issues"`. The documented non-interactive mode. Other options reference non-existent features.

### Q11: Switching both workflows to Batch API for 50% savings?
**Answer: A** — Batch for overnight technical debt reports only; keep real-time for pre-merge checks. Batch API has no latency SLA (up to 24 hours) — unsuitable for blocking workflows.

### Q12: Single-pass review of 14-file PR produces inconsistent results
**Answer: A** — Split into per-file focused passes + cross-file integration pass. Addresses attention dilution directly. Smaller PRs (B) shifts burden. Larger context window (C) doesn't solve attention quality. Consensus filtering (D) would suppress intermittently-caught real bugs.

---

## Cross-Reference: Exam Domains ↔ Tutorial Exercises

| Exercise | Tutorial Chapter | Primary Domains |
|----------|-----------------|-----------------|
| ex1_agent (Multi-Tool Agent) | Ch 2 | Domain 1 (agentic loops, hooks, gates), Domain 2 (tool design, structured errors) |
| ex2_claude_code (Configuration) | Ch 3 | Domain 3 (CLAUDE.md, rules, commands, skills, MCP) |
| ex3_extraction (Structured Data) | Ch 4 | Domain 4 (tool_use schemas, validation/retry, batch API) |
| ex4_research (Multi-Agent Pipeline) | Ch 5 | Domain 1 (coordinator-subagent), Domain 2 (tool distribution), Domain 5 (error propagation, provenance) |

---

## Quick-Reference: Key API Details

| Concept | Values / Syntax | When to Use |
|---------|----------------|-------------|
| `stop_reason` | `"tool_use"`, `"end_turn"`, `"max_tokens"`, `"stop_sequence"` | Agentic loop control flow |
| `tool_choice` | `"auto"`, `"any"`, `{"type":"tool","name":"..."}` | `auto` = default; `any` = must use tool; forced = guaranteed structured output |
| `tool_result` fields | `type`, `tool_use_id`, `content`, `is_error` | Every tool result must match `tool_use_id` from the tool_use block |
| Error categories | `transient`, `validation`, `permission`, `business` | Structured error handling in tool responses |
| CLAUDE.md levels | user (`~/.claude/`), project (root/.claude/), directory | User = personal; project = shared; directory = scoped |
| Rules frontmatter | `paths: ["glob/**/*"]` | Load rules only when editing matching files |
| Skills frontmatter | `context: fork`, `allowed-tools`, `argument-hint` | Isolated execution, restricted tool access |
| MCP config | `.mcp.json` (project), `~/.claude.json` (user) | `${ENV_VAR}` for secrets — never hardcode |
| CI flags | `-p` / `--print`, `--output-format json`, `--json-schema` | Non-interactive mode, structured CI output |
| Batch API | `custom_id`, 50% savings, ≤24h, no multi-turn tools | Offline pipelines only — never blocking workflows |

---

## Preparation Checklist

1. [ ] **Build an agentic loop** — Implement `while True` / `stop_reason` control flow with tool dispatching
2. [ ] **Add hooks and gates** — Pre-tool hooks for business rule enforcement, programmatic gates for ordering
3. [ ] **Configure Claude Code** — CLAUDE.md hierarchy, path-scoped rules, commands, skills, MCP
4. [ ] **Design tool descriptions** — Differentiate similar tools, include boundaries and examples
5. [ ] **Build structured extraction** — `tool_use` with forced `tool_choice`, nullable schema fields, semantic validation
6. [ ] **Implement retry-with-feedback** — Inject specific errors into retry prompts
7. [ ] **Design batch processing** — Submit → poll → handle failures workflow with `custom_id`
8. [ ] **Build multi-agent pipeline** — Coordinator with parallel subagents, explicit context passing, structured error propagation
9. [ ] **Practice few-shot prompting** — Targeted examples for ambiguous scenarios
10. [ ] **Run all exercises** — `uv run pytest` should show 49 passed

---

## Out-of-Scope Topics

These will NOT appear on the exam:
- Fine-tuning Claude / training custom models
- API authentication, billing, account management
- Detailed programming language implementations (beyond tool/schema config)
- Deploying/hosting MCP servers (infrastructure, networking)
- Claude's internal architecture, training, model weights
- Constitutional AI, RLHF, safety training
- Embedding models, vector databases
- Computer use (browser automation)
- Vision/image analysis
- Streaming API, server-sent events
- Rate limiting, quotas, pricing
- OAuth, API key rotation
- Cloud provider configurations (AWS, GCP, Azure)
- Performance benchmarking, model comparison
- Prompt caching implementation details
- Token counting algorithms

---

*Use this guide alongside the [hands-on tutorial](tutorial-en.md) and the official exam guide PDF. Run `uv run pytest` to verify your exercises work.*
