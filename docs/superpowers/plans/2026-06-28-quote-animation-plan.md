# Quote Carousel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a bilingual, fade-animated quote carousel to the analysis waiting state that disappears once real content arrives.

**Architecture:** A small data-driven carousel lives entirely in the frontend. Quotes are defined as i18n keys in `app.js`, rendered into a new `#quote-card` section in `index.html`, styled and animated in `style.css`. Visibility is controlled by existing render/event hooks: show while `lens-reveal` is hidden and no evidence cards exist; hide on lens reveal, first evidence batch, or completion.

**Tech Stack:** Vanilla ES5 JS, CSS custom properties, Flask/Jinja2 templates.

## Global Constraints

- Animation style: fade-in / fade-out carousel.
- Default interval: 8 seconds total per quote (400ms fade in, 6400ms hold, 400ms fade out).
- Carousel pauses when the card is hidden.
- Respect `prefers-reduced-motion`: disable fades and switch instantly.
- Quote card appears only when `#lens-reveal` is hidden and scatter section has zero evidence cards.
- Quotes must be bilingual (Chinese + English) via existing i18n object.
- Commit frequently; each task ends with a working, testable state.

## File Structure

| File | Responsibility |
|---|---|
| `src/frontend/templates/index.html` | Markup for `#quote-card` placed between `.analysis__headline` and `#lens-reveal`. |
| `src/frontend/static/css/style.css` | `.quote-card` layout, typography, fade animation keyframes, reduced-motion fallback, responsive rules. |
| `src/frontend/static/js/app.js` | Quote data, i18n strings, carousel controller (`startQuoteCarousel`, `stopQuoteCarousel`, `updateQuoteCardVisibility`), and hooks into existing event handlers. |

---

### Task 1: Add quote-card markup to analysis page

**Files:**
- Modify: `src/frontend/templates/index.html:231`

**Interfaces:**
- Produces: a `<section id="quote-card" class="quote-card" hidden>` element containing `.quote-card__tag` and `.quote-card__text` children.

- [ ] **Step 1: Insert quote-card section below analysis headline**

After the closing `</div>` of `.analysis__headline` (around line 231) and before `<section class="lens-reveal" id="lens-reveal" hidden>`, insert:

```html
    <!-- Quote carousel: shown only while waiting for the first analysis content. -->
    <section class="quote-card" id="quote-card" hidden aria-live="polite">
      <span class="quote-card__tag" id="quote-card-tag"></span>
      <p class="quote-card__text" id="quote-card-text"></p>
    </section>
```

- [ ] **Step 2: Verify the page still renders**

Run the local Flask server:

```bash
cd /Users/Lovegood/Desktop/Unveiling
python src/app.py
```

Open the app in a browser and confirm no console errors on the home screen.

- [ ] **Step 3: Commit**

```bash
git add src/frontend/templates/index.html
git commit -m "feat(analysis): add quote-card waiting-state markup"
```

---

### Task 2: Style the quote card and fade animation

**Files:**
- Modify: `src/frontend/static/css/style.css` (append near the analysis section)

**Interfaces:**
- Consumes: HTML structure from Task 1.
- Produces: `.quote-card`, `.quote-card__tag`, `.quote-card__text`, `.quote-card.is-visible`, `.quote-card.is-fading`, and `@media (prefers-reduced-motion: reduce)` rules.

- [ ] **Step 1: Add quote-card styles**

Append the following CSS after the `.now` rules (around line 730):

