# Unveiling Vocab — Plain Language Lookup

This file is the **single source of truth** for every user-visible string in the Unveiling Analysis Deck (Mode D). The generator, the result page, and the live narration bar all read from this table — there should be no plain-language string defined anywhere else.

The principle: every term that smells like a system noun ("透镜", "可证伪预判", "killer evidence", "minimum viable answer", "诚信度披露") gets translated into something a non-technical reader would actually say. Internal data field names (`convergent_finding`, `lens_chains`, `is_unexpected`) stay English — they never reach a screen.

This came from a specific user request: "收敛发现 / 张力 / 透镜 / 可证伪预判 等词太专业、不 user-friendly". This file is where that feedback lands.

---

## 1. Section headings (the cognitive rhythm)

Used in result-page section headers, slide titles, and the live narration bar.

| Internal label | User-visible string | Notes |
|----------------|---------------------|-------|
| 收敛发现 / convergent_finding | **总的来看** | The "answer first" slide |
| 张力 / tension | **拉扯之处** | The single orange moment |
| 边界条件 / boundary_condition | **什么时候不成立** | Where the answer breaks |
| 证据脉络 / evidence | **我们找到了什么** | Plural, conversational |
| 未尽 / unresolved | **还没想清楚的** | Humility, sand panel |
| 对你而言 / implication | **给你的提醒** | First-person address |
| 意外发现 (orange evidence) | **意外发现** | Keep — it's already plain |
| 可证伪预判 / predictions | **几个敢打赌的猜想** | "敢打赌" carries the falsifiability |

---

## 2. Lens vocabulary

The word "透镜" is the heaviest jargon in the system. Avoid it in user-visible strings.

| Internal label | User-visible string |
|----------------|---------------------|
| 透镜 / lens | **看问题的角度** (or shorthand **角度**) |
| 透镜演化 | **换过几次角度** |
| 透镜版本链 / lens_chain | **角度怎么变的** |
| 同一透镜的新版本 (parent_lens_id) | **同一个角度的下一稿** |
| 透镜被挑战 | **这个角度被推过** |
| 抽象透镜 | **看问题的角度** (drop "abstract" — implicit) |

---

## 3. Prediction vocabulary

| Internal label | User-visible string |
|----------------|---------------------|
| 可证伪预判 | **敢打赌的猜想** |
| killer evidence / killer_evidence | **决定性证据** |
| if_true_we_should_see | **如果对了,我们应该看到** |
| if_false_we_should_see | **如果错了,我们应该看到** |
| prediction status: **pending** | **还没试过** |
| prediction status: **supported** | **对上了** |
| prediction status: **refuted** | **被推翻了** |
| prediction status: **modified** | **部分对、改过了** |

---

## 4. Evidence vocabulary

### 4.1 Evidence layer (`evidence.layer`)

| Internal label | User-visible string | Color token |
|----------------|---------------------|-------------|
| phenomenon / 现象层 | **表面** | `--layer-phenomenon` |
| mechanism / 机制层 | **怎么运作** | `--layer-mechanism` |
| structure / 结构层 | **底层规律** | `--layer-structure` |

### 4.2 Evidence confidence (`evidence.confidence`)

| Internal label | User-visible string |
|----------------|---------------------|
| strong | **最有分量** |
| medium | **中等** |
| weak | **较弱** |
| unexpected | **意外的一条** |

### 4.3 Misc

| Internal label | User-visible string |
|----------------|---------------------|
| 强证据 | **最有分量的几条** |
| 弱证据 | **不太确定的几条** |
| `is_unexpected = True` | **没在预想里的一条** |
| source_lens_id | **从哪个角度看出来的** (rarely user-visible) |

---

## 5. Sub-question vocabulary

### 5.1 Sub-question status (`sub_questions[].status`)

| Internal label | User-visible string | Color token |
|----------------|---------------------|-------------|
| untouched | **还没看** | `--status-untouched` |
| exploring | **还在看** | `--status-exploring` |
| closed | **想清楚了** | `--status-closed` |
| stuck | **卡住了** | `--status-stuck` |

### 5.2 Sub-question terminology

| Internal label | User-visible string |
|----------------|---------------------|
| 子问题 / sub_question | **拆出来的小问题** (shorthand: **小问题**) |
| 问题树 / issue_tree | **怎么拆的** |
| driving question | **你问的是** |
| minimum viable answer | **最少够用的答案** (or paraphrase: **够回答一下了**) |

---

## 6. Phase vocabulary

| Internal label | User-visible string |
|----------------|---------------------|
| inception / 启动期 | **刚开始** |
| exploration / 探索期 | **展开找** |
| convergence / 收敛期 | **收尾** |

---

## 7. Orchestration vocabulary (rarely user-visible — but if it leaks)

