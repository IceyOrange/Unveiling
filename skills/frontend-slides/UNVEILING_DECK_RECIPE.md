# Unveiling Analysis Deck — Recipe

This file is the canonical specification for **Mode D: Unveiling Analysis Deck**. It is opinionated and sealed: do not negotiate slide count, order, or style with the user. The deck is one paper-textured artifact rendered for the one person who asked the original question.

Read this file together with:

- [SKILL.md](SKILL.md) §"Phase 7: Unveiling Analysis Deck (Mode D)" — entry conditions
- [STYLE_PRESETS.md](STYLE_PRESETS.md) §13 "Unveiling Paper" — locked preset
- [UNVEILING_VOCAB.md](UNVEILING_VOCAB.md) — every user-visible string must route through this
- [viewport-base.css](viewport-base.css) — still mandatory

---

## 1. Canonical Slide Outline

Order is fixed. Optional slides (marked ⚪) appear only when their source data is non-empty. Required slides (marked ⚫) always render — empty fallbacks are listed in §3.

| # | Slide | Required | Data source | Notes |
|---|-------|----------|-------------|-------|
| 01 | 封面 | ⚫ | `driving_question` + `phase` (mode badge) | Hero serif, mode badge top-right |
| 02 | 你问的是 | ⚫ | `driving_question` + `sub_questions[].content` (status as colored dot prefix) | ≤5 子问题 bullets; if >5, keep the 5 with most evidence |
| 03 | 总的来看 | ⚫ | `conclusion.convergent_finding` | Hero serif; 3px ink left-rule |
| 04 | 拉扯之处 | ⚫ | `conclusion.tension` | Pull-quote serif; **4px orange left-rule (the only orange in the deck unless §08 fires)** |
| 05 | 什么时候不成立 | ⚫ | `conclusion.boundary_condition` | Bullet list or 2-card grid |
| 06 | 我们换过几次角度 | ⚪ | `lens_chains[]` | Show ≤2 chains, ≤3 versions per chain; collapse rationale to one line |
| 07 | 我们找到了什么 | ⚫ | `evidence[]` top 3 by `(confidence, layer)` sort | Cards with layer-colored mono pill |
| 08 | 意外发现 | ⚪ | `evidence[is_unexpected=True]` | Only if ≥1 unexpected evidence; orange-tinted card |
| 09 | 几个敢打赌的猜想 | ⚪ | `predictions[]` filtered by `killer_evidence` non-empty | Each item: claim + status chip + 决定性证据 line |
| 10 | 还没想清楚的 | ⚫ | `conclusion.unresolved` + `sub_questions[status=stuck]` | **Sand background panel** |
| 11 | 给你的提醒 | ⚫ | `conclusion.implication` | Hero serif; closing breath |
| 12 | 结束 | ⚫ | `integrity.round_count`, `integrity.token_spent`, `lens_chains` count | Minimal signature; mono meta |

**Why this order:** Cognitive rhythm — answer first (03 总的来看), then unsettle (04 拉扯之处), bound it (05 不成立), show the road (06 换角度 / 07 找到的 / 08 意外), bet (09 猜想), confess (10 没想清楚的), and end with a takeaway (11 提醒). This mirrors the result-page section order in the existing Unveiling frontend.

---

## 2. HTML Skeletons

All skeletons assume:

- `viewport-base.css` is inlined in `<style>`
- The Unveiling Paper preset's full `:root` token block is inlined right after `viewport-base.css`
- Every `.slide` already has `height: 100vh; height: 100dvh; overflow: hidden;` and follows clamp() invariants
- `{{var}}` placeholders are filled by the generator; never embed literal jargon — route every Chinese label through UNVEILING_VOCAB.md

### 2.1 Slide 01 · 封面

```html
<section class="slide slide--cover">
  <span class="mode-badge">{{mode_label}}</span> <!-- 刚开始 / 展开找 / 收尾 -->
  <h1 class="hero-serif">{{driving_question}}</h1>
  <p class="kicker-mono">UNVEILING · 类比分析</p>
</section>
```

### 2.2 Slide 02 · 你问的是

