<a name="english"></a>
# Unveiling

<p align="center">
  <b>Tension-style analysis. Not commonality stacking.</b>
  <br><br>
  <a href="#quick-start">Quick Start</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#web-interface">Web UI</a> ·
  <a href="#prompt-lab">Prompt Lab</a> ·
  <a href="#chinese">中文</a>
</p>

---

Unveiling is a multi-agent analogy analysis system built on **LangGraph**. You bring a driving question; the system abstracts it into structural patterns, searches for analogies across domains and across eras in parallel, and synthesizes a **tension-style conclusion** — core finding, underlying conflict, boundary conditions, unresolved questions — rather than a summary that buries disagreement.

The system runs a three-phase pipeline: **Inception** (structural abstraction) → **Exploration** (parallel lateral + vertical search) → **Convergence** (tension synthesis). All state flows through a four-zone append-only blackboard, and every LLM failure degrades gracefully instead of crashing.

## Why Unveiling?

Most AI analysis tools converge on plausible-sounding consensus. Unveiling is built around two design choices that push in the opposite direction:

- **Tension is the unit of insight.** Every conclusion must name a genuine conflict, specify the boundary conditions under which it holds, and explicitly list what remains unresolved. "There are pros and cons" is not a tension.
- **Analogies must be structural, not surface-level.** The system abstracts your question into roles and relationships before searching — so it finds "a platform that started as public infrastructure and became a shopping mall" instead of "another tech company."

Beneath those: an append-only blackboard, lens version chains that never mutate in place, per-direction independent convergence (each direction stops at 10 cases or 3 rounds), and a token-budget hard ceiling that forces honest convergence.

<a name="architecture"></a>
## Architecture

```
                         ┌─── Inception ─── Exploration ─── Convergence ───┐
                         │              (three-phase pipeline)              │
                         ▼                                                 ▼
   Driving Question  →  Structural Lens  →  ~20 Cases  →  Tension-Style Output

                              Parallel Search
                         ┌──── Lateral (cross-domain) ────┐
                         │     each finds up to 10 cases   │
                         └──── Vertical (cross-era) ───────┘

                   Four-Zone Blackboard (append-only, committed | retracted)
                   ├─ hypothesis_zone    (lens version chain)
                   ├─ evidence_zone      (cases with full metadata)
                   ├─ conclusion_zone    (tension-style records)
                   └─ schedule_log       (scheduler decisions, degradations)
```

### Three Layers

| Layer | Module | Responsibility |
|-------|--------|----------------|
| **Control** | `orchestrator/` | Rule-based scheduler decides when to continue searching vs. converge. Token budget is the hard brake. |
| **Execution** | `agents/` | Three worker agents that call LLMs and search APIs. They never decide what runs next. |
| **State** | `blackboard/` | Four-zone append-only blackboard with reducer-based state merging. |

### Three Execution Agents

| Agent | Phase | Role |
|-------|-------|------|
| **inception** | Phase 1 | Abstracts the driving question into structural roles, relationships, hidden dynamics, cross-domain analogue hints, and a root-cause chain. Produces one `LensRecord`. |
| **search** | Phase 2 | Parallel lateral (cross-domain) + vertical (cross-era) evidence collection. Each direction independently converges at 10 cases or 3 rounds. Pre-validates queries, extracts distinct cases, deduplicates across directions. |
| **convergence** | Phase 3 | Synthesizes all evidence into a tension-style conclusion with core finding, tension, boundary conditions, unresolved questions, temporal trajectory, and crystallized taglines. |

### Rule-Based Scheduler

The orchestrator in Phase 2 is entirely rule-based (no LLM calls):

1. If token budget exceeded → force convergence immediately.
2. If both directions done (target met or rounds exhausted) → converge.
3. Otherwise → continue parallel search.

Every LLM failure is caught, degraded gracefully, and logged as a degradation event in `schedule_log`.

<a name="web-interface"></a>
## Web Interface

The frontend (`frontend/`) is a single-page app with server-sent events for real-time progress:

