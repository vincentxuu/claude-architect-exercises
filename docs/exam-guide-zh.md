# Claude Certified Architect – Foundations：考試導讀指南

> 本導讀指南是 Claude Certified Architect – Foundations 認證考試的結構化學習伴侶。搭配[實作教學](tutorial-zh.md)與官方考試指南 PDF 使用，可獲得完整的備考體驗。

**英文版：** [docs/exam-guide-en.md](exam-guide-en.md)

---

## 考試概覽

### 考試目標
- 驗證實務工作者在使用 Claude 建構生產環境方案時，能否做出合理的架構取捨判斷
- 涵蓋四大核心技術：Claude Code、Claude Agent SDK、Claude API、Model Context Protocol (MCP)
- 題目來自實際客戶使用場景，強調實作判斷而非純理論

### 考試格式與計分
- 全部為單選題（1 個正確答案 + 3 個干擾選項）
- 猜題不扣分——務必作答每一題
- 分數範圍：100–1,000（量尺分數）；及格分數：720
- 結果為通過/未通過

### 目標考生
- 使用 Claude 設計與實作生產環境應用的**方案架構師**
- 具備 6 個月以上的 Claude APIs、Agent SDK、Claude Code、MCP 實務經驗
- 實作經驗涵蓋：代理式應用、CLAUDE.md 設定、MCP 工具/資源設計、結構化輸出工程、上下文視窗管理、CI/CD 整合、升級與可靠性決策

---

## 五大考試領域總覽

| 領域 | 佔比 | 核心重點 | 對應教學章節 |
|------|------|---------|-----------|
| 1. 代理架構與編排 (Agentic Architecture & Orchestration) | 27% | 代理迴圈、多代理協調、hooks、gates、session 管理 | 第一～二章、第五章 |
| 2. 工具設計與 MCP 整合 (Tool Design & MCP Integration) | 18% | 工具描述、結構化錯誤、工具分配、MCP 設定、內建工具 | 第一～二章、第三章 |
| 3. Claude Code 設定與工作流程 (Claude Code Configuration & Workflows) | 20% | CLAUDE.md、rules、commands、skills、MCP、plan mode、CI/CD | 第三章 |
| 4. 提示工程與結構化輸出 (Prompt Engineering & Structured Output) | 20% | 明確標準、few-shot、tool_use schema、驗證/重試、Batch API、多遍審查 | 第四章 |
| 5. 上下文管理與可靠性 (Context Management & Reliability) | 15% | 上下文保存、升級機制、錯誤傳播、大型程式碼探索、人工審查、資訊溯源 | 第五章 |

---

## 考試情境

考試隨機從 6 個情境中抽取 4 個。每個情境設定一個真實的生產環境場景，圍繞該場景出一系列題目。

### 情境 1：客服支援解決代理 (Customer Support Resolution Agent)
- 使用 Claude Agent SDK 建構客服代理
- MCP 工具：`get_customer`、`lookup_order`、`process_refund`、`escalate_to_human`
- 目標：80%+ 首次聯絡解決率，同時知道何時升級
- **涉及領域：** 1、2、5
- **教學對應：** 練習一 (ex1_agent) 直接實作此情境

### 情境 2：使用 Claude Code 生成程式碼 (Code Generation with Claude Code)
- Claude Code 用於程式碼生成、重構、除錯、文件撰寫
- 自訂斜線命令、CLAUDE.md 設定、plan mode vs 直接執行
- **涉及領域：** 3、5
- **教學對應：** 練習二 (ex2_claude_code) 涵蓋所有設定類型

### 情境 3：多代理研究系統 (Multi-Agent Research System)
- 協調器代理 → 網頁搜尋 + 文件分析子代理 → 綜合 → 報告
- Hub-and-spoke 架構，子代理並行執行
- **涉及領域：** 1、2、5
- **教學對應：** 練習四 (ex4_research) 實作此流水線

### 情境 4：使用 Claude 的開發者生產力工具 (Developer Productivity with Claude)
- Agent SDK 工具用於探索程式碼庫、理解遺留系統、產生樣板程式碼
- 內建工具 (Read, Write, Bash, Grep, Glob) + MCP 伺服器
- **涉及領域：** 2、3、1

