# CLAUDE.md

## 项目定位

Unveiling 是一个多 Agent 类比分析系统：用户带着问题来，系统通过横向（跨领域）/纵向（跨时期）类比 + 结构性抽象，产出张力式洞察（不是共性堆叠）。

技术上是一个 LangGraph 编排的三阶段管线：抽象 → 搜集 → 收拢。四分区黑板 + 并行搜索协作。

## 文档导航

- `docs/PRD.md` —— 完整的哲学、架构、流程、前端设计。做设计决策时必读。
- `docs/prompts/` —— Agent 系统提示词（实施中持续打磨）。
- 本文件 —— 代码层面的约束、约定、易错点。

遇到 PRD 和 CLAUDE.md 冲突时，以 PRD 为准，并在本文件提 issue 修正。

## 三阶段设计

```
阶段一：抽象                    阶段二：搜集                阶段三：收拢
──────────────               ──────────────              ──────────────
输入：用户问题                  输入：抽象概念               输入：~20 个案例
识别主体/关系                   横向搜索 ←→ 纵向搜索        跨案例归纳共性
抽象到结构层                    （并行，黑板协作）           发现张力
                              各找 10 个或超时             质疑检验
输出：初始透镜                  输出：证据区积累的案例       组织结论
```

## 代码结构

```
unveiling/
├── main.py                  # CLI 入口
├── models/                  # Pydantic 数据模型
│   ├── _enums.py            # 共享枚举（RecordStatus / EvidenceLayer / Phase / ...）
│   ├── blackboard.py        # 黑板记录基类 + 分区记录类型（LensRecord / EvidenceRecord / ConclusionRecord / ScheduleLogEntry）
│   └── state.py             # LangGraph State（四分区 + 搜索覆盖计数器）
├── blackboard/              # 黑板读写、撤回级联
│   ├── reducers.py          # merge_lists / merge_dicts / replace
│   ├── store.py             # 黑板增删改查
│   └── retraction.py        # 撤回引发的级联失效
├── orchestrator/            # Orchestrator
│   ├── scheduler.py         # 阶段二搜索调度（覆盖率跟踪 + 超时判断）
│   └── rules.py             # 规则层（不调 LLM 的决策）
├── agents/                  # 执行层
│   ├── inception.py         # 阶段一：抽象（识别主体/关系 → 结构层抽象）
│   ├── search.py            # 阶段二：横向/纵向搜索（并行）
│   └── convergence.py       # 阶段三：收拢（归纳→张力→质疑→结论）
├── graph/                   # LangGraph 编排
│   ├── build.py             # StateGraph 构建
│   └── routing.py           # 条件路由函数
├── llm/                     # LLM 调用封装
│   ├── client.py            # DeepSeek 客户端 + JSON 重试 + token 计数
│   ├── abstraction.py       # 抽象原语（贯穿全流程的认知工具）
│   ├── degradation.py       # 失败降级
│   └── prompt_loader.py     # 从 docs/prompts/ 加载
├── search/                  # 搜索工具
│   ├── serper.py            # Serper API（tenacity 重试）
│   └── query_gen.py         # 查询生成
├── frontend/                # Flask + SSE + 原生 HTML
│   ├── app.py               # Flask 入口
│   ├── slides/              # HTML 幻灯片生成器
│   ├── static/              # 静态资源
│   └── templates/           # 页面模板
├── docs/
│   ├── PRD.md               # 完整 PRD
│   └── prompts/             # Agent 系统提示词
└── tests/
    ├── unit/                # 单元测试
    └── integration/         # 集成测试
```

注：顶层为平铺包结构（不是 `unveiling/` 子包）。

## 关键不变量（违反即破坏设计）

1. 三阶段职责不重叠。
   抽象不试图发现深层机制（信息不足），搜集不试图收拢结论（证据不全），收拢不回头重新搜索（预算有限）。
2. 认知层 / 执行层 / 控制层三分。
   执行层（agents/）不做调度决策。Orchestrator（orchestrator/）不直接生成内容。如果一个 agent 里出现"决定下一步调用什么"的逻辑，需要重构。
3. 黑板状态只有 committed 和 retracted 两级。
   不要引入 draft 状态。Agent 内部的中间推敲不暴露到黑板。
4. 黑板"只增不删"的分区不能删记录。
   证据区、调度日志区只允许 append 和 retract，永远不允许物理删除。
5. 每条证据必须带完整元数据。
   `source_lens_id`、`search_direction`（lateral/vertical）、`layer`、`confidence` 一个都不能缺。
6. 透镜演化只能"加新版本"，不能"原地改"。
   修正/分裂/合并都是创建新 LensRecord，`parent_lens_id` 指向前一版本。版本链不可篡改。
7. LLM 失败必须降级，不能让系统终止。
   每个 LLM 调用点都需要降级路径，并在调度日志区记录降级事件。
8. 阶段二搜索不嵌入额外抽象。
   搜索直接用阶段一产出的抽象概念构造搜索词，LLM 正常处理结果判断结构匹配度。抽象只在例外情况（意外发现）使用。