- **Home screen** — Enter your question, pick a mode (near / balanced / far explore), choose output language (Chinese / English), or pick from suggested starter questions.
- **Analysis screen** — Watch the three-phase pipeline in real time:
  - **Phase ribbon** tracks Inception → Exploration → Convergence.
  - **Lens reveal** shows the structural pattern found in Phase 1 (entities, relationships).
  - **Dual progress rails** — parallel lateral and vertical search progress (each direction converges independently at 10 cases or 3 rounds).
  - **Case feed** — chronological stream of evidence as it arrives.
  - **Machine view drawer** — collapsible schedule log + token count for transparency.
  - **Integrity strip** — summary of search breadth after completion.
  - **Conclusion chapters** — full tension-style result revealed progressively.
- **Demo mode** — Append `?demo=1` to load a pre-generated example output.

<a name="prompt-lab"></a>
## Prompt Lab

All agent prompts live in `prompt_lab/` as plain text files with variable placeholders. The `/prompt-lab` web UI lets you:

- Browse and edit all 7 prompts without restarting the server.
- Discover available template variables.
- Preview rendered prompts with custom variable values.
- Run prompts against the LLM in isolation and view the output.
- Browse run history (in-memory ring buffer).

Prompts are reloaded from disk on every agent call, so edits take effect on the next pipeline run with no restart.

| Prompt | Agent | Purpose |
|--------|-------|---------|
| `inception_system` | inception | System role for the abstraction engine |
| `inception_user` | inception | User prompt with `{question}` variable |
| `lateral_query` | search | Generate cross-domain search queries |
| `vertical_query` | search | Generate cross-era search queries |
| `validate_queries` | search | Pre-search dedup + direction validation |
| `case_extraction` | search | Extract structured cases from search results |
| `convergence_synthesize` | convergence | Synthesize evidence into tension-style output |

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | LangGraph (StateGraph with reducer-based state) |
| **LLM** | DeepSeek via OpenAI-compatible API (`deepseek-chat` default) |
| **Search** | Serper API (Google Search proxy, `tenacity` retry) |
| **Data Models** | Pydantic v2 (`strict=True`, `extra="forbid"`) |
| **Web Server** | Flask + SSE (real-time streaming) |
| **Frontend** | Vanilla HTML / CSS / JS (no framework) |
| **Production** | Gunicorn + gevent (Render deployment) |
| **Testing** | pytest + pytest-asyncio |

<a name="quick-start"></a>
## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your keys:

```
OPENAI_API_KEY="your-deepseek-api-key"
OPENAI_API_BASE="https://api.deepseek.com"
OPENAI_MODEL_NAME="deepseek-chat"
SERPER_API_KEY="your-serper-api-key"
```

