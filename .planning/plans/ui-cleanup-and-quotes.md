# Plan: Unveiling analysis page cleanup, quote expansion, and code tidy

## Global Constraints
- Keep changes scoped to `src/frontend/templates/index.html`, `src/frontend/static/css/style.css`, and `src/frontend/static/js/app.js`.
- Preserve the existing warm-cream editorial aesthetic; do not introduce new colors, fonts, or motion language.
- All animations must continue to honor `prefers-reduced-motion: reduce`.
- Bilingual i18n is required: every new user-facing string needs keys in both `中文` and `English`.
- Verify visual result in the browser before committing.
- Commits should be atomic and follow the existing conventional-commit style.

## Task 1: Remove meaningless blank space on the analysis result page

### Goal
Eliminate the large blank strip visible below the conclusion chapters and above the analysis footer in the demo/result view.

### Acceptance Criteria
- [ ] Identify the element(s) causing the blank strip (likely `.quote-card`, `.analysis__transition`, `.recap`, or combined margins).
- [ ] Remove or collapse the source of the blank space without breaking the waiting-state layout.
- [ ] Ensure `.analysis__foot` sits directly below `.conclusions`/`.recap` with only the intended `margin-top`.
- [ ] Verify in browser at both desktop and mobile widths.

### Notes
The user highlighted a tall blank area between the conclusion text and the "重新开始" footer. Check whether a hidden-but-still-flowing element, a duplicated margin, or an empty section is responsible.

## Task 2: Expand waiting-state quote carousel texts

### Goal
Add more quotes to the carousel shown while the analysis is waiting for its first content.

### Acceptance Criteria
- [ ] Expand `QUOTES` in `app.js` from 6 to at least 10 entries.
- [ ] Add matching i18n keys in both languages for new quote tags and texts.
- [ ] New quotes should fit the existing tags (`quoteTagDesign`, `quoteTagMethod`, `quoteTagPhilosophy`) or new appropriately named tags.
- [ ] Keep quote length similar to existing ones so the typewriter effect timing remains pleasant.
- [ ] Verify the carousel cycles through all quotes in the browser.

### Notes
Existing quote themes: design provenance, Ti/Ne methodology, structural-transfer philosophy. Suggested additions: historical perspective, pattern recognition, the role of distance/analogy, user question quality, and cross-domain thinking.

## Task 3: Code tidy — remove dead code and unused rules

### Goal
Clean up accumulated dead code, commented-out sections, and unused CSS classes from the frontend.

### Acceptance Criteria
- [ ] Remove the commented-out "Cases feed" CSS block and any other dead comments.
- [ ] Audit CSS for unused classes (e.g., `.home-form__lang`, `.home-form__lang-option`, `.lens-map__*`) and remove confirmed-unused rules.
- [ ] Audit JS for unused helper functions or stale variables and remove confirmed-unused code.
- [ ] Do not remove code that is referenced by other parts of the system.
- [ ] Run the app and confirm no console errors.
