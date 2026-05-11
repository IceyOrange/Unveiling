# CLAUDE.md

## 项目定位

Unveiling 是一个多 Agent 类比分析系统：用户带着问题来，系统通过横向（跨领域）/纵向（跨时期）类比 + 抽象透镜，产出张力式洞察（不是共性堆叠）。

技术上是一个 LangGraph 编排的状态机：六分区黑板 + 问题树驱动 + Orchestrator 三角色（Scheduler/Judge/Meta）+ 三期生命周期（启动→探索→收敛）。

## 文档导航

- `docs/PRD.md` —— 完整的哲学、架构、流程、前端设计。做设计决策时必读。
- `docs/prompts/` —— Agent 系统提示词（实施中持续打磨）。
- 本文件 —— 代码层面的约束、约定、易错点。

遇到 PRD 和 CLAUDE.md 冲突时，以 PRD 为准，并在本文件提 issue 修正。

## 代码结构

```
unveiling/
├── main.py                  # CLI 入口
├── models/                  # Pydantic 数据模型
│   ├── _enums.py            # 共享枚举（RecordStatus / NodeStatus / Phase / ...）
│   ├── blackboard.py        # 黑板记录基类 + 六分区记录类型（IssueTreeNode / LensRecord / PredictionRecord / EvidenceRecord / DebateRecord / ConclusionRecord / ScheduleLogEntry）
│   └── state.py             # LangGraph State（六分区 + 内部计数器）
├── blackboard/              # 黑板读写、撤回级联、追溯
│   ├── reducers.py          # merge_lists / merge_dicts / replace
│   ├── store.py             # 黑板增删改查 + 依赖索引
│   └── retraction.py        # 撤回引发的级联失效（BFS over references[]）
├── orchestrator/            # 三角色 + 规则层
│   ├── scheduler.py         # 下一步做什么
│   ├── judge.py             # 子问题是否闭合
│   ├── meta.py              # 是否需要回修
│   └── rules.py             # 规则层（不调 LLM 的决策、阶段默认值）
├── agents/                  # 执行层
│   ├── inception.py         # 启动期（澄清+建树+预判）
│   ├── search.py            # 横向/纵向搜索（含近搜索/远搜索/killer_evidence）
│   ├── deepdig.py           # 深挖（带层级标签）
│   ├── lens_op.py           # 透镜生成/修正/分裂/合并
│   ├── debate.py            # 质疑—回应
│   ├── prediction_check.py  # 预判检验
│   └── convergence.py       # 收敛期（张力式输出）
├── graph/                   # LangGraph 编排
│   ├── build.py             # StateGraph 构建
│   └── routing.py           # 条件路由函数
├── llm/                     # LLM 调用封装
│   ├── client.py            # DeepSeek 客户端 + JSON 重试 + token 计数
│   ├── degradation.py       # 失败降级（写 ScheduleLogEntry，接受 OrchestratorRole 或 agent 名字符串）
│   └── prompt_loader.py     # 从 docs/prompts/{name}.md 加载并去 frontmatter
├── search/                  # 搜索工具
│   ├── serper.py            # Serper API（tenacity 重试）
│   └── query_gen.py         # 查询生成（含远搜索查询模板）
├── frontend/                # Flask + SSE + 原生 HTML
│   ├── app.py               # Flask 入口
│   ├── slides/              # HTML 幻灯片生成器（generator.py）
│   ├── static/              # CSS / JS
│   └── templates/           # index.html
├── docs/
│   ├── PRD.md               # 完整 PRD（架构、流程、前端设计）
│   └── prompts/             # Agent 系统提示词（YAML frontmatter + Markdown body）
└── tests/
    ├── unit/                # 单元测试（按源代码结构镜像，无 __init__.py 以免遮蔽源包）
    └── integration/         # 集成测试

```

注：顶层为平铺包结构（不是 `unveiling/` 子包）。`static/`、`templates/`、`tools/` 是历史 CrewAI 遗留目录，已停用，相关功能已迁至 `frontend/` 和各新模块。

## 关键不变量（违反即破坏设计）