### 情境 5：CI/CD 中的 Claude Code (Claude Code for Continuous Integration)
- Claude Code 整合到 CI/CD 流水線：自動化 code review、測試生成、PR 回饋
- 設計能提供可操作回饋並減少誤報的提示
- **涉及領域：** 3、4

### 情境 6：結構化資料擷取 (Structured Data Extraction)
- 使用 JSON schema 從非結構化文件擷取結構化資料
- 邊緣案例處理、下游系統整合
- **涉及領域：** 4、5
- **教學對應：** 練習三 (ex3_extraction) 直接實作此情境

---

## 領域 1：代理架構與編排（27%）

*佔比最高的領域，務必精通。*

### 1.1 代理迴圈設計
**核心概念：**
- 代理迴圈生命週期：發送請求 → 檢查 `stop_reason` → 分派工具呼叫 → 附加結果 → 重複
- `stop_reason` 值：`"tool_use"`（繼續迴圈）、`"end_turn"`（完成）、`"max_tokens"`（達到上限——要處理！）、`"stop_sequence"`
- 工具結果被附加到對話歷史中，讓模型能推理已發生的事
- **要避免的反模式：** 解析自然語言訊號來判定迴圈終止、將任意迭代上限作為主要停止機制、檢查助手文字內容作為完成指標

**教學參考：** `ex1_agent/agent.py` — `run()` 方法實作了標準的 `while True` / `stop_reason` 模式

### 1.2 多代理協調（協調器-子代理模式）
**核心概念：**
- Hub-and-spoke：協調器管理所有子代理間的通訊、錯誤處理、資訊路由
- 子代理有**隔離的上下文**——不會自動繼承協調器的對話歷史
- 協調器職責：任務分解、委派、結果彙總、決定呼叫哪些子代理
- **風險：** 過度狹窄的任務分解 → 覆蓋不完整（例：「創意產業」只分解為視覺藝術，遺漏了音樂/寫作/電影）

**教學參考：** `ex4_research/coordinator.py` — `gather_research()` 搭配 `asyncio.gather`

### 1.3 子代理呼叫與上下文傳遞
**核心概念：**
- `Task` 工具用於產生子代理；協調器的 `allowedTools` 必須包含 `"Task"`
- 子代理上下文必須在 prompt 中**明確提供**——無自動繼承
- `AgentDefinition` 設定：描述、系統提示、每種子代理的工具限制
- `fork_session` 用於從共享基準探索不同路徑
- 在單一回應中發送多個 `Task` 工具呼叫來並行啟動子代理

**教學參考：** `ex4_research/subagents.py` — 明確的參數傳遞，無共享狀態

### 1.4 強制執行與交接模式
**核心概念：**
- **程式化強制執行**（hooks、前提 gates）vs **提示引導**——需要確定性合規時用程式化（如：金融操作前的身份驗證）
- Pre-tool hooks：在執行前攔截並重定向（如：退款 > $500 → 升級）
- 程式化 gates：阻擋下游工具直到前提條件滿足（如：`process_refund` 被阻擋直到 `get_customer` 回傳已驗證的 ID）
- 升級時的結構化交接摘要：客戶 ID、根因、退款金額、建議動作

**教學參考：** `ex1_agent/hooks.py`（HookInterception、pre/post hooks）、`ex1_agent/agent.py`（ProgrammaticGateError）

### 1.5 Agent SDK Hooks
**核心概念：**
- `PostToolUse` hooks：在模型處理前攔截工具結果進行轉換（統一時間戳、狀態碼格式）
- Hook 模式可強制執行合規規則（阻擋違反政策的操作）
- Hooks 提供**確定性保證**；提示指令提供**機率性合規**
- 業務規則需要保證合規時，選擇 hooks

**教學參考：** `ex1_agent/hooks.py` — `run_post_tool_hook()` 將 Unix 時間戳轉換為 ISO 8601

### 1.6 任務分解策略
**核心概念：**
- 固定順序流水線（prompt chaining）vs 動態自適應分解
- Prompt chaining：逐檔分析 → 跨檔整合
- 自適應計畫：根據每步發現生成子任務
- 大型 code review 分拆為逐檔分析 + 跨檔整合，避免注意力稀釋

### 1.7 Session 管理
**核心概念：**
- `--resume <session-name>` 繼續命名的 session
- `fork_session` 建立平行探索分支
- 帶結構化摘要重新開始，通常比恢復帶有過時工具結果的 session 更可靠
- 恢復 session 時，告知代理特定檔案變更以進行針對性重新分析