```html
<section class="slide slide--question">
  <h2 class="section-serif">你问的是</h2>
  <blockquote class="pull-quote">{{driving_question}}</blockquote>
  <p class="kicker-sans">我们把它拆成了这些小问题:</p>
  <ul class="sub-question-list">
    {% for sq in sub_questions[:5] %}
    <li>
      <span class="status-dot" data-status="{{sq.status}}"></span>
      <span class="sub-question-text">{{sq.content}}</span>
      <span class="sub-question-status-label">{{sq.status_label}}</span>
    </li>
    {% endfor %}
  </ul>
</section>
```

### 2.3 Slide 03 · 总的来看

```html
<section class="slide slide--takeaway">
  <h2 class="section-serif">总的来看</h2>
  <p class="hero-serif rule-ink">{{convergent_finding}}</p>
</section>
```

### 2.4 Slide 04 · 拉扯之处

```html
<section class="slide slide--tension">
  <h2 class="section-serif">拉扯之处</h2>
  <blockquote class="pull-quote rule-tension">{{tension}}</blockquote>
</section>
```

`rule-tension` is the 4px orange left-rule. This is the **only** slide that may render orange unless §2.8 fires.

### 2.5 Slide 05 · 什么时候不成立

```html
<section class="slide slide--boundary">
  <h2 class="section-serif">什么时候不成立</h2>
  <ul class="boundary-list">
    {% for item in boundary_items %}
    <li class="boundary-card">{{item}}</li>
    {% endfor %}
  </ul>
</section>
```

If `conclusion.boundary_condition` is a single paragraph, split on sentence terminators (。/. / ;) and keep ≤4 items. Otherwise pre-parse upstream.

### 2.6 Slide 06 · 我们换过几次角度

```html
<section class="slide slide--lens-evolution">
  <h2 class="section-serif">我们换过几次角度</h2>
  {% for chain in lens_chains[:2] %}
  <div class="lens-chain">
    {% for lens in chain.chain[:3] %}
    <div class="lens-version">
      <span class="version-mono">v{{loop.index}}</span>
      <span class="lens-name-serif">{{lens.name}}</span>
      <span class="lens-rationale-sans">{{lens.rationale | truncate(60)}}</span>
    </div>
    {% if not loop.last %}<span class="lens-arrow">↓</span>{% endif %}
    {% endfor %}
  </div>
  {% endfor %}
</section>
```

### 2.7 Slide 07 · 我们找到了什么

```html
<section class="slide slide--evidence">
  <h2 class="section-serif">我们找到了什么</h2>
  <div class="evidence-grid">
    {% for e in evidence[:3] %}
    <article class="evidence-card">
      <span class="layer-pill" data-layer="{{e.layer}}">{{e.layer_label}}</span> <!-- 表面 / 怎么运作 / 底层规律 -->
      <p class="evidence-body-serif">{{e.content}}</p>
      <span class="confidence-meta-mono">{{e.confidence_label}}</span> <!-- 最有分量 / 中等 / 较弱 -->
    </article>
    {% endfor %}
  </div>
</section>
```

### 2.8 Slide 08 · 意外发现 (optional)

Renders only when at least one `evidence[i].is_unexpected == True`. This is the second place orange may appear.

```html
<section class="slide slide--unexpected">
  <h2 class="section-serif">意外发现</h2>
  <p class="kicker-sans">这些没在原本的设想里:</p>
  {% for e in unexpected_evidence[:2] %}
  <article class="unexpected-card rule-tension-soft">
    <p class="evidence-body-serif">{{e.content}}</p>
    <span class="layer-pill" data-layer="{{e.layer}}">{{e.layer_label}}</span>
  </article>
  {% endfor %}
</section>
```

### 2.9 Slide 09 · 几个敢打赌的猜想 (optional)

Renders only when ≥1 prediction has non-empty `killer_evidence`.

```html
<section class="slide slide--predictions">
  <h2 class="section-serif">几个敢打赌的猜想</h2>
  <ul class="prediction-list">
    {% for p in predictions[:3] %}
    <li class="prediction-card">
      <p class="prediction-claim-serif">{{p.claim}}</p>
      <p class="killer-evidence-sans">决定性证据:{{p.killer_evidence}}</p>
      <span class="prediction-status" data-status="{{p.status}}">{{p.status_label}}</span> <!-- 对上了 / 被推翻了 / 部分对、改过了 / 还没试过 -->
    </li>
    {% endfor %}
  </ul>
</section>
```

### 2.10 Slide 10 · 还没想清楚的

