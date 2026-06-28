# Quote Carousel for Analysis Waiting State

## Status

Approved design awaiting implementation plan.

## Context

The Unveiling analysis page currently shows a live status line (the "现在" row) while the backend is in the `inception` and `exploration` phases. During these phases the main content area below the status line is empty until the lens reveal or the first evidence cards appear. This empty interval can feel long and does not reinforce the project's design language or methodology.

## Goal

Fill the waiting gap with a quiet, bilingual quote carousel that:

1. Reduces perceived waiting time.
2. Teaches visitors about the project's design inspiration, analogy methodology, and core philosophy.
3. Disappears gracefully as soon as real analysis content arrives.
4. Does not distract from the primary status line.

## Design Decisions

### Placement

- Insert a new `<section class="quote-card" id="quote-card" hidden>` directly below `.analysis__headline` and above `#lens-reveal`.
- The card is centered in the main content column with a max-width of ~640px.
- It is visible only when both `#lens-reveal` is hidden and the scatter section has no evidence cards.

### Content

Six quotes organized into three thematic tags. Each quote is stored as an i18n key so Chinese and English versions can coexist.

| Tag key (i18n) | Quote key (i18n) | Category |
|---|---|---|
| `quoteTagDesign` | `quoteDesignAmazonia` | Design provenance |
| `quoteTagMethod` | `quoteTiNeDialogue` | Methodology |
| `quoteTagMethod` | `quoteTiNeAbstractThenSearch` | Methodology |
| `quoteTagPhilosophy` | `quoteSharedEssence` | Philosophy |
| `quoteTagPhilosophy` | `quoteStructuralTransfer` | Philosophy |
| `quoteTagPhilosophy` | `quoteFarLeap` | Philosophy |

**Chinese copy**

- `quoteDesignAmazonia`: 背景河流轮廓的 unveil 文本，设计灵感来自「访问亚马逊」。
- `quoteTiNeDialogue`: 类比分析的本质，是不断调用荣格八维中的 Ti 与 Ne 功能。
- `quoteTiNeAbstractThenSearch`: 先用 Ti 把问题抽象成结构，再用 Ne 去远方找相似的骨架。
- `quoteSharedEssence`: 许多事情本质是相通的，只是不同时代、不同领域有不同的表现形式。
- `quoteStructuralTransfer`: 一个好的类比不是相似之处的罗列，而是结构性关系的迁移。
- `quoteFarLeap`: 跨得越远，照得越亮——只要骨架仍然咬合。

**English copy**

- `quoteDesignAmazonia`: The river-outline lettering is inspired by Amazonia's typographic landscape.
- `quoteTiNeDialogue`: Analogy analysis is essentially Ti and Ne in dialogue.
- `quoteTiNeAbstractThenSearch`: Abstract the pattern with Ti, then let Ne search distant skeletons.
- `quoteSharedEssence`: Many things share the same essence; only the costumes differ.
- `quoteStructuralTransfer`: A good analogy is not a list of resemblances, but a transfer of structure.
- `quoteFarLeap`: The farther the leap, the brighter the illumination—if the joints still fit.

### Animation

- Style: fade-in / fade-out carousel.
- Default interval: 8 seconds total per quote.
  - Fade in: 400ms.
  - Hold: 6400ms.
  - Fade out: 400ms.
  - Swap text and fade in next quote.
- Carousel pauses when the card is hidden so no background cycling occurs.
- Respect `prefers-reduced-motion`: disable fades and switch instantly.

### Visibility Logic

Show the quote card when all of the following are true:

- Analysis screen is active.
- `#lens-reveal` is still hidden.
- Scatter section has zero rendered evidence cards.

Hide it when any of the following occur:

- `#lens-reveal` becomes visible (lens event received).
- First evidence batch is rendered in the scatter section.
- Analysis completes.

When hiding, use the same 400ms fade-out rather than an instant `hidden` toggle.

### Visual Style

- Tag: small sans-serif text, low-contrast accent color from the existing palette.
- Quote body: serif font, size between the question headline and the status line.
- Card opacity: ~0.75 so it reads as secondary narration.
- No border or heavy shadow; keep the card light.

### Accessibility

- Container uses `aria-live="polite"` but only announces on first appearance and final disappearance, not on every quote rotation.
- No keyboard trap; users can tab past the card normally.
- Reduced-motion users see static text changes without animation.

## Files to Modify

1. `src/frontend/templates/index.html` — add `#quote-card` markup below `.analysis__headline`.
2. `src/frontend/static/css/style.css` — add `.quote-card`, animation keyframes, and reduced-motion rules.
3. `src/frontend/static/js/app.js` — add `QUOTES` data, i18n strings, carousel controller, and visibility hooks in existing render/event handlers.

## Out of Scope

- Custom SVG path animation (the river-outline reveal effect is reserved for future exploration).
- User-configurable quote list.
- Per-phase quote themes (initial version uses a single rotating pool).

## Success Criteria

- [ ] The quote card appears during empty waiting periods.
- [ ] It cycles through all six quotes at the specified interval.
- [ ] It disappears when the lens reveal or first evidence appears.
- [ ] Chinese and English quotes switch with the language toggle.
- [ ] Animation is disabled under `prefers-reduced-motion`.