---

## 領域 2：工具設計與 MCP 整合（18%）

### 2.1 工具介面設計
**核心概念：**
- 工具描述是 LLM 選擇工具的**主要機制**——描述不充分 → 選擇不可靠
- 在描述中包含：輸入格式、查詢範例、邊緣案例、邊界說明
- 模糊/重疊的描述導致路由錯誤（如：`analyze_content` vs `analyze_document` 描述幾乎相同）
- 系統提示中的關鍵字敏感指令可能產生非預期的工具關聯

**修正策略：** 重新命名工具以消除重疊，將泛用工具拆分為有明確 I/O 契約的專用工具

**教學參考：** `ex1_agent/tools.py` — 比較詳細的 `get_customer` 描述 vs 簡陋的「查詢客戶」

### 2.2 MCP 工具的結構化錯誤回應
**核心概念：**
- MCP `isError` 旗標用於向代理傳達工具失敗
- 錯誤分類：transient（超時）、validation（輸入錯誤）、business（政策違規）、permission（權限不足）
- **為何統一錯誤訊息有害：**「操作失敗」阻止代理做出適當的恢復決策
- 區分：存取失敗（需要重試決策）vs 有效的空結果（查詢成功但無匹配）

**教學參考：** `shared/types.py` — `ToolError` 含 `errorCategory`、`isRetryable`、`message`

### 2.3 工具分配與 tool_choice
**核心概念：**
- 給代理太多工具（18 個而非 4-5 個）會降低選擇可靠性
- 持有超出專業範圍的工具的代理傾向於誤用它們
- 限定工具存取範圍：每個代理只提供其角色所需的工具
- `tool_choice` 選項：`"auto"`（模型決定）、`"any"`（必須使用工具）、`{"type": "tool", "name": "..."}`（必須使用指定工具）
- 強制選擇用於保證結構化輸出；`"any"` 用於存在多個擷取 schema 的情況

**教學參考：** `ex3_extraction/extractor.py` — 強制 `tool_choice` 進行擷取

### 2.4 MCP 伺服器整合
**核心概念：**
- 專案級 `.mcp.json` 用於團隊共享工具；使用者級 `~/.claude.json` 用於個人/實驗性工具
- 環境變數展開：`${GITHUB_TOKEN}`——**永遠不要硬編碼密鑰**
- 所有已設定 MCP 伺服器的工具在連線時被發現
- MCP 資源：公開內容目錄（議題摘要、文件階層、資料庫 schema）以減少探索性工具呼叫
- 標準整合優先使用現有社群 MCP 伺服器，自訂伺服器用於團隊特定工作流程

**教學參考：** `ex2_claude_code/.mcp.json` — GitHub MCP 伺服器使用 `${GITHUB_TOKEN}`

### 2.5 內建工具選擇
**核心概念：**
- **Grep：** 內容搜尋（函式名、錯誤訊息、import 語句）
- **Glob：** 檔案路徑模式匹配（按名稱或副檔名找檔案）
- **Read/Write：** 完整檔案操作；**Edit：** 使用唯一文字匹配進行針對性修改
- Edit 失敗時（非唯一匹配）：用 Read + Write 作為備選方案
- 漸進式理解程式碼庫：Grep → 找到入口點 → Read 追蹤 import 和執行流程

---

## 領域 3：Claude Code 設定與工作流程（20%）

### 3.1 CLAUDE.md 階層
**核心概念：**
- 三個層級：使用者級（`~/.claude/CLAUDE.md`）、專案級（`.claude/CLAUDE.md` 或根目錄 `CLAUDE.md`）、目錄級（子目錄 `CLAUDE.md`）
- 使用者級 = 僅個人使用，不透過版本控制共享
- `@import` 語法引用外部檔案，保持 CLAUDE.md 模組化
- `.claude/rules/` 目錄存放主題特定規則檔，作為龐大單一 CLAUDE.md 的替代方案

**教學參考：** `ex2_claude_code/CLAUDE.md` 及第三章的設定階層說明

### 3.2 自訂命令與技能
**核心概念：**
- **Commands**（`.claude/commands/`）：專案級、透過版本控制共享、使用者觸發的斜線命令
- **Skills**（`.claude/skills/`）：可重用的代理定義，附帶 frontmatter
  - `context: fork` — 隔離的執行上下文，不污染主 session
  - `allowed-tools` — 白名單限制工具存取（安全邊界）
  - `argument-hint` — 提示使用者輸入的佔位字串
