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
from pydantic import BaseModel, field_validator
import json  # 由 make_tool_result 使用，序列化回傳值

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

> **📝 考試重點（client.py）**
> `get_client()` 是延遲初始化的 singleton：第一次呼叫時建立 `Anthropic` 物件並快取，後續呼叫直接回傳快取值。測試中可用 `unittest.mock.patch` 替換 `_client` 來注入假物件，避免真實 API 呼叫。

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

- `print_message()` — 青色（cyan）（assistant）或綠色（user/system）面板，顯示對話訊息
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

---

## 第二章：練習一——多工具代理人與升級機制（`ex1_agent/`）

這個練習示範了代理人架構的四個核心模式：**tool_use 循環**、**stop_reason 控制流**、**程式碼閘門（programmatic gates）**、以及**前置/後置鉤子（pre/post hooks）**。情境是一個客戶支援代理人，能夠查詢客戶資料、查單、處理退款，以及在需要時將案件升級給真人客服。

---

### 2a. 工具定義（`tools.py`）

#### 豐富的工具描述是可靠工具選擇的基礎

Claude 選擇要呼叫哪個工具，靠的是讀取 `TOOL_DEFINITIONS` 裡的 `description` 欄位——這不是給工程師看的文件，而是**模型的決策依據**。描述寫得模糊，模型就可能在錯誤的時機呼叫錯誤的工具；描述寫得精確，模型才能按照預期的順序執行工具鏈。

以 `get_customer` 的描述為例，它明確指出「**ALWAYS call this first**」，以及「customer_id is required for all subsequent operations」。這樣的描述等同於把呼叫順序的契約直接嵌進工具本身，而不是依賴系統提示詞的字數運氣。

#### 四個工具形成一條呼叫鏈

```python
# tools.py — TOOL_DEFINITIONS 結構（節錄 get_customer）
TOOL_DEFINITIONS = [
    {
        "name": "get_customer",
        "description": (
            "Look up a customer record by their email address and return their verified customer_id. "
            "ALWAYS call this first before lookup_order or process_refund — customer_id is required "
            "for all subsequent operations. ..."
        ),  # 豐富描述讓模型知道何時該用此工具
        "input_schema": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "Customer's email address"}
            },
            "required": ["email"],
        },
    },
    # lookup_order、process_refund、escalate_to_human 結構相同，省略
]
```

四個工具的職責鏈：`get_customer`（驗證身份）→ `lookup_order`（查詢訂單）→ `process_refund`（執行退款，限 ≤$500）→ `escalate_to_human`（升級給真人，用於大額或例外情境）。

#### 結構化錯誤回傳 vs. 拋出例外

工具函式遇到錯誤時，**回傳 `ToolError` dict** 而不是 `raise Exception`：

```python
def get_customer(email: str) -> dict:
    customer = _CUSTOMERS.get(email)
    if not customer:
        return ToolError(                    # 回傳，不是拋出
            errorCategory="validation",
            isRetryable=False,
            message=f"No customer found with email '{email}'"
        ).model_dump()                       # 轉成普通 dict 傳給模型
    return customer
```

為什麼回傳比拋出好？因為例外會在 Python 執行層被捕捉，**模型永遠看不到發生了什麼事**。回傳結構化錯誤 dict 才能讓模型讀到 `errorCategory` 和 `isRetryable`，進而自主決定是否重試或改變策略——這是代理人能夠「自我修正」的基礎。

---

### 2b. 鉤子（`hooks.py`）

#### 為何鉤子能提供提示詞無法保證的確定性

系統提示詞告訴模型「退款超過 $500 請升級給真人」，但這是**建議**，不是**強制**。語言模型有一定的隨機性，在邊緣案例或複雜對話脈絡下，模型偶爾可能忽略這條指令。

鉤子是純 Python 程式碼，只要條件成立，攔截就**一定發生**，不依賴模型的注意力。這就是「確定性保證（deterministic guarantee）」的意義：業務規則在程式碼層執行，而不在提示詞層祈禱。

#### 前置鉤子：HookInterception 例外模式

