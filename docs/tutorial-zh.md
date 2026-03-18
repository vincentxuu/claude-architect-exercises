# Claude Certified Architect 練習題教學

本教學帶你逐步走過 **claude-architect-exercises** 單一程式庫（monorepo）中的四個練習題——從安裝環境到執行互動示範，完整理解每個 Claude API 模式。

**對象：** 有基礎 Python 經驗，但不需要事先了解 Claude API。
**語言：** 繁體中文
**英文版：** [docs/tutorial-en.md](tutorial-en.md)

---

## 第 0 章：環境準備

### 需要的工具

在開始之前，確認你的環境具備以下條件：

| 工具 | 最低版本 | 說明 |
|------|----------|------|
| Python | 3.11+ | 練習題使用 `match` 語句與新式型別標注 |
| Git | 任何近代版本 | 用於 clone 本 repo |
| `ANTHROPIC_API_KEY` | — | 從 [console.anthropic.com](https://console.anthropic.com) 取得 |

本專案使用 **uv** 作為套件與虛擬環境管理器。uv 比 pip + venv 快上數倍，也不需要手動切換環境。

```bash
# 安裝 uv（macOS / Linux）
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 安裝步驟

```bash
# 1. Clone 專案
git clone <repo-url> claude-architect-exercises
cd claude-architect-exercises

# 2. 安裝所有依賴（含開發工具）
uv sync

# 3. 設定 API 金鑰
cp .env.example .env
# 編輯 .env，填入你的 ANTHROPIC_API_KEY
```

`.env` 檔案只需要一行：

```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxx
```

### 驗證安裝

```bash
uv run pytest
```

所有測試通過時，你應該看到：

```
49 passed in X.XXs
```

49 個測試全綠代表環境設定正確，可以開始練習。

### 目錄結構

```
claude-architect-exercises/
├── shared/              # 共用工具：型別、客戶端、顯示輔助
├── ex1_agent/           # 練習一：多工具代理人與升級機制
├── ex2_claude_code/     # 練習二：Claude Code 設定
├── ex3_extraction/      # 練習三：結構化資料擷取
├── ex4_research/        # 練習四：多代理人研究流水線
├── tests/               # 49 個 pytest 測試
├── docs/                # 本教學文件
├── pyproject.toml       # uv 專案設定（依賴、Python 版本）
└── .env.example         # API 金鑰範本
```

每個 `ex*` 目錄都是獨立的練習題，彼此不互相依賴，但都共用 `shared/` 目錄下的基礎設施。

> **📝 考試重點**
>
> 本 monorepo 採用 **uv** 而非傳統 pip。`uv sync` 會根據 `pyproject.toml` 和 `uv.lock` 建立完全可重現的環境。考試中若看到關於依賴管理的題目，記住 `uv.lock` 鎖定了所有傳遞依賴的精確版本，確保跨機器的一致性。

---

## 第 1 章：共用基礎設施（`shared/`）

`shared/` 目錄包含三個模組，為四個練習題提供統一的基礎。與其在每個練習題中各自重造輪子，這些共用元件讓我們能把注意力集中在「每個練習的核心問題」上。

---

### 1a. `shared/types.py`：結構化錯誤處理

#### 設計動機

當 Claude 呼叫一個工具時，工具可能因為各種原因失敗——網路超時、輸入格式錯誤、權限不足、或是業務邏輯規則被違反。

最直覺的做法是直接 `raise Exception`，但這在 Claude API 的工具呼叫流程中行不通：**例外會在 Python 層被捕捉，模型根本看不到錯誤發生了**。正確做法是把錯誤「包裝成工具結果回傳給模型」，讓模型自行決定如何應對。

`ToolError` dataclass 為這個錯誤回傳加上結構，讓模型能夠依據錯誤類型做出不同的決策。

#### 程式碼

```python
from typing import Any, Literal
from pydantic import BaseModel
import json

class ToolError(BaseModel):
    errorCategory: Literal["transient", "validation", "permission", "business"]
    # 四種類別決定模型的後續行為策略
    isRetryable: bool          # 模型是否應自動重試
    message: str               # 人類可讀的錯誤描述


def make_tool_result(
    tool_use_id: str,          # 對應 Claude 發出的工具呼叫 ID
    content: Any,              # 成功時的回傳內容（dict 自動轉 JSON）
    is_error: bool = False,
    error_msg: str = "",       # 失敗時的錯誤訊息字串
) -> dict:
    if is_error:
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "is_error": True,
            "content": error_msg,          # API 邊界只接受字串
        }
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": json.dumps(content) if not isinstance(content, str) else content,
    }