- 個人命令：`~/.claude/commands/`（不共享）
- 個人技能變體：`~/.claude/skills/` 使用不同名稱，避免影響隊友
- 選擇 skills（按需載入）vs CLAUDE.md（永遠載入）取決於上下文是通用的還是任務特定的

### 3.3 路徑特定規則
**核心概念：**
- `.claude/rules/` 檔案含 YAML frontmatter `paths:` 欄位，使用 glob 模式
- 僅在編輯匹配檔案時載入規則 → 減少無關上下文和 token 消耗
- 相比目錄級 CLAUDE.md 的優勢：glob 模式規則可覆蓋跨多目錄的慣例（如：`**/*.test.tsx` 覆蓋所有測試檔）

**教學參考：** `ex2_claude_code/.claude/rules/` — React 元件慣例限定於 `src/components/**/*`

### 3.4 Plan Mode vs 直接執行
**核心概念：**
- **Plan mode：** 複雜任務、大規模變更、多種可行方案、架構決策、多檔修改
- **直接執行：** 簡單、範圍明確的變更（單檔 bug fix、新增驗證檢查）
- Plan mode 允許在提交變更前安全探索
- 使用 Explore 子代理處理冗長的探索，保護主上下文
- 可結合使用：plan mode 用於調查 → 直接執行用於實作

### 3.5 迭代式精煉
**核心概念：**
- 具體的輸入/輸出範例在文字描述被不一致解讀時最有效
- 測試驅動迭代：先寫測試 → 分享失敗結果 → 引導改進
- 訪談模式：讓 Claude 提問以發掘開發者未預想到的考量
- 何時在單一訊息中提供所有問題（相互影響的問題）vs 逐一修正（獨立問題）

### 3.6 CI/CD 整合
**核心概念：**
- `-p`（或 `--print`）旗標用於自動化流水線中的非互動模式
- `--output-format json` + `--json-schema` 用於 CI 的結構化輸出
- CLAUDE.md 為 CI 呼叫的 Claude Code 提供專案上下文（測試標準、review 準則）
- Session 上下文隔離：生成程式碼的同一 session 審查效果較差——使用獨立的審查實例
- 重新執行 review 時包含先前的發現，避免重複評論

---

## 領域 4：提示工程與結構化輸出（20%）

### 4.1 明確標準提升精確度
**核心概念：**
- 明確標準 > 模糊指令：「僅在宣稱的行為與實際程式碼行為矛盾時標記註解」vs「檢查註解是否準確」
- 「保守一點」或「只報告高信心發現」等通用指令無法提升精確度
- 某類別的高誤報率會破壞對準確類別的信心
- 撰寫具體 review 標準：定義什麼要報告（bug、安全）vs 什麼要跳過（風格瑣事、局部模式）

### 4.2 Few-Shot 提示
**核心概念：**
- 詳細指令仍產生不一致結果時，最有效的格式一致化技術
- 為模糊案例展示推理過程（為何選擇某個動作而非其他替代方案）
- 讓模型學會對新模式的泛化判斷，而非僅匹配預設案例
- 在擷取任務中減少幻覺（處理非正式度量、多樣的文件結構）
- 為模糊情境使用 2-4 個針對性範例

### 4.3 透過 tool_use + JSON Schema 確保結構化輸出
**核心概念：**
- `tool_use` 搭配 JSON schema = 保證 schema 合規輸出的最可靠方法（消除 JSON 語法錯誤）
- `tool_choice: "auto"`（可能回傳文字）、`"any"`（必須呼叫工具）、`{"type": "tool", "name": "..."}`（必須呼叫特定工具）
- 嚴格 JSON schema 消除語法錯誤但**不能**防止語意錯誤（值放錯欄位、小計不等於總計）
- Schema 設計：required vs optional 欄位、enum 含 `"other"` + 詳情字串模式、nullable 欄位防止幻覺

**教學參考：** `ex3_extraction/schema.py` — `DocumentExtraction` 含 nullable 欄位、`conflict_detected` 旗標