这些约束来自 PRD 的核心设计决策。Claude 写代码时不要违反，违反时主动指出而不是默默改：

1. 问题树是 Orchestrator 调度的唯一界面。
   Scheduler 决策的起点永远是"哪个子问题最需要推进"，不是"还有什么可以挖"。任何让调度逻辑绕开问题树直接看证据的代码都是错的。
2. 认知层 / 执行层 / 控制层三分。
   执行层（agents/）不做调度决策。Orchestrator（orchestrator/）不直接生成内容。如果一个 agent 里出现"决定下一步调用什么"的逻辑，需要重构。
3. 黑板状态只有 committed 和 retracted 两级。
   不要引入 draft 状态。Agent 内部的中间推敲不暴露到黑板——任务完成才提交。
4. 黑板"只增不删"的分区不能删记录。
   证据区、辩论区、调度日志区只允许 append 和 retract（标记为 retracted），永远不允许物理删除。Retracted 记录保留追溯性。
5. 每条证据必须带完整元数据。
   `source_lens_id`, `source_lens_version`, `sub_question_id`, `layer`, `confidence`, `is_unexpected` 一个都不能缺。元数据缺失的证据视为无效。
6. 透镜演化只能"加新版本"，不能"原地改"。
   修正/分裂/合并都是创建新 Lens 记录，`parent_lens_id` 指向前一版本。版本链不可篡改。
7. 可证伪预判必须有 `killer_evidence` 字段。
   生成预判时如果 LLM 没给出 killer_evidence，需要重新生成或舍弃。"无 killer_evidence 的预判"不算预判。
8. 深挖跨层规则：同一层级最多 2 步，必须尝试跨层。跨层失败不是错误，而是结果——标记"止于 X 层"。
9. Orchestrator LLM 失败必须降级，不能让系统终止。
   每个 LLM 判断点都需要规则兜底，并在调度日志区记录降级事件。
10. Token 预算硬上限是最终兜底。
    达到预算上限时强制收敛，未闭合子问题在输出中显式标记"未完成"——不能为了"跑完"而无视预算。

## 数据模型核心约定

### 状态枚举（所有代码统一用英文）

```python
# IssueNode.status
"untouched" | "exploring" | "closed" | "stuck"

# BlackboardRecord.status
"committed" | "retracted"

# Prediction.status
"pending" | "supported" | "refuted" | "modified"

# Evidence.layer
"phenomenon" | "mechanism" | "structure"

# Evidence.confidence
"strong" | "medium" | "weak" | "unexpected"

# Phase（生命周期）
"inception" | "exploration" | "convergence"

```

### 黑板记录基类

所有黑板记录继承 `BlackboardRecord`，必有：

- `id: str`（UUID）
- `status: Literal["committed", "retracted"]`
- `author: str`（写入者，agent 名或 orchestrator 角色）
- `timestamp: datetime`
- `references: list[str]`（引用的其他记录 id）
- `retraction_reason: str | None`

### LangGraph State

State 是黑板 + Orchestrator 内部状态的并集：

- 黑板六分区作为 State 的字段（每个分区是一个 list 或 dict）
- Orchestrator 内部状态（尝试次数计数器、发现密度窗口等）作为额外字段
- State 更新通过 reducer 合并，不要在节点里直接 mutate

## 常见任务的标准做法

### 添加一个新执行 Agent

1. 在 `agents/` 下新建模块
2. 实现签名为 `(state: State) -> dict`（dict 是 State 更新）的函数
3. 在 `graph/build.py` 注册为节点
4. 在 `graph/routing.py` 决定从哪些节点能流转到它
5. 在 `orchestrator/scheduler.py` 决定何时调度它
6. 不要让这个 Agent 自己决定下一步——它的输出永远是"写一些东西到黑板"，下一步由 Scheduler 决定

### 添加一个新的失败降级策略

1. 在 `llm/degradation.py` 添加降级函数
2. 在调用 LLM 的位置用 try/except 或装饰器接入
3. 降级时必须在调度日志区写入降级事件（`author="orchestrator.{role}"`, `references=[]`, 内容描述失败场景）
4. 降级事件参与最终输出的"分析诚信度摘要"