```

#### 四種錯誤類別的語意

| 類別 | 語意 | 模型通常的反應 |
|------|------|----------------|
| `transient` | 暫時性故障（如網路超時） | 稍後重試 |
| `validation` | 輸入格式或值域錯誤 | 修正參數後重試 |
| `permission` | 呼叫者沒有執行此操作的權限 | 不重試，回報給使用者 |
| `business` | 業務邏輯規則被違反（如餘額不足） | 不重試，提供替代方案 |

注意 `ToolError` 與 `make_tool_result` 的職責分工：`ToolError` 用於應用程式內部的錯誤建模；`make_tool_result` 負責 API 邊界的序列化，最終傳給 Claude 的只是一個字串。

---

### 1b. `shared/client.py`：Anthropic 客戶端單例

#### 設計動機

`Anthropic()` 在初始化時會建立 HTTP 連線池，如果在每次 API 呼叫前都建立新的客戶端實例，不僅浪費資源，在高頻呼叫時還可能耗盡系統的 socket 限制。**Singleton 模式**確保整個程式生命週期只建立一個連線池，並在第一次使用時才惰性初始化（lazy initialization）。

#### 程式碼

```python
import os
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()                  # 從 .env 檔案載入環境變數

_client: Anthropic | None = None  # 模組層級的單例持有者

MODEL = "claude-sonnet-4-6"    # 整個 monorepo 使用同一個模型常數


def get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY not set")  # 明確的錯誤提示
        _client = Anthropic(api_key=api_key)
    return _client             # 第二次呼叫直接回傳已存在的實例
```

幾個值得注意的設計細節：

- `load_dotenv()` 在模組載入時就執行，確保任何 `os.getenv()` 呼叫前環境變數已就緒。
- `EnvironmentError` 比靜默的 `None` 更好——它在最早的時機點就告訴開發者「你忘了設定金鑰」。
- `MODEL` 常數集中管理模型名稱，日後升級版本只需改一行。

---

### 1c. `shared/utils.py`：Rich 終端機顯示輔助

#### 設計動機

在開發和除錯代理人程式時，能夠在終端機看到清晰格式化的訊息非常重要——你需要一眼分辨「這是 Claude 的回覆」還是「這是工具呼叫的輸入」。`shared/utils.py` 使用 **Rich** 函式庫，為所有練習題提供一致的視覺風格。

#### 程式碼

```python
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
import json

console = Console()            # 模組層級的 Rich console 實例


def print_message(role: str, content: str) -> None:
    color = "cyan" if role == "assistant" else "green"  # 角色以顏色區分
    console.print(Panel(content, title=f"[bold {color}]{role}[/]", border_style=color))


def print_tool_call(tool_name: str, inputs: dict) -> None:
    console.print(
        Panel(
            Syntax(json.dumps(inputs, indent=2), "json"),  # JSON 語法高亮
            title=f"[bold yellow]Tool Call: {tool_name}[/]",
            border_style="yellow",
        )
    )


def print_error(msg: str) -> None:
    console.print(f"[bold red]ERROR:[/] {msg}")   # 紅色醒目標示
```

三個函式的視覺對應：

- `print_message()` — 藍色（assistant）或綠色（user/system）面板，顯示對話訊息
- `print_tool_call()` — 黃色面板＋JSON 語法高亮，清楚呈現工具被呼叫時的輸入參數
- `print_error()` — 紅色粗體前綴，讓錯誤在大量輸出中立即顯眼

這三個函式沒有回傳值，純粹為了「副作用」（side effect）而存在：讓開發者在練習過程中能夠追蹤代理人的每一步決策。

---

> **📝 考試重點**
>
> **ToolError 四種類別必須記熟**，考試常考「給定錯誤情境，應歸類為哪種 errorCategory」。速記口訣：
>
> - **transient**（暫時）→ 等一下再試可能就好了
> - **validation**（驗證）→ 你送來的資料格式有問題
> - **permission**（權限）→ 你沒有做這件事的資格
> - **business**（業務）→ 規則不允許，換個方法
>
> 另外記住：`isRetryable: bool` 欄位讓模型**程式化地**決定重試策略，不需要在 prompt 中用自然語言描述錯誤處理邏輯。這是結構化輸出優於純文字錯誤訊息的核心理由。

---

接下來的第 2 章將進入第一個練習題 `ex1_agent/`，看這些共用元件如何被組裝成一個有升級機制的多工具代理人。