```python
# hooks.py — run_pre_tool_hook（完整函式）
def run_pre_tool_hook(tool_name: str, tool_inputs: dict) -> None:
    """
    Enforce business rules before tool execution.
    Raises HookInterception to redirect the call to a different tool.
    """
    if tool_name == "process_refund":
        amount = tool_inputs.get("amount", 0)
        if amount > REFUND_THRESHOLD:           # $500 門檻閘門
            raise HookInterception(             # 拋出例外，而非回傳
                redirect_to="escalate_to_human",
                redirect_inputs={
                    "customer_id": tool_inputs["customer_id"],
                    "order_id":    tool_inputs["order_id"],
                    "reason": f"Refund amount ${amount:.2f} exceeds ${REFUND_THRESHOLD:.2f} threshold",
                    "escalation_type": "REFUND_THRESHOLD",
                },
                reason=f"Refund ${amount} > threshold ${REFUND_THRESHOLD}",
            )
```

`HookInterception` 是個特殊例外：它不代表「出錯了」，而是「**請改用這個工具、這些參數**」。呼叫端（`agent.py`）捕捉它後，會把 `tool_name` 和 `tool_inputs` 替換成 `e.redirect_to` 和 `e.redirect_inputs`，接著繼續執行。

#### 後置鉤子：資料正規化

`run_post_tool_hook` 在工具執行後、模型看到結果前，做兩件事：

1. **Unix 時間戳 → ISO 8601**：`created_at: 1700000000` 對模型來說是不透明的數字；轉成 `2023-11-14T22:13:20+00:00` 才有語意。
2. **數字狀態碼 → 字串**：`status: 1` → `"delivered"`，模型才能理解訂單狀態。

---

### 2c. 代理人循環（`agent.py`）

#### `while True` / `stop_reason` 模式

代理人循環的核心邏輯非常簡單：不斷呼叫 API，直到模型說「我做完了」。

```python
# agent.py — AgentSession.run()（核心循環）
def run(self, messages: list) -> str:
    """Run the agentic loop until stop_reason is 'end_turn'. Returns final text."""
    while True:
        response = self._call_api(messages)      # 呼叫 Claude API

        if response.stop_reason == "end_turn":   # 模型認為任務完成
            text = next((b.text for b in response.content if b.type == "text"), "")
            return text                          # 回傳最終文字回覆，結束循環

        if response.stop_reason == "tool_use":   # 模型想呼叫工具
            # 把助理的回覆（含工具呼叫請求）加進對話歷史
            messages.append({"role": "assistant", "content": response.content})
            # 執行工具，取得結果列表
            tool_results = self._process_tool_calls(response.content)
            # 把工具結果以 "user" 角色附加回對話，讓模型繼續推理
            messages.append({"role": "user", "content": tool_results})
            continue                             # 回到 while True 頂端

        # stop_reason 為 max_tokens 或其他非預期值
        raise RuntimeError(f"Unexpected stop_reason: {response.stop_reason!r}")
```

三個 `stop_reason` 的含義：

| stop_reason | 含義 | 正確處理方式 |
|-------------|------|-------------|
| `tool_use` | 模型在回覆中包含一或多個工具呼叫 | 執行工具，將結果附加到歷史，繼續循環 |
| `end_turn` | 模型完成回覆，不需要再呼叫工具 | 取出文字，結束循環 |
| `max_tokens` | 回覆被截斷（達到 token 上限） | 視為錯誤，或實作截斷恢復邏輯 |

#### tool_result 訊息結構

工具結果以 `"user"` 角色回傳給模型，格式由 `make_tool_result()` 產生：

```python
{
    "type": "tool_result",
    "tool_use_id": "toolu_01XxxXXX",  # 對應 Claude 發出的工具呼叫 ID
    "content": "{\"customer_id\": \"C001\", ...}",  # JSON 字串
}
```

`tool_use_id` 是關鍵——模型靠它把「我剛才發出的工具請求」和「這個結果」配對，才能繼續正確推理。

#### 程式碼閘門（Programmatic Gates）

`_REQUIRES_CUSTOMER` 集合定義哪些工具必須在 `get_customer` 成功後才能執行：

