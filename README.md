<a name="english"></a>
# Unveiling

<p align="center">
  <b>See the invisible patterns. Understand anything through analogy.</b>
  <br><br>
  <a href="#quick-start">Quick Start</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="#data-flow-example">Demo</a> ·
  <a href="#chinese">中文</a>
</p>

---

Unveiling is a multi-agent analogy analysis system. Given any topic, it deploys a crew of specialized AI agents that collaboratively analyze the topic through **horizontal** (cross-domain) and **vertical** (cross-era) analogies — producing a structured insight report and an interactive HTML slide deck.

Instead of surface-level summaries, Unveiling reasons like a polymath: abstracting the topic into universal conceptual "lenses," searching for analogous instances across time and domains, comparing them rigorously, validating causal chains, and synthesizing cross-dimensional insights that no single perspective could produce alone.

## Why Unveiling?

Most AI analysis tools give you a flat summary. Unveiling gives you **depth through structure**:

- **Abstraction-first**: It doesn't search blindly. It first distills your topic into 2–3 universal conceptual lenses, then uses those lenses to guide discovery.
- **Cross-dimensional**: Every insight is forced to draw evidence from *both* historical patterns (vertical) and contemporary cross-domain analogies (horizontal).
- **Causally validated**: A dedicated skeptic agent challenges every similarity with three tests — causal chain, confounding variable, and counterfactual.
- **Agent collaboration**: Vertical and Horizontal discovery agents don't work in isolation. They debate on a shared blackboard, refining each other's findings through multi-round discussion.

<a name="architecture"></a>
## Architecture

```
Topic → [Abstracter] → 2-3 Abstract Lenses
                ↓
       ┌────────┴────────┐
       ↓                 ↓
[Vertical Discovery] [Horizontal Discovery]  ← Blackboard Cross-Fertilization
  Across Time           Across Domains
       ↓                 ↓
       └────────┬────────┘
                ↓
          [Comparator] → Pairwise Comparisons
                ↓
        [Causal Reviewer] → Reject Spurious Correlations
                ↓
          [Synthesizer] → Cross-Dimensional Insights
                ↓
        [Visualization] → HTML Slide Deck
```

### The 7 Agents

| Agent | Role | Tools |
|-------|------|-------|
| **Abstracter** | Distills topic into universal conceptual lenses | Pure reasoning |
| **Vertical Discovery** | Searches historical analogs for each lens | Web Search + Blackboard |
| **Horizontal Discovery** | Searches cross-domain analogs for each lens | Web Search + Blackboard |
| **Comparator** | Pairwise comparison: topic vs. each discovered instance | Pure reasoning |
| **Causal Reviewer** | Three-test causal validation of every commonality | Pure reasoning |
| **Synthesizer** | Cross-references vertical & horizontal evidence into unified insights | Pure reasoning |
| **Visualization** | Generates the final HTML slide presentation | SlideGeneratorTool |

### Key Mechanisms

- **Hypothesis-driven discovery**: Lenses guide search, preventing the "throw spaghetti at the wall" problem of open-ended research.
- **Blackboard collaboration**: Vertical and Horizontal agents read and write to a shared blackboard, enabling real-time cross-fertilization of ideas.
- **Brainstorm Room**: After initial lens generation, Vertical and Horizontal agents enter a multi-round discussion (like human experts in a meeting room), with the Abstracter on-call to refine concepts when needed.
- **Causal rigor**: The Causal Reviewer applies (1) traceable causal chain, (2) confounding variable, and (3) counterfactual tests.
- **Cross-dimensional synthesis**: Every insight must explicitly cite *both* vertical and horizontal evidence.

## Tech Stack

- **LLM**: DeepSeek (OpenAI-compatible API)
- **Agent Framework**: CrewAI (ReAct mode)
- **Search**: Serper API (Google Search proxy)
- **Web**: Flask + SSE (Server-Sent Events for real-time progress)
- **Frontend**: Vanilla HTML/CSS/JS
- **Data Models**: Pydantic v2

<a name="quick-start"></a>
## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env`:

```
OPENAI_API_KEY="your-deepseek-api-key"
OPENAI_API_BASE="https://api.deepseek.com"
OPENAI_MODEL_NAME="deepseek-v4-flash"
SERPER_API_KEY="your-serper-api-key"
```

