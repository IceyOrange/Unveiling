<a name="english"></a>
# Unveiling

<p align="center">
  <b>Tension-style analysis. Not commonality stacking.</b>
  <br><br>
  <a href="#quick-start">Quick Start</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#invariants">Invariants</a> ·
  <a href="#output-format">Output</a> ·
  <a href="#chinese">中文</a>
</p>

---

Unveiling is a multi-agent analogy-analysis system built on **LangGraph**. You bring a driving question; the system explores it across time and across domains through abstract conceptual lenses — and produces a **tension-style conclusion** (core finding, underlying conflict, boundary conditions, unresolved questions) rather than a summary that buries disagreement.

The system is a state machine: a **six-zone blackboard** + **issue-tree-driven scheduling** + a **three-role Orchestrator** (Scheduler / Judge / Meta) + a **three-phase lifecycle** (Inception → Exploration → Convergence).

## Why Unveiling?

Most AI analysis tools converge on plausible-sounding consensus. Unveiling is built around two design choices that push in the opposite direction:

- **Tension is the unit of insight.** Every conclusion must name a genuine conflict, specify the boundary conditions under which it holds, and explicitly list what remains unresolved. "There are pros and cons" is not a tension.
- **Falsifiability is mandatory.** Every prediction carries a `killer_evidence` field — the specific observation that would refute it. Predictions without a kill condition are discarded.

Beneath those: an append-only blackboard with cascade retraction, lens version chains that never mutate in place, and an explicit token-budget hard ceiling that forces honest convergence rather than runaway exploration.

<a name="architecture"></a>
## Architecture

```
                        ┌─── Inception ─── Exploration ─── Convergence ───┐
                        │           (three-phase lifecycle)               │
                        ▼                                                 ▼
  Driving Question  →  Issue Tree (the scheduling interface)  →  Tension-Style Output

       Orchestrator (control layer):  Scheduler ─ Judge ─ Meta
                                          │       │       │
                              ┌───────────┼───────┼───────┼───────────┐
                              ▼           ▼       ▼       ▼           ▼
       Execution agents:  inception  search  deepdig  lens_op  debate  prediction_check  convergence
                              │           │       │       │           │
                              └───────────┴───┬───┴───────┴───────────┘
                                              ▼
                       Six-zone Blackboard (append-only, committed | retracted)
                       ├─ issue_tree         (the cognitive layer)
                       ├─ hypothesis_zone    (lenses, predictions)
                       ├─ evidence_zone      (findings with 6 metadata fields)
                       ├─ debate_zone        (challenge–response rounds)
                       ├─ conclusion_zone    (tension-style records)
                       └─ schedule_log       (orchestrator decisions, degradations)
```

### Three Layers

| Layer | Module | Responsibility |
|-------|--------|----------------|
| **Cognitive** | `issue_tree` zone | The map of sub-questions. The only interface Scheduler reads to decide what to do next. |
| **Control** | `orchestrator/` | Scheduler picks the next move; Judge decides when a sub-question is closed; Meta decides when to restructure. |
| **Execution** | `agents/` | The 7 worker agents that actually call LLMs and search. They never decide what runs next. |

### The Seven Execution Agents

| Agent | Role |
|-------|------|
| **inception** | Clarifies the driving question, builds the initial MECE issue tree, mints 2–3 scaffold lenses, emits falsifiable predictions with `killer_evidence`. |
| **search** | Near/far/killer-evidence search across lenses (lateral = cross-domain, vertical = cross-era). |
| **deepdig** | Drills into evidence; enforces the cross-layer rule (≤2 same-layer steps, must attempt to climb to phenomenon → mechanism → structure). |
| **lens_op** | Generates / revises / splits / merges lenses. Always creates a new version, never mutates the prior one. |
| **debate** | Challenge–response rounds against committed evidence and conclusions. |
| **prediction_check** | Looks for the `killer_evidence` of each prediction and marks it `supported` / `refuted` / `modified`. |
| **convergence** | Synthesizes the final tension-style output from everything that survived. |

### The Three-Role Orchestrator

- **Scheduler** — given the issue tree, decides the next agent, target sub-question, and near/far ratio. Rule-based first; LLM only for tie-breakers.
- **Judge** — decides whether a sub-question has reached a minimum-viable answer. Hard rule: no structure/mechanism evidence → cannot close.
- **Meta** — runs periodically; decides whether the framework itself needs revision (new lens? restructure tree? give up on a stuck sub-question?). Conservative by default.