| Internal label | User-visible string |
|----------------|---------------------|
| Orchestrator | (avoid — say "系统" or restructure) |
| Scheduler | (avoid — don't expose) |
| Judge | (avoid — don't expose) |
| Meta | (avoid — don't expose) |
| 降级 / degradation | **走了捷径** |
| ScheduleLogEntry | (avoid — internal) |
| 调度日志区 | (avoid — internal) |
| 诚信度披露 / integrity | **透明披露** (only if surfaced; default is "don't surface") |
| 撤回 / retracted | **改主意了** (rare; e.g., "这条证据后来改主意了") |

---

## 8. Operational mode (user's home-screen choice)

| Internal label | User-visible string |
|----------------|---------------------|
| focus | **聚焦** (already plain) |
| balance | **平衡** (already plain) |
| explore | **远探** (already plain) |
| 远近偏好 / near_far_ratio | **找近的还是远的** (rarely user-visible) |
| 横向类比 / lateral search | **跨领域找** |
| 纵向类比 / vertical search | **跨时期找** |
| 远搜索 | **找冷门的角落** |
| 近搜索 | **就近找** |

---

## 9. Action labels (buttons, links)

| Internal label | User-visible string |
|----------------|---------------------|
| "开始分析" | **开始分析** (keep) |
| "重新开始" | **重新开始** (keep) |
| "诚信度披露" | (cut — feature is being removed) |
| "查看完整分析过程" | **看看是怎么想的** |
| "详情" (debug/expand) | **详情** (keep — already plain) |
| "导出 PDF" | **导出 PDF** (keep) |
| "保存到本地" | **保存到本地** (keep) |

---

## 10. Tone Guidelines

These rules apply to every user-visible string, including the empty-fallback copy in UNVEILING_DECK_RECIPE.md §3.

### 10.1 Voice

- **Address the reader directly**, second-person, conversational. "你问的是 / 给你的提醒" not "用户提出的问题 / 系统建议".
- **Never say "用户"** in user-visible strings — the reader IS the user. Either drop the word or use "你".
- **Never say "系统" as a self-reference** in user-visible strings — say "这次" or "我们" instead. ("这次没找到明显的矛盾点" not "系统未发现明显的矛盾点".)
- **Use plural "我们"** when describing the analysis process collectively — it makes the reader feel like a collaborator, not an audience. ("我们换过几次角度", "我们找到了什么".)

### 10.2 Word choice

- **Concrete > abstract.** "卡住了" beats "状态:停滞". "想清楚了" beats "已闭合".
- **Verb > noun.** "拉扯之处" (verb-flavored) beats "矛盾点" (clinical noun). "怎么运作" beats "机制层".
- **Drop technical adjectives when possible.** "可证伪预判" → "敢打赌的猜想" (drops "可证伪" because the gamble implies it).
- **Keep numbers and units honest.** "走了 N 回合 · 用了 M token" is fine — it tells the truth about cost without dressing it up.

### 10.3 Punctuation

- **Use Chinese punctuation** for body copy: 。 , : ; — leave English/code spans (variable names, token counts) with their native punctuation.
- **One sentence per pull-quote.** If the source string is too long, the recipe says to split — don't paper over it with smaller font.
- **Avoid trailing 。 in slide titles and short labels** ("拉扯之处", not "拉扯之处。"). Sentences in body copy keep their 。.

### 10.4 What never appears in user-visible strings

- "LangGraph", "Orchestrator", "Scheduler", "Judge", "Meta", "blackboard", "黑板"
- "Pydantic", "LLM", "DeepSeek", "Serper"
- "记录", "分区" — these are storage-layer terms
- "委托", "调度" — sound bureaucratic
- "Retraction", "撤回" — say "改主意了" if needed
- Raw status enums in English (use the table above)

---

## 11. Usage Rules

1. **Internal field names stay English.** Code, JSON, log lines, comments may use `convergent_finding`, `lens_chains`, `is_unexpected`. Never translate field names.
2. **Every user-visible string routes through this file.** If a label appears in the rendered HTML, the live narration, or a button, it must match a row in §1–§9 above. If a needed label isn't here, add it before adding it to the UI.
3. **Add rows, don't fork them.** When a new label is needed, edit this file first, then reference the table in the calling code. Avoid hardcoded Chinese in templates.
4. **CSS class names and `data-*` attributes use the internal label, not the user-visible string.** `data-status="closed"` not `data-status="想清楚了"` — the visible string is rendered as the element's text content, separate from the attribute.
5. **When CSV/JSON exporting analysis results,** export the internal English fields. The plain-language translation is a rendering concern, not a data concern.

---

## 12. Coverage Check

This vocab covers the ~40 jargon strings identified in the existing frontend (`frontend/static/js/app.js`, `frontend/templates/index.html`) plus everything that flows from `_serialize_result()`. When extending Unveiling (new agents, new record types, new states), extend this file in the same pass — adding a row here is part of the definition of "done" for any new user-visible feature.