- [DeepSeek API Key](https://platform.deepseek.com)
- [Serper API Key](https://serper.dev)

### 3. Run

**CLI mode:**
```bash
python main.py "AI"
python main.py "short video industry"
python main.py "electric vehicle market"
```

**Web mode:**
```bash
python app.py
# Open http://localhost:5001 in your browser
```

<a name="data-flow-example"></a>
## Data Flow Example

Input: **"AI"**

1. **Abstracter** generates 3 lenses:
   - "Era-defining frontier tool"
   - "Automation of cognitive labor"
   - "Scalable delegation of judgment"

2. **Vertical Discovery** finds historical instances:
   - Cuneiform (3200 BCE), abacus, printing press, double-entry bookkeeping, imperial examination, Taylorism

3. **Horizontal Discovery** finds cross-domain instances:
   - CRISPR (medicine), blockchain (finance), reusable rockets (aerospace), weather AI (meteorology), sports analytics, credit scoring

4. **Comparator** completes 15 pairwise comparisons

5. **Causal Reviewer** validates or rejects each commonality with causal scrutiny

6. **Synthesizer** produces 4 cross-dimensional insights + core thesis + prediction + recommendations

7. **Visualization** outputs an 11-page interactive HTML slide deck

## Slide Styles

| Style | Description |
|-------|-------------|
| **Swiss Modern** | Bauhaus-inspired, black/white/red, Archivo + Nunito |
| **Bold Signal** | Dark theme, vibrant accent, Archivo Black + Space Grotesk |
| **Neon Cyber** | Deep blue base, neon glow, Clash Display + Satoshi |

---

<a name="chinese"></a>
# 中文

<p align="center">
  <b>看见隐藏的模式。通过类比理解一切。</b>
  <br><br>
  <a href="#english">English</a> ·
  <a href="#快速开始">快速开始</a> ·
  <a href="#架构">架构</a> ·
  <a href="#数据流示例">演示</a>
</p>

---

Unveiling（"揭示"）是一个多 Agent 类比分析系统。输入任意主题，它会部署一组专业 AI Agent，通过**横向**（跨领域）和**纵向**（跨时期）两个维度的类比搜索，协作生成结构化洞察报告和交互式 HTML 幻灯片。

与表面摘要不同，Unveiling 像博学家一样思考：先将主题抽象为通用概念"透镜"，再跨越时间和领域搜索类比实例，逐一对比、验证因果链条，最终合成单维视角无法产生的跨维度洞察。

## 为什么做 Unveiling？

大多数 AI 分析工具给出的是平面摘要。Unveiling 通过**结构化推理**提供深度：

- **抽象先行**：不盲目搜索。先将主题提炼为 2–3 个通用概念透镜，再用透镜指导发现。
- **跨维度强制交叉**：每个洞察必须同时引用*纵向*历史证据和*横向*跨领域证据。
- **因果验证**：专职的质疑 Agent 用三重检验挑战每个共性——因果链条、混淆变量、反事实。
- **Agent 协作**：纵向和横向发现 Agent 不在真空中工作。它们在共享讨论板上辩论，通过多轮讨论相互激发。

<a name="架构"></a>
## 架构

```
主题 → [Abstracter] → 2-3 个抽象透镜
              ↓
     ┌────────┴────────┐
     ↓                 ↓
[Vertical Discovery] [Horizontal Discovery]  ← 黑板交叉激发
  穿越时间              穿越领域
     ↓                 ↓
     └────────┬────────┘
              ↓
        [Comparator] → 逐个配对对比
              ↓
      [Causal Reviewer] → 剔除伪相关
              ↓
        [Synthesizer] → 横纵交叉综合洞察
              ↓
      [Visualization] → HTML 幻灯片
```

### 7 个 Agent

| Agent | 职责 | 工具 |
|-------|------|------|
| **Abstracter** | 将主题抽象为通用概念透镜 | 纯推理 |
| **Vertical Discovery** | 为每个透镜搜索历史类比实例 | 网络搜索 + 黑板 |
| **Horizontal Discovery** | 为每个透镜搜索跨领域类比实例 | 网络搜索 + 黑板 |
| **Comparator** | 主题与每个实例逐一配对对比 | 纯推理 |
| **Causal Reviewer** | 对每个共性进行三重因果检验 | 纯推理 |
| **Synthesizer** | 交叉引用纵向与横向证据，生成综合洞察 | 纯推理 |
| **Visualization** | 生成最终 HTML 幻灯片演示 | SlideGeneratorTool |

### 核心机制

- **假设驱动发现**：透镜指导搜索，避免开放式研究的"撒网捞鱼"问题。
- **黑板协作**：纵向和横向 Agent 读写共享讨论板，实现想法的实时交叉激发。
- **头脑风暴室**：初始透镜生成后，纵向和横向 Agent 进入多轮讨论（如同人类专家在会议室），Abstracter 随时待命精炼概念。
- **因果严格性**：Causal Reviewer 应用（1）可追溯因果链、（2）混淆变量、（3）反事实三重检验。
- **跨维度综合**：每个洞察必须显式引用*纵向*和*横向*两方面证据。

## 技术栈

- **LLM**: DeepSeek（OpenAI-compatible API）
- **Agent 框架**: CrewAI（ReAct 模式）
- **搜索**: Serper API（Google Search 代理）
- **Web**: Flask + SSE（Server-Sent Events 实时进度）
- **前端**: 原生 HTML/CSS/JS
- **数据模型**: Pydantic v2

<a name="快速开始"></a>
## 快速开始

### 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `.env`：

```
OPENAI_API_KEY="your-deepseek-api-key"
OPENAI_API_BASE="https://api.deepseek.com"
OPENAI_MODEL_NAME="deepseek-v4-flash"
SERPER_API_KEY="your-serper-api-key"
```

- [DeepSeek API Key](https://platform.deepseek.com)
- [Serper API Key](https://serper.dev)

### 3. 运行

**命令行模式：**
```bash
python main.py "AI"
python main.py "短视频行业"
python main.py "电动车市场"
```

**Web 模式：**
```bash
python app.py
# 浏览器打开 http://localhost:5001
```

<a name="数据流示例"></a>
## 数据流示例

输入：**"AI"**

1. **Abstracter** 生成 3 个透镜：
   - "定义时代的前沿工具"
   - "认知劳动的自动化"
   - "可扩展的判断委托"

2. **Vertical Discovery** 发现历史实例：
   - 楔形文字（公元前 3200 年）、算盘、印刷术、复式记账、科举、泰勒制

3. **Horizontal Discovery** 发现跨领域实例：
   - CRISPR（医学）、区块链（金融）、可回收火箭（航天）、天气 AI（气象）、体育分析、信用评分

4. **Comparator** 完成 15 组配对对比

5. **Causal Reviewer** 用因果审查逐一验证或剔除共性

6. **Synthesizer** 产出 4 个跨维度洞察 + 核心论点 + 预测 + 建议

7. **Visualization** 输出 11 页交互式 HTML 幻灯片

## 幻灯片风格

| 风格 | 描述 |
|------|------|
| **Swiss Modern** | 包豪斯风格，黑/白/红，Archivo + Nunito |
| **Bold Signal** | 深色主题，鲜艳强调色，Archivo Black + Space Grotesk |
| **Neon Cyber** | 深海蓝底色，霓虹辉光，Clash Display + Satoshi |

## 项目结构

```
.
├── main.py                 # CLI 入口
├── app.py                  # Flask Web 入口（端口 5001）
├── crew.py                 # CrewAI Agent 编排
├── brainstorm.py           # 多轮头脑风暴室
├── requirements.txt
├── .env                    # API 密钥配置
├── config/
│   ├── agents.yaml         # 7 个 Agent 角色定义
│   └── tasks.yaml          # 7 个 Task 定义（含 prompt）
├── models/
│   └── schemas.py          # Pydantic 数据模型
├── tools/
│   ├── search_tool.py      # Serper API 搜索
│   ├── blackboard_tool.py  # 黑板读写工具
│   ├── shared_blackboard.py # 线程安全共享黑板
│   └── slide_generator.py  # HTML 幻灯片生成
├── templates/
│   └── index.html          # Web 前端
├── static/
│   ├── css/style.css
│   └── js/app.js           # SSE 实时进度
└── output/                 # 生成的 HTML 幻灯片
```

## License

MIT