```css
/* Quote carousel shown during empty waiting states */
.quote-card {
  max-width: 640px;
  margin: 24px auto 0;
  padding: 16px 20px;
  text-align: center;
  opacity: 0;
  transform: translateY(6px);
  transition: opacity 400ms ease, transform 400ms ease;
  pointer-events: none;
}

.quote-card.is-visible {
  opacity: 0.75;
  transform: translateY(0);
}

.quote-card__tag {
  display: inline-block;
  font-family: var(--font-sans);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent-tension);
  margin-bottom: 8px;
}

.quote-card__text {
  font-family: var(--font-serif);
  font-size: 16px;
  line-height: 1.6;
  color: var(--ink-secondary);
  margin: 0;
}

@media (min-width: 768px) {
  .quote-card { margin-top: 32px; }
  .quote-card__text { font-size: 18px; }
}

@media (prefers-reduced-motion: reduce) {
  .quote-card {
    transition: none;
    opacity: 0.75;
    transform: none;
  }
}
```

- [ ] **Step 2: Check that the card is not visible on home screen**

Because `#quote-card` has `hidden`, it should not appear. Confirm in browser DevTools that the element exists but is not rendered.

- [ ] **Step 3: Commit**

```bash
git add src/frontend/static/css/style.css
git commit -m "feat(analysis): style quote-card waiting-state carousel"
```

---

### Task 3: Add quote data and i18n strings

**Files:**
- Modify: `src/frontend/static/js/app.js` (i18n section and state area)

**Interfaces:**
- Produces: `QUOTES` array and new i18n keys: `quoteTagDesign`, `quoteTagMethod`, `quoteTagPhilosophy`, plus six `quote*` text keys in both languages.

- [ ] **Step 1: Add quote keys to Chinese i18n**

In the `'中文'` strings object, after `nowLabel: '现在',` (around line 52), add:

```js
      quoteTagDesign: '设计溯源',
      quoteTagMethod: '方法论',
      quoteTagPhilosophy: '类比哲思',
      quoteDesignAmazonia: '背景河流轮廓的 unveil 文本，设计灵感来自「访问亚马逊」。',
      quoteTiNeDialogue: '类比分析的本质，是不断调用荣格八维中的 Ti 与 Ne 功能。',
      quoteTiNeAbstractThenSearch: '先用 Ti 把问题抽象成结构，再用 Ne 去远方找相似的骨架。',
      quoteSharedEssence: '许多事情本质是相通的，只是不同时代、不同领域有不同的表现形式。',
      quoteStructuralTransfer: '一个好的类比不是相似之处的罗列，而是结构性关系的迁移。',
      quoteFarLeap: '跨得越远，照得越亮——只要骨架仍然咬合。',
```

- [ ] **Step 2: Add quote keys to English i18n**

In the `'English'` strings object (around line 180), add the English equivalents after `nowLabel: 'Now',`:

```js
      quoteTagDesign: 'Design provenance',
      quoteTagMethod: 'Methodology',
      quoteTagPhilosophy: 'Philosophy',
      quoteDesignAmazonia: "The river-outline lettering is inspired by Amazonia's typographic landscape.",
      quoteTiNeDialogue: 'Analogy analysis is essentially Ti and Ne in dialogue.',
      quoteTiNeAbstractThenSearch: 'Abstract the pattern with Ti, then let Ne search distant skeletons.',
      quoteSharedEssence: 'Many things share the same essence; only the costumes differ.',
      quoteStructuralTransfer: 'A good analogy is not a list of resemblances, but a transfer of structure.',
      quoteFarLeap: 'The farther the leap, the brighter the illumination—if the joints still fit.',
```

- [ ] **Step 3: Define QUOTES array**

After the `I18N` object and before the `state` object (around line 560), add:

```js
  var QUOTES = [
    { tag: 'quoteTagDesign', text: 'quoteDesignAmazonia' },
    { tag: 'quoteTagMethod', text: 'quoteTiNeDialogue' },
    { tag: 'quoteTagMethod', text: 'quoteTiNeAbstractThenSearch' },
    { tag: 'quoteTagPhilosophy', text: 'quoteSharedEssence' },
    { tag: 'quoteTagPhilosophy', text: 'quoteStructuralTransfer' },
    { tag: 'quoteTagPhilosophy', text: 'quoteFarLeap' },
  ];
```

- [ ] **Step 4: Verify keys resolve**

Temporarily open the browser console and run:

```js
I18N['中文'].quoteTagDesign
// expected: "设计溯源"
I18N['English'].quoteFarLeap
// expected: "The farther the leap..."
```

- [ ] **Step 5: Commit**

```bash
git add src/frontend/static/js/app.js
git commit -m "feat(analysis): add bilingual quote data and i18n keys"
```

---

### Task 4: Implement carousel controller and visibility logic

**Files:**
- Modify: `src/frontend/static/js/app.js`

**Interfaces:**
- Consumes: `QUOTES`, `t()`, `dom.quoteCard`, `dom.quoteCardTag`, `dom.quoteCardText`, `state.lens`, `state.evidence`.
- Produces: `startQuoteCarousel()`, `stopQuoteCarousel()`, `updateQuoteCardVisibility()`, `quoteCardIndex` state variable.

- [ ] **Step 1: Add DOM refs**

In `resolveDom()` (around line 606), add inside the returned object:

```js
      quoteCard: document.getElementById('quote-card'),
      quoteCardTag: document.getElementById('quote-card-tag'),
      quoteCardText: document.getElementById('quote-card-text'),
```

- [ ] **Step 2: Add carousel state**

In the `state` object (around line 578), add:

```js
    quoteCardIndex: 0,
    quoteCardTimer: null,
    quoteCardFadeTimer: null,
```

- [ ] **Step 3: Add carousel functions**

After the `setNarration` function (around line 700), add:

```js
  var QUOTE_INTERVAL = 8000;
  var QUOTE_FADE_DURATION = 400;

  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function renderQuoteCard(index) {
    var quote = QUOTES[index % QUOTES.length];
    if (!quote) return;
    setText(dom.quoteCardTag, t(quote.tag));
    setText(dom.quoteCardText, t(quote.text));
  }

  function startQuoteCarousel() {
    stopQuoteCarousel();
    if (!dom.quoteCard || dom.quoteCard.hidden) return;
    state.quoteCardIndex = 0;
    renderQuoteCard(state.quoteCardIndex);
    dom.quoteCard.classList.add('is-visible');
    if (prefersReducedMotion()) {
      state.quoteCardTimer = window.setInterval(function () {
        state.quoteCardIndex = (state.quoteCardIndex + 1) % QUOTES.length;
        renderQuoteCard(state.quoteCardIndex);
      }, QUOTE_INTERVAL);
      return;
    }
    state.quoteCardTimer = window.setInterval(function () {
      if (!dom.quoteCard) return;
      dom.quoteCard.classList.remove('is-visible');
      state.quoteCardFadeTimer = window.setTimeout(function () {
        state.quoteCardIndex = (state.quoteCardIndex + 1) % QUOTES.length;
        renderQuoteCard(state.quoteCardIndex);
        if (dom.quoteCard) dom.quoteCard.classList.add('is-visible');
      }, QUOTE_FADE_DURATION);
    }, QUOTE_INTERVAL);
  }

  function stopQuoteCarousel() {
    if (state.quoteCardTimer) {
      window.clearInterval(state.quoteCardTimer);
      state.quoteCardTimer = null;
    }
    if (state.quoteCardFadeTimer) {
      window.clearTimeout(state.quoteCardFadeTimer);
      state.quoteCardFadeTimer = null;
    }
    if (dom.quoteCard) dom.quoteCard.classList.remove('is-visible');
  }

  function updateQuoteCardVisibility() {
    var hasContent = (
      (dom.lensReveal && !dom.lensReveal.hidden) ||
      (state.evidence && state.evidence.length > 0)
    );
    var shouldShow = state.screen === 'analysis' && !hasContent;
    if (!dom.quoteCard) return;
    if (shouldShow && dom.quoteCard.hidden) {
      show(dom.quoteCard);
      startQuoteCarousel();
    } else if (!shouldShow && !dom.quoteCard.hidden) {
      if (prefersReducedMotion()) {
        stopQuoteCarousel();
        hide(dom.quoteCard);
      } else {
        dom.quoteCard.classList.remove('is-visible');
        state.quoteCardFadeTimer = window.setTimeout(function () {
          stopQuoteCarousel();
          hide(dom.quoteCard);
        }, QUOTE_FADE_DURATION);
      }
    }
  }
```