```python
_REQUIRES_CUSTOMER = {"lookup_order", "process_refund"}  # 需要先驗證客戶

class AgentSession:
    def __init__(self):
        self.verified_customer_id: str | None = None  # 跨輪次追蹤驗證狀態

    def check_gate(self, tool_name: str, tool_inputs: dict) -> None:
        if tool_name in _REQUIRES_CUSTOMER and not self.verified_customer_id:
            raise ProgrammaticGateError(  # 擋住呼叫，回報錯誤給模型
                f"'{tool_name}' requires a verified customer_id from get_customer first."
                # ...（實際訊息含第二行提示）
            )
```

`AgentSession` 是一個**有狀態的物件**，`verified_customer_id` 跨越多輪對話持續存在。當 `get_customer` 成功，`_execute_tool` 會把 `customer_id` 存入 session；之後每次 `check_gate` 都會檢查這個值。這樣即使模型「忘記」先驗證客戶，程式碼層也會攔截並給出明確的錯誤訊息，引導模型回到正確路徑。

#### 完整執行流程

一次標準退款請求的完整流程：

1. 使用者送出訊息 → `messages = [{"role": "user", ...}]`
2. `_call_api()` → `stop_reason = "tool_use"`，模型請求呼叫 `get_customer`
3. `check_gate()` 通過，`run_pre_tool_hook()` 無攔截，執行 `get_customer()`
4. `run_post_tool_hook()` 正規化結果，session 儲存 `verified_customer_id`
5. `tool_result` 附加到 `messages`，進入下一輪
6. 模型請求 `process_refund` → `check_gate()` 通過（已有 `verified_customer_id`）
7. `run_pre_tool_hook()` 確認金額 ≤ $500，無攔截，執行退款
8. 退款結果附加到 `messages`，進入下一輪
9. `stop_reason = "end_turn"` → 模型給出最終回覆，循環結束

---

### 2d. 執行示範（`main.py`）

```bash
uv run python -m ex1_agent.main
```

程式會依序執行三個情境：

**情境一：標準退款（正常流程）**
使用者 `john@example.com` 請求 ORD-001 的 $49.99 退款。代理人依序呼叫 `get_customer` → `process_refund`，模型收到退款確認後以 `end_turn` 結束，輸出退款成功的回覆。

**情境二：大額退款（鉤子攔截）**
使用者請求 ORD-003 的 $599 退款。`get_customer` 成功後，模型嘗試呼叫 `process_refund(amount=599)`；`run_pre_tool_hook` 偵測到金額超過 $500，拋出 `HookInterception`，代理人自動改為呼叫 `escalate_to_human`，並帶上 `escalation_type="REFUND_THRESHOLD"`。終端機輸出可見「Hook intercepted → redirecting to escalate_to_human」訊息。

**情境三：閘門阻擋（缺少先決條件）**
使用者直接詢問「請查詢 ORD-001 的狀態」，沒有提供電子郵件。模型嘗試直接呼叫 `lookup_order`；`check_gate()` 發現 `verified_customer_id` 為 `None`，拋出 `ProgrammaticGateError`，錯誤訊息以 `tool_result` 的形式回傳給模型。模型接收到錯誤後，主動向使用者索取電子郵件地址。

---

> **📝 考試重點**
>
> **stop_reason 三個值的具體含義：**
> - `tool_use`：模型回覆中包含工具呼叫，必須執行完所有工具並附加結果後繼續循環
> - `end_turn`：模型自然結束回覆，任務完成，取出文字並結束循環
> - `max_tokens`：輸出被截斷，屬於非預期情況，應作錯誤處理
>
> **tool_result 訊息的必填欄位：**
> `type`（固定為 `"tool_result"`）、`tool_use_id`（對應工具請求的 ID）、`content`（字串格式的結果）。錯誤情況需額外加上 `is_error: true`。
>
> **閘門 vs. 鉤子的差別：**
> - **閘門（gate）**：在執行前檢查「先決條件是否滿足」，不滿足則直接拒絕，把錯誤訊息回傳給模型，引導模型補齊缺少的步驟
> - **鉤子（hook）**：在執行前/後「修改行為或資料」——前置鉤子可重導向（redirect）呼叫，後置鉤子可轉換（transform）結果；兩者都提供程式碼層的確定性保證，不依賴模型的注意力

---

## 第三章：練習二——Claude Code 設定（ex2_claude_code/）