```html
<section class="slide slide--unresolved bg-sand">
  <h2 class="section-serif">还没想清楚的</h2>
  <p class="body-serif">{{unresolved}}</p>
  {% if stuck_sub_questions %}
  <p class="kicker-sans">这几个小问题卡住了:</p>
  <ul class="stuck-list">
    {% for sq in stuck_sub_questions %}
    <li><span class="status-dot" data-status="stuck"></span>{{sq.content}}</li>
    {% endfor %}
  </ul>
  {% endif %}
</section>
```

`bg-sand` swaps the canvas to `var(--bg-sand) #f0ebe0` — the humility cue.

### 2.11 Slide 11 · 给你的提醒

```html
<section class="slide slide--implication">
  <h2 class="section-serif">给你的提醒</h2>
  <p class="hero-serif rule-ink">{{implication}}</p>
</section>
```

### 2.12 Slide 12 · 结束

```html
<section class="slide slide--signature">
  <p class="signature-mono">
    走了 {{round_count}} 回合 · 用了 {{token_spent}} token · 换过 {{lens_chain_count}} 次角度
  </p>
  <p class="kicker-mono">UNVEILING</p>
</section>
```

---

## 3. Empty-Fallback Copy

Never leave a required slide blank. When the source data is empty/None, render the slide on `bg-sand` with the fallback copy below. These are intentional, plain, and concede uncertainty — they are NOT decorative filler.

| Slide | Empty trigger | Fallback copy |
|-------|---------------|---------------|
| 03 总的来看 | `conclusion is None` or `convergent_finding` empty | "这一轮没收敛到一个清晰的结论。可能是问得太大,也可能是材料还不够。" |
| 04 拉扯之处 | `tension` empty | "这次没找到明显的矛盾点 —— 这本身就是信号:要么问题方向比较一致,要么我们还没看到对立面。" |
| 05 什么时候不成立 | `boundary_condition` empty | "没列出明显的边界条件。意味着结论的适用范围还没被压力测试过。" |
| 07 我们找到了什么 | `evidence` empty | "这一轮没沉淀出有分量的证据条目。" |
| 10 还没想清楚的 | `unresolved` empty AND no stuck sub-questions | "这次没有明显卡住的小问题。" |
| 11 给你的提醒 | `implication` empty | "这次没生成具体的提醒。如果你对结论有共鸣,可以从「拉扯之处」那一页继续追问。" |

Optional slides (06, 08, 09) simply don't render when empty — no fallback needed.

---

## 4. Data Mapping

Every template variable maps to a field from `_serialize_result()` in `frontend/app.py`. Internal field names stay English; user-visible string transformations happen via UNVEILING_VOCAB.md.

| Template variable | Source field | Transform |
|-------------------|--------------|-----------|
| `{{driving_question}}` | `payload["driving_question"]` | none |
| `{{mode_label}}` | derived: `payload["phase"]` → UNVEILING_VOCAB.md phase table | inception→刚开始, exploration→展开找, convergence→收尾 |
| `{{sub_questions}}` | `payload["sub_questions"]` | sort by `(status_priority, -evidence_count)` then slice [:5] |
| `sq.status_label` | `sq["status"]` | VOCAB: untouched→还没看, exploring→还在看, closed→想清楚了, stuck→卡住了 |
| `sq.status` (CSS data-attr) | `sq["status"]` | passthrough — CSS reads it for the dot color |
| `{{convergent_finding}}` | `payload["conclusion"]["convergent_finding"]` | none (empty-fallback per §3) |
| `{{tension}}` | `payload["conclusion"]["tension"]` | none (empty-fallback per §3) |
| `{{boundary_items}}` | `payload["conclusion"]["boundary_condition"]` | split on 。 / . / ; — keep ≤4 |
| `{{lens_chains}}` | `payload["lens_chains"]` | slice [:2] outer, [:3] inner |
| `lens.rationale` | `lens["rationale"]` | truncate to ~60 chars; ellipsis on overflow |
| `{{evidence}}` | `payload["evidence"]` | already sorted upstream by `(confidence_rank, layer_rank)` — just slice [:3] |
| `e.layer_label` | `e["layer"]` | VOCAB: phenomenon→表面, mechanism→怎么运作, structure→底层规律 |
| `e.confidence_label` | `e["confidence"]` | VOCAB: strong→最有分量, medium→中等, weak→较弱, unexpected→意外 |
| `{{unexpected_evidence}}` | filter `payload["evidence"]` where `is_unexpected == True` | slice [:2] |
| `{{predictions}}` | `payload["predictions"]` filtered to `killer_evidence` non-empty | slice [:3] |
| `p.status_label` | `p["status"]` | VOCAB: pending→还没试过, supported→对上了, refuted→被推翻了, modified→部分对、改过了 |
| `{{unresolved}}` | `payload["conclusion"]["unresolved"]` | none (empty-fallback per §3) |
| `{{stuck_sub_questions}}` | filter `payload["sub_questions"]` where `status == "stuck"` | passthrough |
| `{{implication}}` | `payload["conclusion"]["implication"]` | none (empty-fallback per §3) |
| `{{round_count}}` | `payload["integrity"]["round_count"]` | integer |
| `{{token_spent}}` | `payload["integrity"]["token_spent"]` | integer |
| `{{lens_chain_count}}` | `len(payload["lens_chains"])` | integer |