- [ ] **Step 4: Reset carousel on analysis start**

In `startAnalysis()` (around line 994), before the `fetch` call, add:

```js
    state.quoteCardIndex = 0;
    stopQuoteCarousel();
```

- [ ] **Step 5: Hook visibility into render and event handlers**

Call `updateQuoteCardVisibility()` in these places:

1. In `onPhase()` after each `setNarration` branch (around line 1070):

```js
    updateQuoteCardVisibility();
```

2. At the end of `onLens()` (around line 1078):

```js
    updateQuoteCardVisibility();
```

3. At the end of `onEvidenceBatch()` after the `if (items.length)` block (around line 1107):

```js
    updateQuoteCardVisibility();
```

4. In the analysis screen render path where the analysis screen becomes active. Find `showScreen('analysis')` or the equivalent in `startAnalysis()` and add `updateQuoteCardVisibility();` after the screen switch.

- [ ] **Step 6: Manual smoke test**

1. Start the server and submit a question.
2. While the status line shows "正在拆解问题 — 提炼核心结构", confirm the quote card appears below it and cycles.
3. When the lens reveal appears, confirm the quote card fades out.
4. Refresh and submit another question; confirm the card reappears and cycles through different quotes.
5. Toggle language and confirm the quotes switch language.

- [ ] **Step 7: Commit**

```bash
git add src/frontend/static/js/app.js
git commit -m "feat(analysis): wire quote carousel visibility and rotation"
```

---

### Task 5: Polish and verify reduced motion

**Files:**
- Modify: `src/frontend/static/css/style.css`, `src/frontend/static/js/app.js`

**Interfaces:**
- Ensures `prefers-reduced-motion` users see instant switches and no fade.

- [ ] **Step 1: Verify reduced-motion path**

In browser DevTools, enable "Emulate CSS media feature prefers-reduced-motion: reduce" (Chrome: Rendering panel). Start an analysis and confirm:

- Quote card appears without fade animation.
- Quote text switches instantly at 8-second intervals.
- Card disappears instantly when content arrives.

- [ ] **Step 2: Check responsive layout**

Resize the browser to mobile width (375px) and confirm the card fits within the viewport and the quote text remains readable.

- [ ] **Step 3: Commit any CSS tweaks**

If adjustments are needed, commit them:

```bash
git add src/frontend/static/css/style.css src/frontend/static/js/app.js
git commit -m "fix(analysis): quote-card reduced-motion and responsive polish"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Plan task |
|---|---|
| Insert quote card below headline | Task 1 |
| Bilingual quote content | Task 3 |
| Fade carousel, 8s interval, pause on hide | Task 4 |
| Show only when lens hidden and no evidence | Task 4 (`updateQuoteCardVisibility`) |
| Disappear on lens reveal / evidence / completion | Task 4 (hooks in `onLens`, `onEvidenceBatch`, `onPhase`) |
| Reduced motion support | Task 2 CSS + Task 4 `prefersReducedMotion` + Task 5 |
| Card opacity ~0.75, light styling | Task 2 |

### Placeholder scan

No TBD, TODO, or vague steps remain. Every step contains exact file paths, line ranges, code, and verification commands.

### Type consistency

- DOM refs: `dom.quoteCard`, `dom.quoteCardTag`, `dom.quoteCardText`.
- State keys: `state.quoteCardIndex`, `state.quoteCardTimer`, `state.quoteCardFadeTimer`.
- Functions: `startQuoteCarousel()`, `stopQuoteCarousel()`, `updateQuoteCardVisibility()`, `renderQuoteCard(index)`.
- All usages match these names.

### Gaps

None identified. The plan is scoped to the approved design.