**核心模式：Claude Code 專案設定層次結構**

Claude Code 不只是一個對話介面——它是一套可以透過多層設定檔深度客製化的開發工具。本章帶你逐一認識這五種設定類型，以及它們各自解決什麼問題。

---

### 3a. CLAUDE.md——專案層級指令

`CLAUDE.md` 是最基礎的設定層。每次開啟新的 Claude Code session，它都會自動載入，讓 Claude 理解這個專案的基本規範。

**重點：** 這份檔案不需要路徑範圍（path scoping），規則對整個專案一律套用。

以下是 `ex2_claude_code/CLAUDE.md` 的內容：

```markdown
# Project Standards

## Code Quality
- All functions must have type hints           # 所有函式必須有型別標注
- No bare `except:` — always catch specific exception types
- Use `pathlib.Path` instead of `os.path` for file operations
- Prefer f-strings over `.format()` or `%`

## Testing
- Write tests before implementation (TDD)
- Every public function needs at least one test

## Git
- Commits in imperative mood: "Add feature" not "Added feature"
```

這些規則涵蓋程式碼品質、測試習慣、版本控制三個面向，是任何檔案都必須遵守的全域標準。

---

### 3b. .claude/rules/*.md——路徑範圍規則

規則檔案解決了「不同目錄需要不同規範」的問題。透過 YAML frontmatter 的 `paths:` 欄位，Claude 只在符合的路徑下套用規則，避免把 React 前端規範錯誤套用到後端 API 程式碼上。

**與 CLAUDE.md 的差異：** CLAUDE.md 全域生效；規則只在 `paths:` 命中的檔案時才啟動。

以下是 `react.md` 的 frontmatter：

```yaml
---
paths:
  - "src/components/**/*"   # 套用到所有元件
  - "src/pages/**/*"        # 套用到所有頁面
---
```

本練習共有三個規則檔：

| 檔案 | 適用路徑 | 用途 |
|------|----------|------|
| `react.md` | `src/components/**/*`、`src/pages/**/*` | React 元件慣例（函式元件、hooks 命名） |
| `api.md` | `src/api/**/*`、`src/services/**/*` | API 處理器規範（async、Pydantic 驗證） |
| `testing.md` | `**/*.test.*`、`**/*.spec.*`、`**/tests/**` | 測試慣例（AAA 模式、命名規則） |

`testing.md` 的路徑模式特別值得注意：它用萬用字元匹配所有測試相關副檔名，無論測試放在哪個目錄都能觸發。

---

### 3c. .claude/commands/*.md——斜線指令

命令（commands）與規則最大的差異在於：**規則是被動觸發的，命令是使用者主動呼叫的。**

在 Claude Code 的對話框輸入 `/review` 或 `/extract-types`，就會執行對應的命令內容。這適合「需要的時候才執行」的任務，而不是每次修改檔案都自動套用的規範。

本練習有兩個命令：

- **`/review`**（`review.md`）：依據團隊檢查清單審查目前檔案，逐項確認型別標注、錯誤處理、測試覆蓋、命名規範與安全性，並回報問題位置與修正建議。

- **`/extract-types`**（`extract-types.md`）：將 Python Pydantic 模型或 dataclass 轉換成 TypeScript interface，處理型別對應（`str` → `string`、`list[T]` → `T[]`）並保留 docstring 為 JSDoc 註解。

命令本身就是一段提示詞，沒有額外 frontmatter。這讓設計命令的門檻很低——只要清楚描述你想要 Claude 做什麼就夠了。

---

### 3d. .claude/skills/*.md——可複用代理人提示詞

Skill 是比命令更進一步的封裝。它透過 frontmatter 控制代理人的執行環境，適合需要獨立脈絡或限定工具集的複雜任務。

本練習有兩個 skill：

以下是 `analyze-codebase.md` 的 frontmatter：

```yaml
---
context: fork                        # 啟動隔離的子代理人脈絡
allowed-tools:                       # 限制代理人只能使用唯讀工具
  - Read
  - Grep
  - Glob
argument-hint: "path to analyze (default: current directory)"
---
```