Note: `payload["integrity"]` is still present in the current schema. A separate planned step will remove the integrity badge from the result page; until then, the recipe only reads `round_count` / `token_spent` from it for the signature slide. No integrity meta surfaces elsewhere in the deck.

---

## 5. Embed Mode

When the deck is rendered inside an `<iframe>` on the Unveiling result page (the planned upcoming layout: deck on top half, milestone thinking on bottom half), pass `embed=True` to the generator. In embed mode:

- **Hide nav-dots** — the parent page owns navigation context; the dots would compete
- **Hide the keyboard-hint pill** ("← → 切换 · Space 下一张") — the deck inside an iframe rarely has focus
- **Hide the progress bar** — small frame, redundant
- **Disable global keyboard listeners** OR scope them to `document.querySelector('.slide-deck')`'s focus state — otherwise the parent page's arrow keys get hijacked
- **Auto-fit:** ensure `body { overflow: hidden; }` so the iframe shows exactly one slide at a time
- **Click-to-advance** still works on the slide body
- **No autoplay** unless the parent page explicitly triggers it via `postMessage` — start on slide 01, paused

Standalone mode (when the user downloads the deck as a single HTML file) keeps all UI elements visible.

---

## 6. Generation Order

The generator MUST follow this order so empty-fallback logic and ordering invariants hold:

1. Read the payload; validate required keys are present (`driving_question`, `sub_questions`, `conclusion`)
2. Compute derived fields: `mode_label`, `sub_question status_labels`, `evidence layer_labels` / `confidence_labels`, `prediction status_labels`, `lens_chain_count`
3. Pre-process: sort/slice sub_questions, evidence, predictions; build `unexpected_evidence` and `stuck_sub_questions`; split `boundary_condition` into items
4. Decide which optional slides (06, 08, 09) render based on data presence
5. Decide which empty-fallback applies to each required slide
6. Render the 10-12 slides in canonical order
7. Inline `viewport-base.css` + Unveiling Paper `:root` block + recipe-specific CSS (status-dot, layer-pill, rule-ink/rule-tension, bg-sand, mode-badge)
8. If `embed=True`, strip nav-dots/keyboard-hint/progress-bar HTML and scope key handlers

---

## 7. Validation Checklist

Before delivering the HTML:

- [ ] No literal English-from-source strings leaked: search the rendered HTML for "convergent_finding", "tension" (as English label, not field), "lens", "killer evidence", "phenomenon/mechanism/structure" (as English labels), "supported/refuted/modified", "inception/exploration/convergence". If any appear in a `>...<` text node, route them through UNVEILING_VOCAB.md first.
- [ ] No jargon Chinese leaked: "收敛发现", "可证伪预判", "诚信度披露", "minimum viable answer". Replace per UNVEILING_VOCAB.md.
- [ ] Orange `#ff6b35` appears on exactly one slide (Slide 04 拉扯之处), or exactly two if Slide 08 意外发现 fires. Never elsewhere.
- [ ] Every required slide rendered, even when source data is empty (empty-fallback applied).
- [ ] Every clamp() font-size uses three args. Every `.slide` has `overflow: hidden`. Breakpoints at 700/600/500px included.
- [ ] In embed mode, no nav-dots / keyboard-hint / progress-bar in DOM.
- [ ] `payload["integrity"]` is read only for `round_count` / `token_spent` on Slide 12 — never surfaced as an "integrity badge" in the deck.