9. 阶段二横向和纵向并行，黑板协作。
   不是串行轮转，是并行搜索 + 分批提交黑板 + 互相参考。

## 数据模型核心约定

### 状态枚举（所有代码统一用英文）

```python
# BlackboardRecord.status
"committed" | "retracted"

# Evidence.layer
"phenomenon" | "mechanism" | "structure"

# Evidence.confidence
"strong" | "medium" | "weak" | "unexpected"

# Evidence.search_direction
"lateral" | "vertical"

# Phase
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

### 透镜记录

`LensRecord` 承载阶段一的抽象结果，包含：

- `name: str` — 透镜名称
- `rationale: str` — 为什么这个透镜成立
- `entities: list[AbstractedEntity]` — 各主体的结构角色
  - `surface: str` — 原始术语（如 "AI"）
  - `structural_role: str` — 抽象后的结构角色
- `relationships: list[AbstractedRelation]` — 关系的结构模式
  - `surface: str` — 原始关系描述
  - `structural: str` — 抽象后的结构关系
- `parent_lens_id: str | None` — 版本链

### LangGraph State

```python
class State(BaseModel):
    # 四分区黑板
    hypothesis_zone: list[LensRecord]       # 透镜版本链
    evidence_zone: list[EvidenceRecord]     # 搜索证据
    conclusion_zone: list[ConclusionRecord] # 最终结论
    schedule_log: list[ScheduleLogEntry]    # 调度日志

    # 搜索覆盖（阶段二用）
    lateral_count: int    # 横向已找到几个
    vertical_count: int   # 纵向已找到几个

    # Orchestrator 内部
    token_spent: int
    phase: Phase

    # 用户输入
    user_question: str
    output_language: str  # "中文" | "English"
```

State 更新通过 reducer 合并，不要在节点里直接 mutate。

## 常见任务的标准做法

### 添加一个新执行 Agent

1. 在 `agents/` 下新建模块
2. 实现签名为 `(state: State) -> dict` 的函数
3. 在 `graph/build.py` 注册为节点
4. 在 `graph/routing.py` 决定路由
5. 不要让这个 Agent 自己决定下一步

### 添加一个新的失败降级策略

1. 在 `llm/degradation.py` 添加降级函数
2. 在调用 LLM 的位置用 try/except 接入
3. 降级时必须在调度日志区写入降级事件
4. 降级事件参与最终输出的"分析诚信度摘要"

## 易错点

### 1. 不要把搜索结果当成可信知识

`search/serper.py` 返回的是 Google 搜索结果——会有 SEO 污染、流行话题偏向、对冷门历史覆盖差。

- 搜索结果必须经过 LLM 二次提取和结构化，不能直接当证据
- 当多次搜索仍只返回现成类比时，标注低置信度，不要硬塞

### 2. 不要让 Orchestrator 自己执行任务

Orchestrator 只决策，不执行。如果在 `orchestrator/` 下出现"调 Serper API"、"生成透镜"这类代码，是错的。

### 3. 不要在节点函数里 mutate state

LangGraph 节点函数应该返回 dict 表示 State 更新，由框架合并。直接修改传入的 state 对象会导致并行分支的状态污染。

### 4. 不要为了"看起来更好"而隐藏信息

"搜不到足够案例"或"收敛失败"是合法的出口。最终输出必须明确标注，不要包装成完美结果。

### 5. 不要混淆 retract 和 delete

记录被撤回时：`status = "retracted"`，`retraction_reason` 填原因，记录本身保留。

### 6. 模型名注意

`OPENAI_MODEL_NAME` 在 `.env` 里。DeepSeek 当前可用的型号是 `deepseek-chat`（默认）和 `deepseek-reasoner`（关键判断点可选）。不要写不存在的型号。

## 开发工作流

### 安装与运行

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 配置 .env（OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_MODEL_NAME, SERPER_API_KEY）

# CLI
python main.py "AI 时代人们的 AI 焦虑"

# Web
python app.py       # http://localhost:5001
```

### 验证写对了

提交前确认：

- 三阶段职责不重叠
- 新增的状态字段是否在枚举里
- 新增的 LLM 调用是否有降级路径
- 测试覆盖：至少有一个测试覆盖正常路径，一个覆盖 LLM 失败路径

## 当前实施状态

### MVP 范围

- ✅ 三阶段管线（抽象 → 搜集 → 收拢）
- ✅ 四分区黑板
- ✅ 并行横向（当代跨领域）+ 纵向（跨时期）搜索
- ✅ 搜索前 LLM 验证层（去重 + 方向校验）
- ✅ 独立收敛（每方向各自搜满或超时即停）
- ✅ CLI 入口 + 详细日志输出到 tmp/
- 🚧 基础 Web 展示

## 一句话原则

> 写代码时如果不确定，先回去读 PRD 对应小节，再决定怎么写。设计的所有妥协和取舍都在那里，CLAUDE.md 只是它的代码层投影。
