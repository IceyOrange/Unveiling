# Results Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the six conclusion chapters a clear three-tier visual hierarchy (§1 prominent → §2-3 standard → §4-6 footnote) using CSS only, and verify the already-implemented cases/scatter lifecycle separation works correctly.

**Architecture:** Pure CSS addition to `style.css`. No HTML or JS changes. The footnote tier is applied via ID selectors that override the base `.conclusion` class. Verification of the cases/scatter separation is a manual demo run with no code changes.

**Tech Stack:** Plain CSS with `oklch()` color, CSS Grid, CSS custom properties already defined in `:root`.

**Spec:** `docs/superpowers/specs/2026-06-17-results-page-redesign.md`

---

## File Map

| File | Change |
|---|---|
| `src/frontend/static/css/style.css` | Add ~30 lines after line 1194 (after the existing `#chapter-boundary_condition` block) |
| `src/frontend/static/js/app.js` | **Read-only verification only** — no edits |
| `src/frontend/templates/index.html` | **No changes** |

---

## Task 1: Add Footnote Visual Tier for §4–6

**Context:** The base `.conclusion` class (line 1149) sets `padding: var(--space-5)`, `background: var(--surface-card)`, `box-shadow: var(--shadow-soft)`, and lead/para font-size at 16px. The existing `#chapter-boundary_condition / #chapter-unresolved / #chapter-implication` block (lines 1190–1194) only sets `grid-column: span 2`. We are extending that with visual downweighting.

The `#chapter-unresolved` card already has class `.conclusion--unresolved` which sets its inner `.conclusion__prose` to `background: var(--surface-inset)` with padding. When we set the card itself to `surface-inset`, that inner block becomes invisible — we override it to `transparent` and reset its padding.

**Files:**
- Modify: `src/frontend/static/css/style.css:1190–1194`

---

- [ ] **Step 1: Extend the existing §4-6 block with footnote overrides**

Open `src/frontend/static/css/style.css`. Find line 1190, which currently reads:

```css
#chapter-boundary_condition,
#chapter-unresolved,
#chapter-implication {
  grid-column: span 2;
}
```

Replace it with:

```css
#chapter-boundary_condition,
#chapter-unresolved,
#chapter-implication {
  grid-column: span 2;
  background: var(--surface-inset);
  border-color: var(--border-hairline);
  box-shadow: none;
  padding: var(--space-4);
}

/* Footnote cards don't lift on hover — they're supplementary */
#chapter-boundary_condition:hover,
#chapter-unresolved:hover,
#chapter-implication:hover {
  transform: none;
  box-shadow: none;
}

/* Downscale the section marker (§4, §5, §6 labels) */
#chapter-boundary_condition .conclusion__marker-no,
#chapter-boundary_condition .conclusion__marker-name,
#chapter-unresolved .conclusion__marker-no,
#chapter-unresolved .conclusion__marker-name,
#chapter-implication .conclusion__marker-no,
#chapter-implication .conclusion__marker-name {
  font-size: 9px;
}

/* Downscale body text */
#chapter-boundary_condition .conclusion__lead,
#chapter-unresolved .conclusion__lead,
#chapter-implication .conclusion__lead {
  font-size: 14px;
}

#chapter-boundary_condition .conclusion__para,
#chapter-unresolved .conclusion__para,
#chapter-implication .conclusion__para {
  font-size: 13px;
}

/* Unresolved has .conclusion--unresolved which sets its inner prose block to
   surface-inset + padding. With the card already surface-inset, that block
   becomes invisible — reset it to blend cleanly. */
#chapter-unresolved .conclusion__prose {
  background: transparent;
  padding: 0;
  border-radius: 0;
}
```

---

- [ ] **Step 2: Open the dev server and visually verify the three tiers**

If the dev server is not already running on port 5001:

```bash
cd /Users/Lovegood/Desktop/Unveiling
bash dev.sh &
```

Open `http://localhost:5001` in a browser. Click the demo link (or navigate to the analysis page with demo data pre-loaded). Scroll to the conclusions section and check:

**Expected visual result:**