### 4.4 驗證、重試與回饋迴圈
**核心概念：**
- Retry-with-error-feedback：在重試 prompt 中附加具體驗證錯誤以引導修正
- 當資訊根本不存在於來源時，重試無效（vs 格式/結構錯誤時有效）
- 發現中的 `detected_pattern` 欄位可進行誤報的系統性分析
- 語意驗證：擷取 "calculated_total" 和 "stated_total" 以標記差異

**教學參考：** `ex3_extraction/validator.py` — 語意驗證 + 附帶具體錯誤的重試迴圈

### 4.5 批次處理
**核心概念：**
- Message Batches API：節省 50% 成本、最長 24 小時處理時間、無延遲 SLA
- 適用於：隔夜報告、每週稽核、夜間測試生成
- **不適用於：** 阻塞型工作流程（merge 前檢查）
- 單一批次請求內不支援多輪工具呼叫
- `custom_id` 用於關聯請求/回應配對
- 僅重新提交失敗項目（由 `custom_id` 識別），而非整個批次

**教學參考：** `ex3_extraction/batch.py` — submit → poll → handle_failures 工作流程

### 4.6 多實例與多遍審查
**核心概念：**
- 自我審查的限制：模型保留推理上下文，不太可能質疑自己的決定
- 獨立審查實例（不含先前推理）能發現更多細微問題
- 大型審查的多遍策略：逐檔局部分析 + 跨檔整合
- 驗證遍次中模型自報信心分數，用於校準過的路由分配

---

## 領域 5：上下文管理與可靠性（15%）

### 5.1 上下文保存
**核心概念：**
- 漸進式摘要的風險：將數字、日期、百分比壓縮成模糊的摘要
- 「中間遺失」效應：模型可靠處理長輸入的開頭和結尾，但可能遺漏中間部分
- 工具結果在上下文中累積的 token 與其相關性不成比例（40+ 欄位中只有 5 個有用）
- 將交易事實擷取到持久的「案例事實」區塊中，置於摘要歷史之外
- 將關鍵發現放在彙總輸入的開頭；使用明確的章節標題組織

### 5.2 升級與歧義解決
**核心概念：**
- 升級觸發條件：客戶要求人工服務、政策例外/空白、無法取得進展
- 不僅限於複雜案例——客戶明確要求時立即升級
- 基於情緒的升級和自報信心分數不是案例複雜度的可靠代理指標
- 多個客戶匹配 → 請求澄清，不要以啟發式方法選擇
- 在系統提示中新增明確的升級標準搭配 few-shot 範例

### 5.3 多代理系統的錯誤傳播
**核心概念：**
- 結構化錯誤上下文（失敗類型、嘗試的查詢、部分結果、替代方案）讓協調器能做出智慧恢復決策
- 區分存取失敗（超時 → 重試決策）vs 有效空結果（無匹配）
- 泛用錯誤狀態對協調器隱藏了有價值的上下文
- **反模式：** 靜默吞掉錯誤（將空結果當成功回傳）或單一失敗就終止整個工作流程
- 子代理應對暫時性失敗實作本地恢復，僅傳播無法本地解決的錯誤

**教學參考：** `ex4_research/errors.py` — `SubagentResult` 與 `SubagentError`

### 5.4 大型程式碼庫探索
**核心概念：**
- 長 session 中的上下文退化：模型開始引用「典型模式」而非先前發現的特定類別
- Scratchpad 檔案用於跨上下文邊界保存關鍵發現
- 子代理委派冗長探索；主代理維持高層協調
- 結構化狀態持久化用於故障恢復：代理匯出狀態到已知位置，協調器在恢復時載入清單
- 使用 `/compact` 在冗長探索 session 中減少上下文消耗

### 5.5 人工審查與信心校準
**核心概念：**
- 聚合準確率（97%）可能掩蓋特定文件類型或欄位的低表現
- 分層隨機抽樣用於測量高信心擷取的錯誤率
- 欄位級信心分數使用標注驗證集校準
- 在自動化高信心擷取之前，按文件類型和欄位區段驗證準確率
- 將低信心或模糊的擷取路由到人工審查

### 5.6 多來源綜合中的資訊溯源
**核心概念：**
- 摘要步驟中如未保留宣稱-來源映射，來源歸屬會丟失
- 綜合代理必須保留並合併宣稱-來源映射
- 來自可信來源的衝突統計數據：標注衝突並附來源歸屬，不任意選擇其一
- 要求包含發布/收集日期以防止時間性誤解
- 不同內容類型有不同呈現方式：財務數據用表格、新聞用散文、技術發現用結構化列表

