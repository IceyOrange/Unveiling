# Results Page Redesign — Design Spec

**Date:** 2026-06-17  
**Scope:** Analysis results page frontend (`src/frontend/`)  
**Status:** Approved, pending implementation plan

---

## 1. Background & Goals

The Unveiling analysis page presents a rich stream of results: a structural lens, analogical evidence plotted on a scatter chart, and six conclusion chapters. Two pain points were identified:

1. **Bento layout (conclusions grid)** — §4–6 each span only 2 of 6 columns, making them too narrow. The six chapters lack a clear editorial hierarchy; all cards feel visually equivalent despite having very different weight.
2. **Evidence display redundancy** — The `cases` live-feed list and the `scatter__cards` below the chart both render the same evidence records. Their roles overlap during analysis and after completion.

---

## 2. Design Decisions

### 2a. Bento Conclusions Layout → Option B (Editorial Style)

**Structure:**

```
┌─────────────────────────────────────────────┐
│  § 1  核心结论  (full width, elevated bg)    │
│  大字号 lead + prose, 更多内边距              │
├──────────────────────┬──────────────────────┤
│  § 2  这件事的走向   │  § 3  难处在哪        │
│  (半宽, 普通卡片)    │  (半宽, 橙色强调)     │
├───────────┬──────────┴────────┬─────────────┤
│  § 4      │  § 5              │  § 6        │
│  边界条件  │  还没回答清楚的   │  所以你应该  │
│  (注脚式, 背景 inset, 字号稍小) │            │
└───────────┴───────────────────┴─────────────┘
```

**Grid mapping:**
- `#chapter-core_finding` — `grid-column: 1 / -1`，保持全宽，`background: var(--surface-elevated)`，`padding` 增大
- `#chapter-temporal_trajectory` — `grid-column: span 3`（不变）
- `#chapter-tension` — `grid-column: span 3`（不变），强调色保留
- `#chapter-boundary_condition`、`#chapter-unresolved`、`#chapter-implication` — 改为 `grid-column: span 2`，但加以下视觉降调：
  - `font-size` 缩小 (`.conclusion__lead`: 14px, `.conclusion__para`: 13px)
  - `background: var(--surface-inset)` 或降低 border 显著性
  - `padding` 缩小至 `var(--space-4)`
  - `.conclusion__marker-no` 和 `.conclusion__marker-name` 字号降至 9px

**Rationale:** §4–6 在语义上是补充信息（边界、未解问题、建议），不应与核心发现等权。通过字号 + 背景色的双重降调，在不改变网格比例的前提下建立清晰层次。

---

### 2b. Evidence Display — Clear Role Separation

**Problem:** `cases` 列表（`.cases#cases`）和 `scatter__cards`（`#scatter-cards`）渲染相同证据，在分析完成后同时可见，造成重复。

**Decision:** 明确两者的生命周期，不合并交互。

| 组件 | 生命周期 | 职责 |
|---|---|---|
| `.cases#cases` | 分析**进行中** | 实时流：每条证据到达时追加显示，给用户「正在搜集」的感知 |
| `#scatter-cards` | 分析**完成后** | 完整列表：所有证据的可浏览归档，支持用户逐条细读 |

**Implementation status:** 此逻辑**已在 JS 中实现**，无需改动：

- `renderScatter()` (app.js:1441)：当 `plotCases.length >= 2` 时，`show(scatterSection)` + `hide(casesSection)`；证据不足时反向 fallback
- `transitionToResult()` (app.js:1167)：分析完成时给 `casesSection` 加 `is-complete` class，作为视觉收尾

本次任务只需**验证**该行为在 demo 流程中正确工作，确认 `scatter__cards` 已渲染完整证据列表后 `casesSection` 确实隐藏。**不需要写新代码。**

**Rationale:** 用户需要「所有证据的线性列表」，这是散点图无法替代的。但同时显示两者是冗余的，通过时间分工消除冗余而不损失功能。

---

## 3. Out of Scope

以下内容在本次设计中**不涉及**：
- 散点图交互（点击散点/详情面板）
- `insight-bridge` 的视觉强化
- `lens-reveal` 的展示方式
- 国际化（i18n）字符串修改
- 移动端布局调整（保持现有 `@media (max-width: 960px)` 逻辑不变）

---

## 4. Files Affected

| 文件 | 改动类型 |
|---|---|
| `src/frontend/static/css/style.css` | 结论卡片降调样式（`.conclusion` 注脚变体），§1 padding 增大 |
| `src/frontend/static/js/app.js` | **无需改动**，现有逻辑已正确处理 cases/scatter 切换 |
| `src/frontend/templates/index.html` | 无结构改动（网格比例不变，只改 CSS） |

---

## 5. Success Criteria

1. 结论区 §1 与 §4–6 在视觉重量上有可感知的层次差异
2. §2/§3 作为「中间层」，明显重于 §4–6 但轻于 §1
3. 分析完成后页面上只有一处证据列表（`scatter__cards`），不出现重复
4. 分析进行中，`cases` 实时流照常工作
5. 所有现有动画（`conclusion-in`、`fade-in`）不受影响