**`context: fork` 的意義：** 這個欄位告訴 Claude Code 在獨立的子代理人脈絡（isolated sub-agent context）中執行這個 skill，而不是在主對話的脈絡裡執行。子代理人結束後，它的中間步驟不會污染主對話的 context window——這是「agent-as-tool」模式的具體實現。

**`allowed-tools:` 的意義：** 透過明確限制工具集，可以保證分析 skill 不會意外修改任何檔案（只能 Read/Grep/Glob）；而 `generate-tests.md` 則只允許 `Write`，確保它只寫測試、不讀取其他程式碼。

| Skill | `context` | `allowed-tools` | 用途 |
|-------|-----------|-----------------|------|
| `analyze-codebase` | `fork` | Read, Grep, Glob | 分析程式碼庫結構，回傳摘要 |
| `generate-tests` | （未設定）| Write | 為指定函式或類別產生 pytest 測試 |

---

### 3e. .mcp.json——MCP 伺服器設定

MCP（Model Context Protocol）讓 Claude Code 可以連接外部工具伺服器，擴展原生能力之外的功能（如存取 GitHub、資料庫、第三方 API）。

以下是 `ex2_claude_code/.mcp.json` 的完整內容：

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

**`${ENV_VAR}` 展開的設計理由：** 機密資訊（如 API token）不應寫死在設定檔裡，因為設定檔通常會進版本控制。`${GITHUB_TOKEN}` 是佔位符，Claude Code 啟動時會自動從系統環境變數展開。這樣即使設定檔外洩，攻擊者也拿不到真實的 token。

---

### 3f. validate.py——設定驗證腳本

`validate.py` 提供了一個命令列工具，讓你在撰寫完設定後立即驗證結構是否完整。

**兩個核心函式：**

- **`validate_structure(base)`**：逐一確認 `REQUIRED_FILES` 列表中的九個設定檔是否存在。只要有任何一個檔案缺失，就回傳含有錯誤訊息的列表。

- **`validate_rule_frontmatter(rule_file)`**：用正規表達式解析規則檔的 YAML frontmatter，確認它以 `---` 開頭、有對應的結尾 `---`，且 frontmatter 中包含 `paths:` 欄位。

以下是 CLI 進入點（`validate.py` 第 47–61 行）：

```python
if __name__ == "__main__":
    base = Path(__file__).parent          # 以 validate.py 所在目錄為基準
    all_errors = validate_structure(base)
    rules_dir = base / ".claude" / "rules"
    for rule_file in rules_dir.glob("*.md"):   # 逐一驗證所有規則檔
        errs = validate_rule_frontmatter(rule_file)
        all_errors.extend([f"{rule_file.name}: {e}" for e in errs])

    if all_errors:
        print("VALIDATION FAILED:")
        for err in all_errors:
            print(f"  ✗ {err}")
        sys.exit(1)                        # 非零退出碼，方便 CI 捕捉
    else:
        print("✓ All Claude Code configuration files are valid")
```

執行方式：

```bash
uv run python ex2_claude_code/validate.py
```

若所有設定檔齊備且格式正確，會印出 `✓ All Claude Code configuration files are valid`；否則列出所有錯誤並以 `exit(1)` 結束，便於整合進 CI/CD 流程。

---

### 考試重點提示