**教學參考：** `ex4_research/context.py` — `ResearchContext.to_prompt_context()` 保留來源 URL 和日期

---

## 範例題目解析

### Q1：代理在 12% 的案例中跳過 `get_customer` → 帳號辨識錯誤
**答案：A** — 程式化前提條件 gate。關鍵業務邏輯（退款前驗證身份）需要確定性保證，提示方法（B、C）是機率性的。路由分類器（D）處理的是工具可用性而非順序。

### Q2：代理在客戶查詢訂單時呼叫 `get_customer` 而非 `lookup_order`
**答案：B** — 擴充工具描述，包含輸入格式、查詢範例、邊界說明。工具描述是選擇的主要機制。低成本、高槓桿的修正。Few-shot 範例（A）增加 token 卻未修正根因。路由層（C）過度工程。合併工具（D）有效但力度過大。

### Q3：代理升級簡單案例、自行處理複雜案例（解決率 55% vs 目標 80%）
**答案：A** — 新增明確的升級標準搭配 few-shot 範例展示何時升級 vs 自行解決。解決不明確的決策邊界。自報信心（B）校準不良。獨立分類器（C）需要標注資料和 ML 基礎設施。情緒分析（D）與案例複雜度無關。

### Q4：團隊共享的 `/review` 命令應放在哪？
**答案：A** — `.claude/commands/` 在專案 repo 中。版本控制、自動可用。`~/.claude/commands/`（B）僅個人使用。CLAUDE.md（C）用於指令而非命令定義。`.claude/config.json`（D）不存在。

### Q5：單體應用 → 微服務重構的方法？
**答案：A** — 進入 plan mode。複雜任務需要多種可行方案和架構決策，先探索再提交。直接執行（B）可能導致昂貴的返工。全面的前期指令（C）假設你已知結構。反應式 plan mode（D）忽略複雜度已經是已知的。

### Q6：不同慣例（React/API/DB/tests）分散在各目錄？
**答案：A** — `.claude/rules/` 搭配 YAML frontmatter glob 模式。根據檔案路徑自動套用慣例，不受目錄位置限制。根 CLAUDE.md（B）依賴推斷。Skills（C）需手動觸發。子目錄 CLAUDE.md（D）無法處理分散各處的檔案。

### Q7：「AI 在創意產業的影響」研究只涵蓋視覺藝術
**答案：B** — 協調器的任務分解過於狹窄。只分解為視覺藝術子任務，遺漏了音樂/寫作/電影。子代理在其被指派的範圍內正確執行。問題在於被指派了「什麼」，而非「如何」執行。

### Q8：網頁搜尋子代理超時——最佳錯誤傳播方式？
**答案：A** — 回傳結構化錯誤上下文（失敗類型、嘗試的查詢、部分結果、替代方案）。讓協調器能做出智慧恢復決策。泛用狀態（B）隱藏上下文。當成功處理（C）靜默產生不完整輸出。終止工作流程（D）過度破壞性。

### Q9：綜合代理需要事實驗證，增加 2-3 次往返（延遲增加 40%）
**答案：A** — 給綜合代理一個限定範圍的 `verify_fact` 工具用於簡單查詢（85% 的案例），複雜驗證仍透過協調器。最小權限原則。批次處理（B）產生阻塞依賴。完整搜尋工具（C）違反關注點分離。預測性快取（D）無法預測驗證需求。

### Q10：CI 流水線因等待互動輸入而掛起
**答案：A** — 使用 `-p` 旗標：`claude -p "Analyze this pull request for security issues"`。這是文件記載的非互動模式。其他選項引用不存在的功能。

### Q11：兩個工作流程都切換到 Batch API 以節省 50%？
**答案：A** — 僅隔夜技術債報告使用 Batch；merge 前檢查保持即時呼叫。Batch API 無延遲 SLA（最長 24 小時）——不適合阻塞型工作流程。

### Q12：14 檔 PR 的單遍 review 產生不一致結果
**答案：A** — 拆分為逐檔分析 + 跨檔整合。直接解決注意力稀釋問題。要求更小的 PR（B）將負擔轉嫁開發者。更大的上下文視窗（C）無法解決注意力品質問題。共識過濾（D）會抑制間歇性發現的真實 bug。

---

## 交叉參照：考試領域 ↔ 教學練習