### 添加一个新的黑板字段

1. 修改 `models/blackboard.py` 的对应记录类
2. 修改 `models/state.py` 的 State
3. 修改对应的 reducer（如果是 list/dict 的合并逻辑）
4. 检查所有写入这个分区的 Agent 是否需要更新
5. 检查 `frontend/` 是否需要展示这个新字段

## 易错点（Claude 容易写错的地方）

### 1. 不要把搜索结果当成可信知识

`search/serper.py` 返回的是 Google 搜索结果——会有 SEO 污染、流行话题偏向、对冷门历史覆盖差。这是项目最大的隐形风险（PRD"关键约束与限制"小节有详述）。

- 搜索结果必须经过 LLM 二次提取和结构化，不能直接当证据
- 远搜索的查询不要直接用问题关键词，要让 LLM 基于透镜生成"指向冷门时空角落"的查询
- 当多次搜索仍只返回现成类比时，标注 `is_unexpected=False` 和低置信度，不要硬塞

### 2. 不要让 Orchestrator 自己执行任务

Orchestrator 只决策，不执行。如果在 `orchestrator/` 下出现"调 Serper API"、"生成透镜"这类代码，是错的。这些是 `agents/` 的事。

### 3. 不要绕过问题树推进分析

错误模式：Scheduler 看到证据区有新意外发现，直接调度一个深挖任务。
正确模式：意外发现先触发问题树评估（Meta 角色），如果需要新增子问题或重构问题树，先做这件事，再调度深挖。

### 4. 不要让 Judge 在子问题相关内容过多时直接塞进 prompt

Judge / Meta 在 context 超量时应该先做摘要再判断。`orchestrator/judge.py` 应该有 token 数检查，超量时调用摘要逻辑。

### 5. 不要为了"看起来更好"而隐藏卡住的子问题

"卡住"是合法的出口状态。最终输出必须明确列出卡住的子问题和原因，不要包装成"已闭合"或"无相关发现"。

### 6. 不要混淆 retract 和 delete

记录被撤回时：`status = "retracted"`，`retraction_reason` 填原因，记录本身保留。然后调用 `blackboard/retraction.py` 的级联失效逻辑标记依赖它的下游记录。

### 7. 不要在节点函数里 mutate state

LangGraph 节点函数应该返回 dict 表示 State 更新，由框架合并。直接修改传入的 state 对象会导致并行分支的状态污染。

### 8. 模型名注意

`OPENAI_MODEL_NAME` 在 `.env` 里。DeepSeek 当前可用的型号是 `deepseek-chat`（默认）和 `deepseek-reasoner`（关键判断点可选）。不要写 `deepseek-v4-flash` 这种不存在的型号。

## 开发工作流

### 安装与运行

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 配置 .env（OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_MODEL_NAME, SERPER_API_KEY）

# CLI 基础用法
python main.py "AI 公司现在应不应该烧钱扩张？"

# CLI 完整用法
python main.py \
  --question "AI 公司现在应不应该烧钱扩张？" \
  --context "我在评估投资某 AI 初创" \
  --mode focus      # focus | balance | explore

# Web
python app.py       # http://localhost:5001
```

### 调试

- LangGraph 的 Checkpoint 默认开启，每个节点完成后状态持久化在 `.checkpoints/`
- 用 `python tools/replay.py <checkpoint_id>` 重放某个时刻的状态（如果该工具尚未实现，可以先用 LangGraph 自带的 trace 功能）
- 单个 Agent 可单独测试：`pytest tests/agents/test_search.py`

### 验证写对了

提交前确认：

-  关键不变量是否违反（特别是 1、2、3、5、6）
-  新增的状态字段是否在枚举里
-  新增的 LLM 调用是否有降级路径
-  测试覆盖：至少有一个测试覆盖正常路径，一个覆盖 LLM 失败路径

## 当前实施状态

### MVP 范围

- ✅ 完整三期生命周期（启动 → 探索 → 收敛）
- ✅ 六分区黑板 + 轮询式调度循环
- ✅ Orchestrator 三角色 + 失败降级
- ✅ CLI 入口
- 🚧 基础 Web 展示（最简版，参考 PRD"前端设计"）
- 🚧 启动期用户确认（交互模式）

### MVP 不包括（明确延后）

- ❌ 探索期/收敛期的用户中途介入 UI
- ❌ 高级可视化（透镜演化图、辩论树等）
- ❌ 多次分析对比、历史归档
- ❌ 结构化辅助数据源（仅 Serper）

### PoC 验收标准

- 至少 3 个真实主题端到端跑通
- 输出包含真实张力（不是共性堆叠）——人工评估
- 单次成本 ≤ ¥3，时间 ≤ 30 分钟
- Orchestrator LLM 调用占比 ≤ 30%

## Agent Prompt 雏形

以下是 Orchestrator 三角色和执行 Agent 的系统提示词起点。实施时根据 PoC 反馈持续打磨，最终版应该在 `docs/prompts/` 下维护。

### Scheduler

```
你是一个分析系统的调度官。你的唯一职责是：基于当前问题树状态，
决定下一步应该做什么。