> **五種設定類型的差異：**
>
> | 類型 | 檔案位置 | 觸發方式 | 適用場景 |
> |------|----------|----------|----------|
> | CLAUDE.md | 專案根目錄 | 每次 session 自動載入 | 全域程式碼規範 |
> | rules/*.md | `.claude/rules/` | 路徑符合時自動套用 | 特定目錄/檔案類型的規範 |
> | commands/*.md | `.claude/commands/` | 使用者輸入 `/指令名` | 按需執行的任務（審查、轉換） |
> | skills/*.md | `.claude/skills/` | 明確調用 skill | 需要隔離脈絡或限制工具的複雜任務 |
> | .mcp.json | 專案根目錄 | 啟動時自動載入 | 連接外部工具伺服器 |
>
> **MCP 機密處理：** 使用 `${ENV_VAR}` 佔位符，Claude Code 啟動時從系統環境變數展開，避免機密寫死進設定檔或版本控制。
>
> **規則 vs. 命令：** 規則是被動的——路徑匹配時自動生效，開發者無須主動觸發；命令是主動的——需要使用者輸入 `/指令名` 才執行。Skill 則是命令的進階形式，額外控制代理人的脈絡隔離（`context: fork`）與工具存取權限（`allowed-tools:`）。

---

## 第四章：練習三——結構化資料擷取（ex3_extraction/）

**核心模式：** 強制 tool_use、Pydantic 作為 schema、語意驗證、帶回饋的重試

這一章解決一個實際問題：如何讓 Claude 可靠地將非結構化文件（發票、合約、報告）轉換成固定形狀的 Python 物件，同時偵測資料本身的語意矛盾？

---

### 4a. schema.py — Pydantic 模型與 tool 定義

#### 為何用 tool_use 做結構化擷取，而不是在 prompt 中要求 JSON？

直接在 prompt 要求「請回傳 JSON」有幾個已知問題：

1. **格式不穩定**：Claude 可能在 JSON 前後夾雜說明文字（"Here is the JSON:"），下游 `json.loads()` 會炸掉。
2. **無法強制 schema**：你無法宣告哪些欄位是必填、哪些型別合法——模型自由發揮。
3. **缺乏型別保證**：即使回傳了 JSON，`quantity` 可能是字串 `"3"` 而非數字 `3`。

`tool_use` 解決以上三點：你把 schema 以 JSON Schema 形式傳給 API，模型的回傳值保證符合該 schema，Pydantic 再負責最後一哩的型別驗證。

#### LineItem 與 DocumentExtraction 模型

```python
class LineItem(BaseModel):
    description: str        # 必填：品項描述
    quantity: float         # 必填：數量
    unit_price: float       # 必填：單價
    total: float            # 必填：小計

class DocumentExtraction(BaseModel):
    document_type: Literal["invoice", "contract", "report", "other"]
    other_detail: str | None = None      # 僅當 document_type == "other" 時使用

    vendor_name: str                     # 必填：發行方名稱
    total_amount: float | None = None    # 可空：文件可能未列出總金額
    line_items: list[LineItem] = []
    issue_date: str | None = None        # 可空：日期可能缺失

    stated_total: float | None = None    # 文件上寫的總金額
    calculated_total: float | None = None  # 明細加總值
    conflict_detected: bool = False      # 語意自我檢查旗標
```

#### 可空欄位（`float | None = None`）vs 必填欄位

這是設計決策，不是便利寫法。規則是：

- **必填**（無 `None`）：該資訊在所有目標文件中都一定存在——例如 `vendor_name`。若模型找不到就應該視為擷取失敗，而非留空。
- **可空**（`| None = None`）：資訊**合理地**可能缺席，且缺席本身是有效狀態——例如 `issue_date`（有些內部文件就是沒有日期）。

把所有欄位都設成可空看似「安全」，但會讓驗證邏輯失去意義，且難以發現真正的擷取失敗。

#### `conflict_detected` 旗標——語意完整性自我檢查

這個布林欄位展示了一個重要模式：**讓模型在擷取時順帶做語意推理**，而不是等到事後驗證才發現問題。

在 tool description 中明確告訴模型：

> "Set `conflict_detected=true` if `stated_total` does not match the sum of `line_items`."

這樣模型在填寫欄位時就會計算並比對，而不是機械複製數字。`validator.py` 再做一次程式層面的確認，形成雙重保險。

#### `get_extraction_tool()` — Pydantic 如何映射到 JSON Schema

`get_extraction_tool()` 手動維護一份與 Pydantic 模型對應的 JSON Schema dict。兩個關鍵點：

- 可空欄位映射為 `"type": ["number", "null"]`，與 Pydantic 的 `float | None` 語意一致。
- `required` 陣列只包含 `["document_type", "vendor_name", "conflict_detected"]`——其餘欄位不強制。

這個手動維護的 schema 讓你對 API 合約有完整控制，不依賴 `.model_json_schema()` 的自動產出（後者的格式有時需要額外轉換）。

---

### 4b. extractor.py — 強制 tool_use

#### 核心擷取邏輯

```python
def extract_document(document_text: str) -> dict:
    client = get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        tools=[get_extraction_tool()],
        tool_choice={"type": "tool", "name": "extract_document"},  # 強制指定
        messages=[{"role": "user", "content": f"Extract data from this document:\n\n{document_text}"}],
    )
    # 從回應中找 tool_use block
    for block in response.content:
        if block.type == "tool_use" and block.name == "extract_document":
            return block.input
    raise RuntimeError("No tool_use block in response — unexpected API behavior")
```

#### `tool_choice={"type": "tool", "name": "extract_document"}` — 強制選擇

`tool_choice` 有三種模式（考試常考）：

| 模式 | 行為 |
|------|------|
| `{"type": "auto"}` | 模型自行判斷是否呼叫 tool（預設） |
| `{"type": "any"}` | 模型必須呼叫至少一個 tool，但自選哪個 |
| `{"type": "tool", "name": "..."}` | 模型必須呼叫指定名稱的 tool |

這裡使用第三種——**強制選擇**。這保證回應一定包含 `extract_document` 的 `tool_use` block，讓下游解析完全可預期，不需要處理「模型選擇直接回答文字」的情況。

#### RuntimeError 防護

即使設定了強制 `tool_choice`，防禦性程式設計仍然重要：

```python
raise RuntimeError("No tool_use block in response — unexpected API behavior")
```

這行程式碼永遠不應該被觸發，但若 API 行為異常（例如模型版本切換、quota 限流導致部分回應），它能給出明確的失敗訊息，而不是在後續步驟發生神秘的 `AttributeError`。

---

### 4c. validator.py — 語意驗證與帶回饋的重試

#### `SemanticValidationError`：為何用自訂例外

```python
class SemanticValidationError(Exception):
    """Raised when extracted data has semantic inconsistencies."""
```

使用自訂例外而非內建的 `ValueError`，原因有二：

1. **可被精確捕捉**：呼叫端可以 `except SemanticValidationError as e` 只處理語意問題，其他例外繼續往上傳播。
2. **訊息即回饋**：例外訊息被設計成可以直接塞進下一個 prompt——這是 `retry_with_feedback()` 的關鍵依賴。

#### `validate_extraction()` — 0.01 容差的浮點數比較

```python
if (
    doc.stated_total is not None
    and doc.calculated_total is not None
    and not doc.conflict_detected
    and abs(doc.stated_total - doc.calculated_total) > 0.01
):
    raise SemanticValidationError(...)
```

幾個設計細節值得注意：

- **先確認非 None**：可空欄位在比較前必須做 None 守衛，否則 `abs(None - 3.0)` 在執行期炸掉。
- **0.01 容差**：浮點數運算不精確（`0.1 + 0.2 ≠ 0.3`），容差避免誤報假警報。
- **跳過已標記衝突**：若模型自己已設 `conflict_detected=True`，代表它已知悉差異，不需再次報錯。

#### `retry_with_feedback()` — 將錯誤注入下一個 prompt

```python
def retry_with_feedback(
    document_text: str,
    failed_extraction: dict,
    validation_error: str,
    max_retries: int = 3,
) -> dict | None:
    client = get_client()
    for attempt in range(max_retries):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            tools=[get_extraction_tool()],
            tool_choice={"type": "tool", "name": "extract_document"},
            messages=[{
                "role": "user",
                "content": (
                    f"The previous extraction had a validation error. Please fix it.\n\n"
                    f"ORIGINAL DOCUMENT:\n{document_text}\n\n"
                    f"FAILED EXTRACTION:\n{json.dumps(failed_extraction, indent=2)}\n\n"
                    f"VALIDATION ERROR:\n{validation_error}\n\n"  # 具體錯誤注入
                    f"Please re-extract with the error corrected."
                )
            }],
        )
        for block in response.content:
            if block.type == "tool_use":
                return block.input
    return None  # 重試耗盡，回傳 None 讓呼叫端決定後續
```

#### 為何帶回饋的重試比泛用「請修正」更有效

比較兩種重試策略：

- **泛用重試**：`"Please try again."` — 模型不知道哪裡錯了，大概率重複相同錯誤。
- **帶回饋重試**：把失敗的擷取結果 + 具體錯誤訊息一起傳入 — 模型有完整脈絡，知道要調整 `stated_total` 與 `calculated_total` 的差異。

這是 LLM 應用中的通用原則：**錯誤訊息本身是最好的 prompt 工程素材**。`SemanticValidationError` 的訊息設計成人類可讀且機器可用，正是為了服務這個重試迴圈。

---

### 4d. batch.py — 批次 API

#### 何時使用批次 API

批次 API 適合以下特性同時成立的工作負載：

| 條件 | 說明 |
|------|------|
| **大量文件** | 幾十到幾千份，逐一同步處理效率太低 |
| **可接受延遲** | 不需要即時結果，最長 24 小時都 OK |
| **成本敏感** | 批次 API 比同步 API **便宜 50%** |

**何時不該用批次：** 任何需要立即回應的流程——例如 pre-merge CI 檢查、使用者互動介面、或下一步驟依賴本步驟結果的管線。

#### `custom_id` 關聯模式

批次 API 不保證回應順序，因此每個請求必須附上 `custom_id`：

```python
def build_batch_request(custom_id: str, document_text: str) -> dict:
    return {
        "custom_id": custom_id,   # 自訂識別碼，用於結果對應
        "params": { ... }
    }
```

慣例是用原始檔案名稱或資料庫 ID 作為 `custom_id`，這樣在批次完成後能直接對應回原始資料。

#### `submit_batch()` → `poll_batch()` → `handle_failures()` 流程

```python
# 1. 提交
batch_id = submit_batch({"doc-001": text1, "doc-002": text2})

# 2. 輪詢直到完成
results = poll_batch(batch_id)

# 3. 處理失敗項目
retry_docs = handle_failures(results, original_docs)
if retry_docs:
    retry_batch_id = submit_batch(retry_docs)  # 只重送失敗的
```

#### `poll_batch()` 的判斷邏輯

```python
def poll_batch(batch_id: str, poll_interval: int = 60) -> dict:
    client = get_client()
    while True:
        batch = client.messages.batches.retrieve(batch_id)
        if batch.processing_status == "ended":   # 唯一結束狀態
            break
        time.sleep(poll_interval)                # 預設 60 秒輪詢一次

    results = {}
    for result in client.messages.batches.results(batch_id):
        if result.result.type == "succeeded":    # 成功才取 tool_use block
            for block in result.result.message.content:
                if block.type == "tool_use":
                    results[result.custom_id] = {"status": "success", "data": block.input}
        else:
            results[result.custom_id] = {
                "status": "failed",
                "error": str(result.result),     # 保留原始錯誤供 handle_failures 使用
            }
    return results
```

`result.result.type == "succeeded"` 是關鍵判斷點——批次中每個請求都有自己的成功/失敗狀態，整批「ended」只代表處理完成，不保證全部成功。

`handle_failures()` 的設計讓失敗處理與成功處理完全解耦：它只回傳需要重試的 `{custom_id: text}` dict，呼叫端可選擇立即重送或記錄後人工審查。

---

### 執行練習三

```bash
uv run python -m ex3_extraction.main
```

你會看到同步擷取、語意驗證、重試回饋，以及批次提交的完整流程輸出。

---

### 考試重點提示

> **`tool_choice` 的三個選項：**
>
> | 設定 | 效果 |
> |------|------|
> | `{"type": "auto"}` | 模型自由決定是否使用 tool（預設行為） |
> | `{"type": "any"}` | 強制呼叫 tool，但模型自選哪個 |
> | `{"type": "tool", "name": "xxx"}` | 強制呼叫指定名稱的 tool，保證結構化輸出 |
>
> **批次 API 的取捨：**
>
> - 優勢：50% 成本節省、適合大量文件的離線處理
> - 限制：最長 24 小時處理視窗、無延遲 SLA 保證、不適合阻塞式或即時工作流
> - 失敗處理原則：批次「ended」≠ 全部成功，必須逐一檢查 `result.result.type`，對失敗項目用 `custom_id` 追蹤並選擇性重送
>
> **重試回饋 prompt 的模式：**
>
> 有效的重試 prompt 必須包含三要素：(1) 原始輸入文件、(2) 失敗的擷取結果、(3) 具體的錯誤訊息。缺少任何一項都會讓模型在沒有足夠脈絡的情況下重複相同錯誤。`SemanticValidationError` 的訊息文字應設計為「人類可讀且可直接注入 prompt」的格式。