| 練習 | 教學章節 | 主要涉及領域 |
|------|---------|------------|
| ex1_agent（多工具代理） | 第二章 | 領域 1（代理迴圈、hooks、gates）、領域 2（工具設計、結構化錯誤） |
| ex2_claude_code（設定） | 第三章 | 領域 3（CLAUDE.md、rules、commands、skills、MCP） |
| ex3_extraction（結構化資料） | 第四章 | 領域 4（tool_use schema、驗證/重試、Batch API） |
| ex4_research（多代理流水線） | 第五章 | 領域 1（協調器-子代理）、領域 2（工具分配）、領域 5（錯誤傳播、溯源） |

---

## 速查表：關鍵 API 細節

| 概念 | 值 / 語法 | 使用時機 |
|------|----------|---------|
| `stop_reason` | `"tool_use"`、`"end_turn"`、`"max_tokens"`、`"stop_sequence"` | 代理迴圈控制流程 |
| `tool_choice` | `"auto"`、`"any"`、`{"type":"tool","name":"..."}` | `auto` = 預設；`any` = 必須使用工具；forced = 保證結構化輸出 |
| `tool_result` 欄位 | `type`、`tool_use_id`、`content`、`is_error` | 每個 tool result 必須匹配 tool_use block 的 `tool_use_id` |
| 錯誤分類 | `transient`、`validation`、`permission`、`business` | 工具回應中的結構化錯誤處理 |
| CLAUDE.md 層級 | user (`~/.claude/`)、project (root/.claude/)、directory | user = 個人；project = 共享；directory = 限定範圍 |
| Rules frontmatter | `paths: ["glob/**/*"]` | 僅在編輯匹配檔案時載入規則 |
| Skills frontmatter | `context: fork`、`allowed-tools`、`argument-hint` | 隔離執行、限制工具存取 |
| MCP 設定 | `.mcp.json`（專案）、`~/.claude.json`（使用者） | `${ENV_VAR}` 處理密鑰——永不硬編碼 |
| CI 旗標 | `-p` / `--print`、`--output-format json`、`--json-schema` | 非互動模式、結構化 CI 輸出 |
| Batch API | `custom_id`、節省 50%、≤24h、無多輪工具 | 僅限離線流水線——永不用於阻塞型工作流程 |

---

## 備考清單

1. [ ] **建構代理迴圈** — 實作 `while True` / `stop_reason` 控制流程搭配工具分派
2. [ ] **新增 hooks 與 gates** — Pre-tool hooks 用於業務規則強制執行，程式化 gates 用於順序控制
3. [ ] **設定 Claude Code** — CLAUDE.md 階層、路徑限定規則、commands、skills、MCP
4. [ ] **設計工具描述** — 區分相似工具，包含邊界說明和範例
5. [ ] **建構結構化擷取** — `tool_use` 搭配強制 `tool_choice`、nullable schema 欄位、語意驗證
6. [ ] **實作 retry-with-feedback** — 在重試 prompt 中注入具體錯誤
7. [ ] **設計批次處理** — submit → poll → handle failures 工作流程搭配 `custom_id`
8. [ ] **建構多代理流水線** — 協調器搭配並行子代理、明確的上下文傳遞、結構化錯誤傳播
9. [ ] **練習 few-shot 提示** — 為模糊情境撰寫針對性範例
10. [ ] **執行所有練習** — `uv run pytest` 應顯示 49 passed

---

## 考試範圍外的主題

以下主題**不會**出現在考試中：
- 微調 Claude / 訓練自訂模型
- API 認證、帳單、帳號管理
- 詳細程式語言實作（超出工具/schema 設定的範圍）
- 部署/託管 MCP 伺服器（基礎設施、網路）
- Claude 內部架構、訓練過程、模型權重
- Constitutional AI、RLHF、安全訓練方法
- Embedding 模型、向量資料庫
- Computer use（瀏覽器自動化）
- 視覺/圖像分析功能
- Streaming API、server-sent events
- 速率限制、配額、定價
- OAuth、API key 輪替
- 雲端供應商設定（AWS、GCP、Azure）
- 效能基準測試、模型比較
- Prompt caching 實作細節
- Token 計數演算法

---

*搭配[實作教學](tutorial-zh.md)與官方考試指南 PDF 使用本導讀指南。執行 `uv run pytest` 驗證你的練習題正常運作。*