输入：
- 问题树（含每个子问题的状态：untouched / exploring / closed / stuck）
- 各子问题的最近活动摘要
- 当前阶段（inception / exploration / convergence）
- 远近偏好（用户设定 + 阶段默认）

输出（JSON）：
{
  "next_agent": "search_lateral" | "search_vertical" | "deepdig" | "lens_op" | "debate" | "prediction_check",
  "target_sub_question": "<sub_question_id>",
  "near_far_ratio": <0.0 to 1.0>,
  "reason": "为什么选这个（一句话）"
}

约束：
- 你不执行任务，只决策
- 决策起点永远是"哪个子问题最需要推进"，不是"还有什么可以挖"
- 如果多个子问题优先级难分，选 attempt_count 最少的

```

### Judge

```
你是一个分析系统的裁判。你的职责是：判断某个子问题是否达到 minimum viable answer。

输入：
- 子问题描述
- 该子问题相关的全部证据、辩论、深挖记录
- 相关的可证伪预判及检验状态

minimum viable answer 的标准：
1. 至少一条结构层或机制层的发现（不能全是现象层）
2. 相关可证伪预判已被检验（killer_evidence 找到或确认未找到）
3. 在辩论区至少经历过一次质疑回合

输出（JSON）：
{
  "status": "exploring" | "closed" | "stuck",
  "reason": "判断依据（具体引用哪些证据/缺什么）",
  "missing": ["还缺什么才能闭合"] | []
}

约束：
- 不要为了"看起来完整"而判定 closed——硬性条件不满足就是 exploring
- 多次尝试仍无进展时果断判定 stuck，标注原因

```

### Meta

```
你是一个分析系统的元认知者。你的职责是：判断当前分析框架本身是否需要回修。

输入：
- 黑板全局趋势摘要（最近 N 轮发现密度、意外发现累积、透镜被挑战次数）
- 当前问题树和透镜版本链
- 卡住的子问题及原因

输出（JSON）：
{
  "needs_revision": true | false,
  "revision_type": "issue_tree_restructure" | "new_lens" | "retry_stuck_sub_question" | null,
  "reason": "为什么需要回修（具体证据）",
  "proposed_action": "具体怎么改"
}

约束：
- 回修代价高，只在真正必要时触发
- "意外发现密集积累且当前问题树无法吸纳"是回修信号
- 默认倾向于不回修（保守原则）

```

### 执行 Agent 共同约束

所有执行 Agent（search/deepdig/lens_op/debate/prediction_check）的 prompt 必须包含：

```
1. 你的输出会写入黑板，被其他 Agent 引用，写入后视为 committed
2. 任何不确定的内容应该明确标注置信度，不要伪装确定
3. 引用的证据必须可溯源（指向证据区的具体记录 id）
4. 不要决定"下一步做什么"——那是 Scheduler 的事
5. 输出格式严格遵循 Pydantic schema（见 models/）
```

------

## 一句话原则

> 写代码时如果不确定，先回去读 PRD 对应小节，再决定怎么写。设计的所有妥协和取舍都在那里，CLAUDE.md 只是它的代码层投影。