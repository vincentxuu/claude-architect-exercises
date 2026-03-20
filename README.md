# Claude Certified Architect — Foundations Exercises

[繁體中文版](#繁體中文) | English

Production-quality implementations of all 4 preparation exercises from the [Claude Certified Architect — Foundations](https://anthropic.skilljar.com/claude-certified-architect-foundations-access-request) exam guide, demonstrating core Claude API patterns: agentic loops, Claude Code configuration, structured extraction, and multi-agent orchestration.

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# 3. Verify setup
uv run pytest          # 49 tests should pass
```

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/), an [Anthropic API key](https://console.anthropic.com)

## Exercises

| #   | Exercise              | Run Command                                 | Key Patterns                                            |
| --- | --------------------- | ------------------------------------------- | ------------------------------------------------------- |
| 1   | Multi-Tool Agent      | `uv run python -m ex1_agent.main`           | Agentic loop, programmatic gates, pre/post hooks        |
| 2   | Claude Code Config    | `uv run python ex2_claude_code/validate.py` | CLAUDE.md, rules, commands, skills, MCP                 |
| 3   | Structured Extraction | `uv run python -m ex3_extraction.main`      | Forced tool_use, semantic validation, batch API         |
| 4   | Multi-Agent Research  | `uv run python -m ex4_research.main`        | Coordinator-subagent, asyncio.gather, error propagation |

## Project Structure

```text
claude-architect-exercises/
├── shared/              # Shared client, types, and console utilities
├── ex1_agent/           # Exercise 1: agentic loop with tool use
├── ex2_claude_code/     # Exercise 2: Claude Code configuration files
├── ex3_extraction/      # Exercise 3: structured data extraction
├── ex4_research/        # Exercise 4: multi-agent research pipeline
├── tests/               # pytest test suite (49 tests)
├── docs/                # Tutorials and exam study guides
├── pyproject.toml       # uv project config
└── .env.example         # API key template
```

## Documentation

### Tutorials

Step-by-step walkthroughs explaining the *why* behind each pattern, not just the *what*.

- [English Tutorial](docs/tutorial-en.md) — Complete walkthrough of all exercises and patterns
- [繁體中文教學](docs/tutorial-zh.md) — 完整的實作教學與 Claude API 模式解析

### Exam Study Guides

Structured study companions for the certification exam. Covers all 5 exam domains, 6 scenarios, 12 sample questions with analysis, and a preparation checklist.

- [English Exam Guide](docs/exam-guide-en.md) — Exam structure, domain deep-dives, sample Q&A
- [考試導讀指南](docs/exam-guide-zh.md) — 考試結構、領域深度解析、範例題目解析

## Tests

```bash
uv run pytest              # Run all 49 tests
uv run pytest tests/ -v    # Verbose output
```

## License

MIT

---

# 繁體中文

[English](#claude-certified-architect--foundations-exercises) | 繁體中文

[Claude Certified Architect — Foundations](https://anthropic.skilljar.com/claude-certified-architect-foundations-access-request) 認證考試的 4 個準備練習題完整實作，涵蓋核心 Claude API 模式：代理迴圈、Claude Code 設定、結構化擷取、多代理編排。

## 快速開始

```bash
# 1. 安裝依賴
uv sync

# 2. 設定環境
cp .env.example .env
# 在 .env 中填入你的 ANTHROPIC_API_KEY

# 3. 驗證安裝
uv run pytest          # 應顯示 49 passed
```

**環境需求：** Python 3.11+、[uv](https://docs.astral.sh/uv/)、[Anthropic API 金鑰](https://console.anthropic.com)

## 練習題

| #   | 練習                | 執行指令                                       | 核心模式                                       |
| --- | ------------------- | ---------------------------------------------- | ---------------------------------------------- |
| 1   | 多工具代理          | `uv run python -m ex1_agent.main`              | 代理迴圈、程式化 gates、pre/post hooks          |
| 2   | Claude Code 設定    | `uv run python ex2_claude_code/validate.py`    | CLAUDE.md、rules、commands、skills、MCP        |
| 3   | 結構化資料擷取      | `uv run python -m ex3_extraction.main`         | 強制 tool_use、語意驗證、Batch API              |
| 4   | 多代理研究流水線    | `uv run python -m ex4_research.main`           | 協調器-子代理、asyncio.gather、錯誤傳播         |

## 目錄結構

```text
claude-architect-exercises/
├── shared/              # 共用工具：型別、客戶端、顯示輔助
├── ex1_agent/           # 練習一：多工具代理與升級機制
├── ex2_claude_code/     # 練習二：Claude Code 設定檔
├── ex3_extraction/      # 練習三：結構化資料擷取
├── ex4_research/        # 練習四：多代理研究流水線
├── tests/               # pytest 測試套件（49 個測試）
├── docs/                # 教學文件與考試導讀
├── pyproject.toml       # uv 專案設定
└── .env.example         # API 金鑰範本
```

## 文件資源

### 實作教學

逐步教學，說明每個模式背後的「為什麼」，而不僅僅是「怎麼做」。

- [English Tutorial](docs/tutorial-en.md) — Complete walkthrough of all exercises and patterns
- [繁體中文教學](docs/tutorial-zh.md) — 完整的實作教學與 Claude API 模式解析

### 考試導讀

認證考試的結構化學習伴侶，涵蓋五大考試領域、六大情境、12 道範例題目解析與備考清單。

- [English Exam Guide](docs/exam-guide-en.md) — Exam structure, domain deep-dives, sample Q&A
- [考試導讀指南](docs/exam-guide-zh.md) — 考試結構、領域深度解析、範例題目解析

## 測試

```bash
uv run pytest              # 執行全部 49 個測試
uv run pytest tests/ -v    # 詳細輸出
```

## 授權

MIT