| Chapter | Expected appearance |
|---|---|
| §1 核心结论 | Full-width, white elevated card, 18px lead, generous padding, subtle shadow |
| §2 这件事的走向 | Half-width, standard card bg (`surface-card`), 16px lead, normal padding |
| §3 难处在哪 | Half-width, standard card bg, orange-tinted marker and left border accent |
| §4 边界条件 | Third-width, **gray inset bg** (`surface-inset`), **14px lead**, **13px para**, no shadow, no hover lift |
| §5 还没回答清楚的 | Third-width, gray inset bg, 14px italic lead, 13px para, prose block blends with card (no inner box) |
| §6 所以你应该 | Third-width, gray inset bg, 14px lead, 13px para, no shadow, no hover lift |

If §4–6 look the same visual weight as §2–3 (i.e., the inset background isn't visible), check that the browser isn't serving a cached CSS file. Hard-refresh with `Cmd+Shift+R`.

---

- [ ] **Step 3: Check mobile breakpoint at 960px**

In browser DevTools, set the viewport width to 900px (below the 960px breakpoint). Verify:

- All six chapters collapse to `grid-column: 1/-1` (full width, stacked)
- §4–6 still show the gray inset background and smaller font sizes
- §1 still shows the elevated card with generous padding

The existing `@media (max-width: 960px)` block at line 1196 only overrides `grid-column` — it does not touch background or font sizes, so the footnote tier remains visible on mobile. This is correct and requires no additional CSS.

---

- [ ] **Step 4: Commit**

```bash
git add src/frontend/static/css/style.css
git commit -m "style: add footnote visual tier for conclusion chapters §4-6"
```

Expected output: `1 file changed, ~30 insertions(+), 5 deletions(-)`

---

## Task 2: Verify Evidence Display Lifecycle (No Code Changes)

**Context:** `renderScatter()` in `app.js:1441` already implements the lifecycle: when ≥2 plottable cases exist, it calls `show(scatterSection)` + `hide(casesSection)`. When insufficient cases exist, it falls back to `show(casesSection)`. `transitionToResult()` at line 1167 adds `is-complete` to casesSection before calling `renderScatter`. No code edits needed — this is a smoke test.

**Files:**
- Read-only: `src/frontend/static/js/app.js`

---

- [ ] **Step 5: Run the demo and observe evidence section lifecycle**

With the dev server running (`http://localhost:5001`), click the demo button on the home screen. Watch the analysis page as it streams:

**During analysis (exploration phase):**
- The `.cases` section (id=`cases`) should be **visible**, streaming evidence cards in real-time as they arrive
- The scatter chart section (id=`scatter`) should be **hidden**

**After analysis completes (transitionToResult fires):**
- The `.cases` section should become **hidden** (removed from view by `hide(dom.casesSection)` inside `renderScatter`)
- The scatter chart (id=`scatter`) should appear with dots plotted
- The `#scatter-cards` section below the chart should show the **complete** list of all evidence cards

If the cases section remains visible after the scatter chart appears, check the browser console for JS errors during `renderScatter`. The most likely cause is fewer than 2 cases having valid `era`/`distance` fields.

---

- [ ] **Step 6: Confirm scatter-cards completeness**

After the demo completes, scroll to the scatter chart. Below the chart (below the legend), `#scatter-cards` should list **all** evidence cases — count them and compare to the counter shown in the cases section header during analysis (e.g., "8条").

If counts match: ✓ done.  
If `#scatter-cards` is empty: check `renderScatter()` at app.js:1627 — the loop `plotCases.forEach(... dom.scatterCards.appendChild(buildScatterCard(e)))` populates it. If `plotCases` is empty (all cases filtered out by the `e.era !== 'future'` check at line 1448), the demo evidence data may need `era` fields added — but this is outside the scope of this plan.

---

- [ ] **Step 7: No commit needed**

Task 2 is verification only. If everything looks correct, the plan is complete.

If a bug is found during verification (e.g., cases section doesn't hide), that is a separate bug fix outside this plan's scope — file it as a new issue and do not patch it here.

---

## Done Criteria

- [ ] Opening the demo in a browser shows a visually clear three-tier conclusion hierarchy
- [ ] §1 is the most visually prominent card
- [ ] §4–6 are noticeably lighter (gray bg, smaller text, no shadow, no hover lift) than §2–3
- [ ] On a 900px viewport, all cards stack full-width while §4–6 retain their footnote styling
- [ ] After demo completes, only `#scatter-cards` shows evidence (not both scatter-cards + cases list simultaneously)
- [ ] Commit `style: add footnote visual tier for conclusion chapters §4-6` is on `main`
