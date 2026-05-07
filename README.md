# Spatio-Temporal Analogy Analysis

基于 CrewAI 的多 Agent 时空类比分析系统。接收任意主题（名词/动词），通过横向（跨领域）和纵向（跨时期）两个维度的类比搜索，生成深度分析报告和交互式 HTML 幻灯片。

## 架构

```
Topic → [Abstracter] → 2-3 抽象透镜
                ↓
       ┌────────┴────────┐
       ↓                 ↓
[Vertical Discovery] [Horizontal Discovery]  ← Blackboard 交叉激发
  穿越时间              穿越领域
       ↓                 ↓
       └────────┬────────┘
                ↓
          [Comparator] → 逐个配对对比
                ↓
        [Causal Reviewer] → 剔除伪相关
                ↓
          [Synthesizer] → 横纵交叉整合
                ↓
        [Visualization] → HTML 幻灯片
```

### 7 个 Agent

| Agent | 职责 | 工具 |
|-------|------|------|
| **Abstracter** | 将 topic 抽象为 2-3 个通用概念（"透镜"） | 无（纯推理） |
| **Vertical Discovery** | 用透镜搜索历史同类实例 | Serper API + Blackboard |
| **Horizontal Discovery** | 用透镜搜索跨领域同类实例 | Serper API + Blackboard |
| **Comparator** | 将 topic 与每个实例配对对比，提取共性与特性 | 无 |
| **Causal Reviewer** | 三重因果检验，剔除伪相关 | 无 |
| **Synthesizer** | 交叉整合横纵证据，生成核心论点与预测 | 无 |
| **Visualization** | 调用 slide_generator 生成 HTML 幻灯片 | SlideGeneratorTool |

### 关键机制

- **假设驱动**：Abstracter 先生成抽象透镜，再用透镜指导搜索，避免盲目搜索
- **黑板协作**：Vertical/Horizontal Discovery Agent 通过共享黑板交叉激发灵感
- **因果审查**：Causal Reviewer 通过因果链条、混淆变量、反事实三重检验剔除伪相关
- **横纵交叉综合**：Synthesizer 要求每个洞察同时引用纵向和横向证据

## 技术栈

- **LLM**: DeepSeek (via OpenAI-compatible API)
- **Agent 框架**: CrewAI (ReAct 模式)
- **搜索**: Serper API (Google Search proxy)
- **Web 框架**: Flask + SSE (Server-Sent Events)
- **前端**: 原生 HTML/CSS/JS
- **数据模型**: Pydantic v2

## 项目结构

```
SpatioTemporalAnalysis/
├── main.py                     # CLI 入口
├── app.py                      # Flask Web 入口 (port 5001)
├── crew.py                     # CrewAI Crew 编排
├── requirements.txt
├── .env                        # API 密钥配置
├── config/
│   ├── agents.yaml             # 7 个 Agent 角色定义
│   └── tasks.yaml              # 7 个 Task 定义（含 prompt）
├── models/
│   └── schemas.py              # Pydantic 数据模型（12 个）
├── tools/
│   ├── search_tool.py          # Serper API 网络搜索工具
│   ├── blackboard.py           # 共享黑板工具
│   └── slide_generator.py      # HTML 幻灯片生成工具
├── templates/
│   └── index.html              # Web 前端页面
├── static/
│   ├── css/style.css
│   └── js/app.js               # SSE 实时进度 + 结果展示
├── skills/
│   └── frontend-slides/        # 幻灯片样式框架
│       ├── viewport-base.css
│       ├── STYLE_PRESETS.md
│       └── templates/
└── output/                     # 生成的 HTML 幻灯片
```

## 快速开始

### 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `.env` 文件：

```
OPENAI_API_KEY="your-deepseek-api-key"
OPENAI_API_BASE="https://api.deepseek.com"
OPENAI_MODEL_NAME="deepseek-v4-flash"
SERPER_API_KEY="your-serper-api-key"
```

- DeepSeek API Key: https://platform.deepseek.com
- Serper API Key: https://serper.dev

### 3. 运行

**CLI 模式：**
```bash
python main.py "AI"
python main.py "短视频"
python main.py "电动车市场"
```

**Web 模式：**
```bash
python app.py
# 浏览器打开 http://localhost:5001
```

## 数据流示例

以 "AI" 为输入：

1. **Abstracter** 生成 3 个透镜：
   - "复杂性的时代抽象工具"
   - "隐性知识的可操作化"
   - "可扩展的判断委托"

2. **Vertical Discovery** 发现历史实例：
   - 楔形文字 (3200 BCE)、算盘、印刷术、复式记账、科举、泰勒制

3. **Horizontal Discovery** 发现跨领域实例：
   - CRISPR、区块链、可回收火箭、天气 AI、体育分析、信用评分

4. **Comparator** 完成 15 组配对比较

5. **Causal Reviewer** 逐个审查共性的因果有效性

6. **Synthesizer** 生成 4 个横纵交叉洞察 + 核心论点 + 预测 + 建议

7. **Visualization** 输出 11 页交互式 HTML 幻灯片

## 幻灯片风格

| 风格 | 特点 |
|------|------|
| Swiss Modern | Bauhaus 风格，黑/白/红，Archivo+Nunito 字体 |
| Bold Signal | 深色主题，鲜艳点缀，Archivo Black+Space Grotesk |
| Neon Cyber | 深蓝底色，霓虹辉光，Clash Display+Satoshi |

## 已知问题

- **Causal Reviewer 过于严格**：当横向发现的实例本身是 AI 的子类应用时，审查员会认为共性不独立。可通过改进横向搜索策略来缓解。
- **DeepSeek 不支持 `output_pydantic`**：已移除结构化输出，Agent 输出为自由格式 JSON。
- **macOS AirPlay 占用 5000 端口**：Web 模式默认使用 5001 端口。

## License

MIT