Every Orchestrator LLM call has a rule fallback; every failure is logged to `schedule_log` as a degradation event (Invariant #9).

<a name="invariants"></a>
## Architectural Invariants

The system enforces ten invariants. Each is mechanically checkable in tests; violating any breaks the design:

1. The issue tree is the sole scheduling interface.
2. Cognitive / execution / control layers are strictly separated.
3. Blackboard records have only two states: `committed` and `retracted`. No drafts.
4. Evidence, debate, and schedule-log zones are append-only — never physically deleted.
5. Every evidence record carries 6 metadata fields (`source_lens_id`, `source_lens_version`, `sub_question_id`, `layer`, `confidence`, `is_unexpected`).
6. Lens operations create new versions; the version chain is immutable.
7. Every prediction has a `killer_evidence` field. No exceptions.
8. Deep-dig respects cross-layer rules: ≤2 same-layer steps; must attempt to cross layers; "stops at layer X" is a legitimate result.
9. Every Orchestrator LLM call has a rule fallback and logs degradation on failure.
10. Token-budget hard ceiling is the final brake — when hit, convergence is forced and unfinished sub-questions are marked explicitly.

See `CLAUDE.md` for the day-to-day code-level summary, and `docs/PRD.md` for the full design philosophy.

## Tech Stack

- **Framework**: LangGraph (StateGraph + checkpointing)
- **LLM**: DeepSeek (OpenAI-compatible API, `deepseek-chat` default; `deepseek-reasoner` available for critical judgments)
- **Search**: Serper API (Google Search proxy, with `tenacity` retry)
- **Data Models**: Pydantic v2 (`strict=True`, `extra="forbid"`)
- **Web**: Flask + SSE
- **Frontend**: Vanilla HTML/CSS/JS

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
python main.py "Should AI companies burn cash to expand?"

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
# fast suite (181 unit tests)
pytest

# e2e against real DeepSeek + Serper APIs (small token budget)
pytest -m e2e
```

<a name="output-format"></a>
## Output Format

Conclusions are structured as **tension records**, not commonality lists:

| Field | Meaning |
|-------|---------|
| `convergent_finding` | The most robust finding that survived all scrutiny rounds. |
| `tension` | The central conflict the analysis reveals (real conflict — not "pros and cons"). |
| `boundary_condition` | The specific, testable conditions under which the finding holds vs. breaks down. |
| `unresolved` | What remains genuinely uncertain. Never empty — every honest analysis leaves something open. |
| `implication` | What this means for the original driving question. |

Every run also emits an **analysis-integrity summary**: closed vs. stuck sub-questions, degradation count, lens evolution depth, and unfinished branches.

## Slide Styles

The HTML deck (CLI output, generated from `frontend/slides/`) supports three presets:

| Style | Description |
|-------|-------------|
| **Swiss Modern** | Bauhaus-inspired, black/white/red, Archivo + Nunito |
| **Bold Signal** | Dark theme, vibrant accent, Archivo Black + Space Grotesk |
| **Neon Cyber** | Deep blue base, neon glow, Clash Display + Satoshi |

## Project Structure

```
.
├── main.py                     # CLI entry point
├── models/                     # Pydantic models
│   ├── _enums.py               # shared enums
│   ├── blackboard.py           # zone record types
│   └── state.py                # LangGraph State
├── blackboard/                 # store, reducers, retraction cascade
├── orchestrator/               # Scheduler / Judge / Meta + rule layer
├── agents/                     # 7 execution agents
├── graph/                      # StateGraph topology + conditional routing
├── llm/                        # DeepSeek client, JSON retry, degradation logger, prompt loader
├── search/                     # Serper wrapper, query generator
├── frontend/                   # Flask + SSE + slide generator
├── docs/
│   ├── PRD.md                  # full product/architecture spec
│   └── prompts/                # versioned agent prompts (YAML frontmatter)
└── tests/
    ├── unit/                   # mirrors source structure; fast
    └── e2e/                    # real-API tests, marked @pytest.mark.e2e
```

## Acknowledgments

The interactive HTML slide presentation is inspired by [frontend-slides](https://github.com/zarazhangrui/frontend-slides).

---

<a name="chinese"></a>
# 中文

<p align="center">
  <b>张力式分析。不是共性堆叠。</b>
  <br><br>
  <a href="#english">English</a> ·
  <a href="#快速开始">快速开始</a> ·
  <a href="#架构">架构</a> ·
  <a href="#不变量">不变量</a> ·
  <a href="#输出格式">输出</a>
</p>

---

Unveiling（"揭示"）是一个基于 **LangGraph** 的多 Agent 类比分析系统。你带着驱动问题来，系统通过抽象概念透镜在时间与领域两个维度上展开探索，最终产出**张力式结论**——核心发现、核心冲突、边界条件、未解之问——而不是把分歧抹平的"折中型摘要"。

整个系统是一个状态机：**六分区黑板** + **问题树驱动调度** + **Orchestrator 三角色**（Scheduler / Judge / Meta）+ **三期生命周期**（启动 → 探索 → 收敛）。

## 为什么做 Unveiling？

大多数 AI 分析工具最终都收敛到"听起来合理的共识"。Unveiling 围绕两个相反方向的设计抉择展开：

- **张力是洞察的最小单元。** 每个结论必须命名一个真实冲突，给出该结论成立 / 失效的边界条件，并明确列出仍未解决的问题。"既有优点也有缺点"不算张力。
- **可证伪是硬性要求。** 每条预判必须携带 `killer_evidence` 字段——能够推翻它的那个具体观察。没有 kill 条件的预判会被丢弃。

底层支撑：只增不删的黑板与级联撤回、永远不原地修改的透镜版本链、强制诚实收敛的 token 预算硬上限。

<a name="架构"></a>
## 架构

```
                        ┌─── 启动 ─── 探索 ─── 收敛 ───┐
                        │      （三期生命周期）         │
                        ▼                              ▼
   驱动问题  →   问题树（调度的唯一界面）   →   张力式结论

       Orchestrator（控制层）:  Scheduler ─ Judge ─ Meta
                                    │       │       │
                            ┌───────┼───────┼───────┼───────┐
                            ▼       ▼       ▼       ▼       ▼
       执行 Agent:  inception  search  deepdig  lens_op  debate  prediction_check  convergence
                            │       │       │       │           │
                            └───────┴───┬───┴───────┴───────────┘
                                        ▼
                  六分区黑板（只增不删，状态仅 committed / retracted）
                  ├─ issue_tree         （认知层）
                  ├─ hypothesis_zone    （透镜、预判）
                  ├─ evidence_zone      （含 6 元数据的发现）
                  ├─ debate_zone        （质疑—回应回合）
                  ├─ conclusion_zone    （张力式记录）
                  └─ schedule_log       （Orchestrator 决策、降级事件）
```

### 三层架构

| 层级 | 模块 | 职责 |
|------|------|------|
| **认知层** | `issue_tree` 分区 | 子问题地图。Scheduler 决策时唯一会读的输入。 |
| **控制层** | `orchestrator/` | Scheduler 决定下一步；Judge 决定子问题是否闭合；Meta 决定是否回修。 |
| **执行层** | `agents/` | 真正调用 LLM 和搜索的 7 个 Agent。永远不决定下一步做什么。 |

### 7 个执行 Agent

| Agent | 职责 |
|-------|------|
| **inception** | 澄清驱动问题，搭建初始 MECE 问题树，铸造 2–3 个脚手架透镜，给出带 `killer_evidence` 的可证伪预判。 |
| **search** | 跨透镜的近搜索 / 远搜索 / killer_evidence 搜索（横向 = 跨领域，纵向 = 跨时期）。 |
| **deepdig** | 深挖证据；强制跨层规则（同层 ≤2 步，必须尝试爬升 现象 → 机制 → 结构）。 |
| **lens_op** | 生成 / 修正 / 分裂 / 合并透镜。永远新增版本，绝不原地修改。 |
| **debate** | 针对已提交的证据和结论进行质疑—回应。 |
| **prediction_check** | 主动寻找每条预判的 `killer_evidence`，标记 `supported` / `refuted` / `modified`。 |
| **convergence** | 把所有挺过审查的内容合成为最终的张力式输出。 |

### Orchestrator 三角色

- **Scheduler** —— 基于问题树，决定下一个 Agent、目标子问题和远近偏好。规则优先，LLM 只用于难分胜负的情况。
- **Judge** —— 决定某个子问题是否达到 minimum viable answer。硬规则：没有结构层或机制层证据 → 不能闭合。
- **Meta** —— 周期性运行；决定框架本身是否需要修订（新增透镜？重构问题树？放弃卡住的子问题？）。默认保守。

每个 Orchestrator LLM 调用都有规则兜底；每次失败都作为降级事件写入 `schedule_log`（不变量 #9）。

<a name="不变量"></a>
## 关键不变量

系统强制执行 10 条不变量。每一条都在测试中可机械验证；违反任何一条都会破坏设计：

1. 问题树是调度的唯一界面。
2. 认知层 / 执行层 / 控制层严格分离。
3. 黑板记录只有 `committed` 和 `retracted` 两态——没有 draft。
4. 证据区、辩论区、调度日志区只增不删——永远不允许物理删除。
5. 每条证据必须携带 6 元数据（`source_lens_id`、`source_lens_version`、`sub_question_id`、`layer`、`confidence`、`is_unexpected`）。
6. 透镜操作只能新增版本；版本链不可篡改。
7. 每条预判必须有 `killer_evidence` 字段。无例外。
8. 深挖遵守跨层规则：同层 ≤2 步；必须尝试跨层；"止于 X 层"是合法结果。
9. 每个 Orchestrator LLM 调用都有规则兜底，并在失败时记录降级事件。
10. Token 预算硬上限是最后的刹车——触顶时强制收敛，未完成子问题在输出中显式标记。

详见 `CLAUDE.md`（代码层约定）和 `docs/PRD.md`（完整设计哲学）。

## 技术栈

- **框架**: LangGraph（StateGraph + Checkpoint）
- **LLM**: DeepSeek（OpenAI-compatible API；默认 `deepseek-chat`，关键判断点可选 `deepseek-reasoner`）
- **搜索**: Serper API（Google Search 代理，`tenacity` 重试）
- **数据模型**: Pydantic v2（`strict=True`、`extra="forbid"`）
- **Web**: Flask + SSE
- **前端**: 原生 HTML/CSS/JS

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
# 最小用法
python main.py "AI 公司现在应不应该烧钱扩张？"

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
# 快速套件（181 个单元测试）
pytest

# 真实 API 端到端测试（小预算）
pytest -m e2e
```

<a name="输出格式"></a>
## 输出格式

结论是结构化的**张力记录**，而不是共性列表：

| 字段 | 含义 |
|------|------|
| `convergent_finding` | 经过所有质疑回合幸存的最稳健发现。 |
| `tension` | 本次分析揭示的核心冲突（真实冲突——不是"既有优点也有缺点"）。 |
| `boundary_condition` | 该发现成立 / 失效的具体、可检验的条件。 |
| `unresolved` | 仍然真正不确定的部分。永远不为空——任何诚实的分析都会留有余地。 |
| `implication` | 这对原始驱动问题意味着什么。 |

每次运行都会附带一份**分析诚信度摘要**：闭合 / 卡住的子问题数、降级事件计数、透镜演化深度、未完成分支等。

## 幻灯片风格

CLI 输出的 HTML 幻灯片（由 `frontend/slides/` 生成）支持三种预设：

| 风格 | 描述 |
|------|------|
| **Swiss Modern** | 包豪斯风格，黑/白/红，Archivo + Nunito |
| **Bold Signal** | 深色主题，鲜艳强调色，Archivo Black + Space Grotesk |
| **Neon Cyber** | 深海蓝底色，霓虹辉光，Clash Display + Satoshi |

## 项目结构

```
.
├── main.py                     # CLI 入口
├── models/                     # Pydantic 模型
│   ├── _enums.py               # 共享枚举
│   ├── blackboard.py           # 六分区记录类型
│   └── state.py                # LangGraph State
├── blackboard/                 # store、reducer、撤回级联
├── orchestrator/               # Scheduler / Judge / Meta + 规则层
├── agents/                     # 7 个执行 Agent
├── graph/                      # StateGraph 拓扑 + 条件路由
├── llm/                        # DeepSeek 客户端、JSON 重试、降级日志、提示加载
├── search/                     # Serper 封装、查询生成
├── frontend/                   # Flask + SSE + 幻灯片生成
├── docs/
│   ├── PRD.md                  # 完整产品 / 架构说明书
│   └── prompts/                # 版本化 Agent 提示词（YAML frontmatter）
└── tests/
    ├── unit/                   # 镜像源代码结构；快速
    └── e2e/                    # 真实 API 测试，标记 @pytest.mark.e2e
```

## 致谢

交互式 HTML 幻灯片演示的设计灵感来源于 [frontend-slides](https://github.com/zarazhangrui/frontend-slides)。

## License

MIT