- [DeepSeek API Key](https://platform.deepseek.com)
- [Serper API Key](https://serper.dev)

### 3. Run

**CLI mode:**

```bash
# minimal
python main.py -q "Should AI companies burn cash to expand?"

# with optional context and mode
python main.py \
  --question "Should AI companies burn cash to expand?" \
  --context "I am evaluating an investment in an AI startup" \
  --mode focus     # focus | balance | explore
```

**Web mode:**

```bash
python frontend/app.py
# open http://localhost:5001
```

### 4. Run Tests

```bash
# unit + integration
pytest

# end-to-end against real APIs (small token budget)
pytest -m e2e
```

<a name="output-format"></a>
## Output Format

Conclusions are structured as **tension records**, not commonality lists:

| Field | Meaning |
|-------|---------|
| `core_finding` | The most robust finding that survived all scrutiny. |
| `tension` | The central conflict the analysis reveals (real conflict — not "pros and cons"). |
| `boundary_condition` | The specific, testable conditions under which the finding holds vs. breaks down. |
| `unresolved` | What remains genuinely uncertain. Never empty — every honest analysis leaves something open. |
| `implication` | What this means for the original driving question. |
| `temporal_trajectory` | How the dynamic has evolved over time (optional). |
| `taglines` | One-line crystallizations per chapter. |

Every run also emits an **analysis-integrity summary**: lateral/vertical case counts, degradation events, and token consumption — so you can see how broad and honest the search was.

## Deployment

The project includes Render deployment config:

```yaml
# render.yaml — deploy with one click
services:
  - type: web
    name: unveiling
    runtime: python
    startCommand: "gunicorn -k gevent -w 1 -b 0.0.0.0:$PORT --timeout 300 frontend.app:app"
```

Environment variables (`OPENAI_API_KEY`, `OPENAI_API_BASE`, `OPENAI_MODEL_NAME`, `SERPER_API_KEY`) are set in the Render dashboard.

## Key Invariants

The system enforces these invariants. Violating any breaks the design:

1. **Three-phase separation.** Inception doesn't search; Exploration doesn't conclude; Convergence doesn't go back and search more.
2. **Cognitive / execution / control layers are separated.** Agents never decide what runs next.
3. **Blackboard records have only two states:** `committed` and `retracted`. No drafts.
4. **Evidence zone and schedule log are append-only** — never physically deleted.
5. **Every evidence record carries full metadata:** `source_lens_id`, `search_direction`, `case_name`, `layer`, `confidence`, `is_unexpected`. None are optional.
6. **Lens operations create new versions;** the version chain is immutable.
7. **LLM failures degrade, never crash.** Every LLM call has a fallback path, and degradations are logged.
8. **Search doesn't embed extra abstraction.** Queries use structural roles from Phase 1; LLM only judges structural fit.
9. **Lateral and vertical search are parallel,** each converging independently.

See `CLAUDE.md` for day-to-day code-level conventions, and `docs/PRD.md` for the full design philosophy.

## Project Structure

```
.
├── main.py                     # CLI entry point
├── models/                     # Pydantic v2 data models
│   ├── _enums.py               # shared enums (RecordStatus, EvidenceLayer, Phase, …)
│   ├── blackboard.py           # zone record types (LensRecord, EvidenceRecord, …)
│   └── state.py                # LangGraph State (four zones + search counters)
├── blackboard/
│   └── reducers.py             # merge_lists / merge_dicts / replace
├── orchestrator/
│   ├── scheduler.py            # rule-based scheduler (token budget, coverage check)
│   └── rules.py                # TARGET_EXAMPLES, MIN_EXAMPLES, MAX_ROUNDS constants
├── agents/
│   ├── inception.py            # Phase 1: structural abstraction
│   ├── search.py               # Phase 2: parallel lateral + vertical search
│   └── convergence.py          # Phase 3: tension-style synthesis
├── graph/
│   ├── build.py                # StateGraph topology
│   └── routing.py              # conditional routing after scheduler
├── llm/
│   ├── client.py               # DeepSeek client, JSON retry, token accounting
│   ├── degradation.py          # DegradationLogger → ScheduleLogEntry
│   └── prompt_loader.py        # load prompts from prompt_lab/ on every call
├── search/
│   ├── serper.py               # Serper API wrapper (tenacity retry)
│   └── query_gen.py            # query generation helpers
├── frontend/
│   ├── app.py                  # Flask + SSE (analysis + prompt lab APIs)
│   ├── templates/
│   │   ├── index.html          # main analysis UI
│   │   └── prompt-lab.html     # prompt editing UI
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── prompt_lab/                 # live-editable agent prompts
│   ├── meta.json               # prompt metadata (variables, phase, description)
│   ├── inception_system.txt
│   ├── inception_user.txt
│   ├── lateral_query.txt
│   ├── vertical_query.txt
│   ├── validate_queries.txt
│   ├── case_extraction.txt
│   └── convergence_synthesize.txt
├── output/                     # generated HTML analysis reports (gitignored)
├── docs/
│   ├── PRD.md                  # full product/architecture spec
│   └── prompts/                # versioned agent prompt history
├── tests/
│   ├── unit/                   # mirrors source structure
│   └── e2e/                    # real-API tests (@pytest.mark.e2e)
├── render.yaml                 # Render deployment config
├── Procfile                    # process definition for deployment
├── deploy.sh                   # self-hosted deployment script (Ubuntu + systemd)
└── requirements.txt
```

## Acknowledgments

The interactive HTML slide presentation is inspired by [frontend-slides](https://github.com/zarazhangrui/frontend-slides).

## License

MIT

---

<a name="chinese"></a>
# 中文

<p align="center">
  <b>张力式分析。不是共性堆叠。</b>
  <br><br>
  <a href="#english">English</a> ·
  <a href="#快速开始">快速开始</a> ·
  <a href="#架构">架构</a> ·
  <a href="#web-界面">Web 界面</a> ·
  <a href="#提示词实验室">提示词实验室</a>
</p>

---

Unveiling（"揭示"）是一个基于 **LangGraph** 的多 Agent 类比分析系统。你带着驱动问题来，系统先把问题抽象成结构角色和关系，然后在跨领域和跨时期两个维度上并行搜索类比案例，最终产出**张力式结论**——核心发现、核心冲突、边界条件、未解之问——而不是把分歧抹平的"折中型摘要"。

系统跑一个三阶段管线：**抽象**（结构抽象）→ **搜集**（横向 + 纵向并行搜索）→ **收拢**（张力合成）。所有状态流经四分区只增不删的黑板，每个 LLM 调用都有降级兜底，不会因为 API 故障而崩溃。

## 为什么做 Unveiling？

大多数 AI 分析工具最终都收敛到"听起来合理的共识"。Unveiling 围绕两个相反方向的设计抉择展开：

- **张力是洞察的最小单元。** 每个结论必须命名一个真实冲突，给出该结论成立 / 失效的边界条件，并明确列出仍未解决的问题。"既有优点也有缺点"不算张力。
- **类比必须是结构层面的，不是表面匹配。** 系统先把你的问题抽象成角色和关系，再去搜索——所以它找到的是"一个从公共基础设施变成购物中心的平台"，而不是"又一家科技公司"。

底层支撑：只增不删的黑板、永远不原地修改的透镜版本链、每方向独立收敛（各找 10 个案例或跑满 3 轮即停）、token 预算硬上限强制诚实收敛。

<a name="架构"></a>
## 架构

```
                         ┌─── 抽象 ─── 搜集 ─── 收拢 ───┐
                         │         （三阶段管线）          │
                         ▼                                ▼
   驱动问题  →   结构透镜  →  ~20 个案例  →  张力式结论

                              并行搜索
                         ┌──── 横向（跨领域） ────────────┐
                         │     各方向独立收敛，找满 10 个  │
                         └──── 纵向（跨时期） ────────────┘

                  四分区黑板（只增不删，状态仅 committed / retracted）
                  ├─ hypothesis_zone    （透镜版本链）
                  ├─ evidence_zone      （含完整元数据的案例）
                  ├─ conclusion_zone    （张力式记录）
                  └─ schedule_log       （调度决策、降级事件）
```

### 三层架构

| 层级 | 模块 | 职责 |
|------|------|------|
| **控制层** | `orchestrator/` | 纯规则调度器：判断继续搜索还是收敛。Token 预算是硬刹车。 |
| **执行层** | `agents/` | 三个工作 Agent，调用 LLM 和搜索 API。永远不决定下一步做什么。 |
| **状态层** | `blackboard/` | 四分区只增不删黑板，通过 reducer 合并状态更新。 |

### 三个执行 Agent

| Agent | 阶段 | 职责 |
|-------|------|------|
| **inception** | 阶段一 | 将驱动问题抽象为结构角色、关系、隐藏动力学、跨领域类比线索和根因链。产出一条 `LensRecord`。 |
| **search** | 阶段二 | 横向（跨领域）+ 纵向（跨时期）并行搜索。每方向独立收敛（10 个案例或 3 轮即停）。预校验查询、提取不重复案例、跨方向去重。 |
| **convergence** | 阶段三 | 将所有证据合成为张力式结论：核心发现、核心冲突、边界条件、未解之问、时间轨迹和章节金句。 |

### 规则调度器

阶段二的 Orchestrator 完全基于规则（不调 LLM）：

1. Token 预算超限 → 立即强制收敛。
2. 两个方向都完成（达到目标或轮次耗尽）→ 收敛。
3. 否则 → 继续并行搜索。

每个 LLM 故障都会被捕获、优雅降级，并作为降级事件写入 `schedule_log`。

<a name="web-界面"></a>
## Web 界面

前端（`frontend/`）是一个单页应用，通过 Server-Sent Events 实时推送分析进度：

- **首页** — 输入问题、选择模式（就近 / 平衡 / 远探）、输出语言（中文 / English），或从推荐问题中挑选。
- **分析页** — 实时观看三阶段管线运行：
  - **阶段指示条** 追踪 抽象 → 搜集 → 收拢。
  - **透镜揭示** 展示阶段一找到的结构模式（角色、关系）。
  - **双轨进度条** — 横向和纵向搜索并行推进，各自独立收敛。
  - **案例流** — 证据到达时的实时时间线。
  - **机器视角抽屉** — 可折叠的调度日志 + token 计数。
  - **诚信度条** — 搜索完成后展示搜索广度摘要。
  - **结论章节** — 完成后逐步揭示的完整张力式结果。
- **演示模式** — URL 后加 `?demo=1` 加载预生成的示例输出。

<a name="提示词实验室"></a>
## 提示词实验室

所有 Agent 提示词存放在 `prompt_lab/` 中，是带有变量占位符的纯文本文件。`/prompt-lab` Web UI 支持：

- 浏览和编辑全部 7 个提示词，无需重启服务器。
- 自动发现模板中的可用变量。
- 用自定义变量值预览渲染后的提示词。
- 单独运行提示词到 LLM 并查看输出。
- 浏览运行历史（内存环形缓冲区）。

提示词在每次 Agent 调用时从磁盘重新加载，编辑后在下次管线运行时即刻生效。

| 提示词 | Agent | 用途 |
|--------|-------|------|
| `inception_system` | inception | 抽象引擎的系统角色 |
| `inception_user` | inception | 用户提示词（含 `{question}` 变量） |
| `lateral_query` | search | 生成跨领域搜索查询 |
| `vertical_query` | search | 生成跨时期搜索查询 |
| `validate_queries` | search | 搜索前去重 + 方向校验 |
| `case_extraction` | search | 从搜索结果中提取结构化案例 |
| `convergence_synthesize` | convergence | 将证据合成为张力式输出 |

## 技术栈

| 组件 | 技术 |
|------|------|
| **框架** | LangGraph（StateGraph + reducer 状态合并） |
| **LLM** | DeepSeek，通过 OpenAI 兼容 API（默认 `deepseek-chat`） |
| **搜索** | Serper API（Google Search 代理，`tenacity` 重试） |
| **数据模型** | Pydantic v2（`strict=True`、`extra="forbid"`） |
| **Web 服务** | Flask + SSE（实时流式推送） |
| **前端** | 原生 HTML / CSS / JS（无框架） |
| **生产部署** | Gunicorn + gevent（Render 部署） |
| **测试** | pytest + pytest-asyncio |

<a name="快速开始"></a>
## 快速开始

### 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填入密钥：

```
OPENAI_API_KEY="your-deepseek-api-key"
OPENAI_API_BASE="https://api.deepseek.com"
OPENAI_MODEL_NAME="deepseek-chat"
SERPER_API_KEY="your-serper-api-key"
```

- [DeepSeek API Key](https://platform.deepseek.com)
- [Serper API Key](https://serper.dev)

### 3. 运行

**命令行模式：**

```bash
# 最简用法
python main.py -q "AI 公司现在应不应该烧钱扩张？"

# 完整用法（可选 context 与 mode）
python main.py \
  --question "AI 公司现在应不应该烧钱扩张？" \
  --context "我在评估投资某 AI 初创" \
  --mode focus     # focus | balance | explore
```

**Web 模式：**

```bash
python frontend/app.py
# 浏览器打开 http://localhost:5001
```

### 4. 运行测试

```bash
# 单元 + 集成测试
pytest

# 真实 API 端到端测试（小预算）
pytest -m e2e
```

<a name="输出格式"></a>
## 输出格式

结论是结构化的**张力记录**，而不是共性列表：

| 字段 | 含义 |
|------|------|
| `core_finding` | 经过所有审查幸存的最稳健发现。 |
| `tension` | 本次分析揭示的核心冲突（真实冲突——不是"既有优点也有缺点"）。 |
| `boundary_condition` | 该发现成立 / 失效的具体、可检验的条件。 |
| `unresolved` | 仍然真正不确定的部分。永远不为空——任何诚实的分析都会留有余地。 |
| `implication` | 这对原始驱动问题意味着什么。 |
| `temporal_trajectory` | 该动态随时间的演化轨迹（可选）。 |
| `taglines` | 每个章节的一句话凝练。 |

每次运行都会附带一份**分析诚信度摘要**：横向/纵向案例数、降级事件数、token 消耗量——让你能看到搜索有多广、多诚实。

## 部署

项目包含 Render 部署配置：

```yaml
# render.yaml — 一键部署
services:
  - type: web
    name: unveiling
    runtime: python
    startCommand: "gunicorn -k gevent -w 1 -b 0.0.0.0:$PORT --timeout 300 frontend.app:app"
```

环境变量（`OPENAI_API_KEY`、`OPENAI_API_BASE`、`OPENAI_MODEL_NAME`、`SERPER_API_KEY`）在 Render 控制台中设置。

## 关键不变量

系统强制执行以下不变量。违反任何一条都会破坏设计：

1. **三阶段职责不重叠。** 抽象不搜索；搜集不做结论；收拢不回头搜索。
2. **认知层 / 执行层 / 控制层严格分离。** Agent 永远不决定下一步做什么。
3. **黑板记录只有 `committed` 和 `retracted` 两态**——没有 draft。
4. **证据区和调度日志区只增不删**——永远不允许物理删除。
5. **每条证据必须携带完整元数据：** `source_lens_id`、`search_direction`、`case_name`、`layer`、`confidence`、`is_unexpected`。缺一不可。
6. **透镜操作只能新增版本；** 版本链不可篡改。
7. **LLM 失败必须降级，不能让系统终止。** 每个 LLM 调用都有降级路径，降级事件写入调度日志。
8. **搜索不嵌入额外抽象。** 查询直接用阶段一的结构角色构造；LLM 只判断结构匹配度。
9. **横向和纵向搜索并行，各自独立收敛。**

详见 `CLAUDE.md`（代码层约定）和 `docs/PRD.md`（完整设计哲学）。

## 项目结构

```
.
├── main.py                     # CLI 入口
├── models/                     # Pydantic v2 数据模型
│   ├── _enums.py               # 共享枚举（RecordStatus / EvidenceLayer / Phase / …）
│   ├── blackboard.py           # 分区记录类型（LensRecord / EvidenceRecord / …）
│   └── state.py                # LangGraph State（四分区 + 搜索计数器）
├── blackboard/
│   └── reducers.py             # merge_lists / merge_dicts / replace
├── orchestrator/
│   ├── scheduler.py            # 纯规则调度器（token 预算、覆盖检查）
│   └── rules.py                # TARGET_EXAMPLES、MIN_EXAMPLES、MAX_ROUNDS 常量
├── agents/
│   ├── inception.py            # 阶段一：结构抽象
│   ├── search.py               # 阶段二：横向 + 纵向并行搜索
│   └── convergence.py          # 阶段三：张力式合成
├── graph/
│   ├── build.py                # StateGraph 拓扑
│   └── routing.py              # 调度器后的条件路由
├── llm/
│   ├── client.py               # DeepSeek 客户端、JSON 重试、token 计数
│   ├── degradation.py          # DegradationLogger → ScheduleLogEntry
│   └── prompt_loader.py        # 每次调用时从 prompt_lab/ 加载提示词
├── search/
│   ├── serper.py               # Serper API 封装（tenacity 重试）
│   └── query_gen.py            # 查询生成辅助
├── frontend/
│   ├── app.py                  # Flask + SSE（分析 + 提示词实验室 API）
│   ├── templates/
│   │   ├── index.html          # 主分析界面
│   │   └── prompt-lab.html     # 提示词编辑界面
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── prompt_lab/                 # 可实时编辑的 Agent 提示词
│   ├── meta.json               # 提示词元数据（变量、阶段、描述）
│   ├── inception_system.txt
│   ├── inception_user.txt
│   ├── lateral_query.txt
│   ├── vertical_query.txt
│   ├── validate_queries.txt
│   ├── case_extraction.txt
│   └── convergence_synthesize.txt
├── output/                     # 生成的 HTML 分析报告（gitignored）
├── docs/
│   ├── PRD.md                  # 完整产品 / 架构说明书
│   └── prompts/                # 版本化 Agent 提示词历史
├── tests/
│   ├── unit/                   # 镜像源代码结构
│   └── e2e/                    # 真实 API 测试（@pytest.mark.e2e）
├── render.yaml                 # Render 部署配置
├── Procfile                    # 部署进程定义
├── deploy.sh                   # 自托管部署脚本（Ubuntu + systemd）
└── requirements.txt
```

## 致谢

交互式 HTML 幻灯片演示的设计灵感来源于 [frontend-slides](https://github.com/zarazhangrui/frontend-slides)。

## License

MIT
