"""Render a Unveiling Analysis Deck (Mode D) from an analysis payload.

The deck spec lives in ``skills/frontend-slides/UNVEILING_DECK_RECIPE.md``.
Every user-visible string routes through ``UNVEILING_VOCAB.md`` — this module
holds those mappings as Python constants so we don't drift.

Public API::

    generate_slides(source, output_path=None, *, embed=False) -> Path | str

``source`` can be either an analysis ``State`` (legacy CLI callers in
``main.py``) or a payload dict already produced by
``frontend.payload.serialize_state``. When ``output_path`` is omitted, the
function returns the HTML string instead of writing to disk — this is how the
Flask route serves the deck inside an iframe.

The generator is intentionally template-free (no Jinja). f-strings + manual
``html.escape`` keep the rendering boundary auditable, which matters because
the same payload is also displayed elsewhere — divergence between the two
paths is exactly what we don't want.
"""

from __future__ import annotations

import html
import re
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Vocab — single source of truth for user-visible strings.
# Mirror of skills/frontend-slides/UNVEILING_VOCAB.md §1-§6.
# ---------------------------------------------------------------------------

VOCAB_PHASE: dict[str, str] = {
    "inception": "刚开始",
    "exploration": "展开找",
    "convergence": "收尾",
}

VOCAB_SUB_QUESTION_STATUS: dict[str, str] = {
    "untouched": "还没看",
    "exploring": "还在看",
    "closed": "想清楚了",
    "stuck": "卡住了",
}

VOCAB_EVIDENCE_LAYER: dict[str, str] = {
    "phenomenon": "表面",
    "mechanism": "怎么运作",
    "structure": "底层规律",
}

VOCAB_EVIDENCE_CONFIDENCE: dict[str, str] = {
    "strong": "最有分量",
    "medium": "中等",
    "weak": "较弱",
    "unexpected": "意外的一条",
}

VOCAB_PREDICTION_STATUS: dict[str, str] = {
    "pending": "还没试过",
    "supported": "对上了",
    "refuted": "被推翻了",
    "modified": "部分对、改过了",
}

# Empty-fallback copy — mirror of UNVEILING_DECK_RECIPE.md §3.
EMPTY_FALLBACK: dict[str, str] = {
    "convergent_finding": "这一轮没收敛到一个清晰的结论。可能是问得太大,也可能是材料还不够。",
    "tension": "这次没找到明显的矛盾点 —— 这本身就是信号:要么问题方向比较一致,要么我们还没看到对立面。",
    "boundary_condition": "没列出明显的边界条件。意味着结论的适用范围还没被压力测试过。",
    "evidence": "这一轮没沉淀出有分量的证据条目。",
    "unresolved": "这次没有明显卡住的小问题。",
    "implication": "这次没生成具体的提醒。如果你对结论有共鸣,可以从「拉扯之处」那一页继续追问。",
}

# Sub-question priority for the "你问的是" 5-bullet truncation.
# Lower value = surface first.
SUB_QUESTION_PRIORITY: dict[str, int] = {
    "stuck": 0,        # surface what's blocking
    "exploring": 1,    # active work
    "closed": 2,       # answered
    "untouched": 3,    # the rest
}

# ---------------------------------------------------------------------------
# Paths & static assets.
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_VIEWPORT_CSS_PATH = (
    _PROJECT_ROOT / "skills" / "frontend-slides" / "viewport-base.css"
)


def _load_viewport_css() -> str:
    """Load the shared viewport-fit base CSS at runtime.

    The skill file is the single source of truth — we don't copy its content
    into Python because it drifts. If the file is missing (skill folder moved
    or stripped), fall back to a comment so the deck still renders.
    """
    try:
        return _VIEWPORT_CSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return "/* viewport-base.css unavailable at render time */"


# ---------------------------------------------------------------------------
# Unveiling Paper preset CSS — mirror of STYLE_PRESETS.md §13.
# Must stay in sync with frontend/static/css/style.css :root.
# ---------------------------------------------------------------------------

UNVEILING_PAPER_CSS = """
:root {
    /* Canvas */
    --bg-cream: #faf7f0;
    --bg-sand: #f0ebe0;
    --surface-card: #ffffff;
    --surface-inset: #f5f1e8;

    /* Ink */
    --ink-primary: #2d2a26;
    --ink-secondary: #6b6660;
    --ink-tertiary: #a8a39b;

    /* Tension exclusive */
    --accent-tension: #ff6b35;
    --accent-tension-soft: rgba(255, 107, 53, 0.08);
    --accent-tension-border: rgba(255, 107, 53, 0.25);

    /* Status */
    --status-closed: #4a7c59;
    --status-exploring: #c8941a;
    --status-untouched: #a8a39b;
    --status-stuck: #8b3a3a;

    /* Layer */
    --layer-structure: #3a5a6c;
    --layer-mechanism: #6c5b3a;
    --layer-phenomenon: #a8a39b;

    /* Shadows */
    --shadow-sm: 0 1px 2px rgba(45, 42, 38, 0.04);
    --shadow-md: 0 2px 8px rgba(45, 42, 38, 0.06);
    --shadow-lg: 0 8px 24px rgba(45, 42, 38, 0.08);

    /* Type voices */
    --font-serif: "Source Han Serif SC", "Songti SC", "Noto Serif CJK SC", Georgia, serif;
    --font-sans: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB",
        "Microsoft YaHei", "Helvetica Neue", sans-serif;
    --font-mono: "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace;

    /* Hero / section type scale (clamps obey viewport-base invariants) */
    --hero-size: clamp(2rem, 5vw, 3rem);
    --section-size: clamp(1.4rem, 3vw, 1.625rem);
    --quote-size: clamp(1.1rem, 2.4vw, 1.375rem);
    --meta-size: clamp(0.7rem, 1.2vw, 0.75rem);
}

body {
    margin: 0;
    background: var(--bg-cream);
    color: var(--ink-primary);
    font-family: var(--font-sans);
    font-size: var(--body-size);
    line-height: 1.55;
}

.slide {
    background: var(--bg-cream);
    padding: var(--slide-padding);
    justify-content: center;
}

.slide.bg-sand,
.slide--unresolved,
.slide--empty {
    background: var(--bg-sand);
}

.slide-inner {
    max-width: min(720px, 90vw);
    margin: 0 auto;
    width: 100%;
}

.hero-serif {
    font-family: var(--font-serif);
    font-size: var(--hero-size);
    font-weight: 400;
    line-height: 1.3;
    color: var(--ink-primary);
    margin: 0;
}

.section-serif {
    font-family: var(--font-serif);
    font-size: var(--section-size);
    font-weight: 600;
    color: var(--ink-primary);
    margin: 0 0 var(--content-gap);
}

.kicker-sans {
    font-family: var(--font-sans);
    font-size: var(--body-size);
    color: var(--ink-secondary);
    margin: 0 0 var(--element-gap);
}

.kicker-mono {
    font-family: var(--font-mono);
    font-size: var(--meta-size);
    color: var(--ink-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: var(--content-gap) 0 0;
}

.body-serif {
    font-family: var(--font-serif);
    font-size: var(--body-size);
    line-height: 1.7;
    color: var(--ink-primary);
}

.pull-quote {
    font-family: var(--font-serif);
    font-size: var(--quote-size);
    font-style: italic;
    line-height: 1.55;
    color: var(--ink-primary);
    margin: 0;
    padding: 0 0 0 var(--element-gap);
}

.rule-ink {
    border-left: 3px solid var(--ink-primary);
    padding-left: clamp(0.75rem, 2vw, 1.25rem);
}

.rule-tension {
    border-left: 4px solid var(--accent-tension);
    padding-left: clamp(0.75rem, 2vw, 1.25rem);
}

.rule-tension-soft {
    border-left: 4px solid var(--accent-tension);
    background: var(--accent-tension-soft);
    padding: clamp(0.5rem, 1.5vw, 1rem) clamp(0.75rem, 2vw, 1.25rem);
    border-radius: 0 4px 4px 0;
}

.mode-badge {
    position: absolute;
    top: clamp(0.75rem, 2vw, 1.5rem);
    right: clamp(0.75rem, 2vw, 1.5rem);
    font-family: var(--font-mono);
    font-size: var(--meta-size);
    color: var(--ink-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 0.25rem 0.5rem;
    border: 1px solid var(--ink-tertiary);
    border-radius: 2px;
}

/* ---- Sub-question list (slide 02 / slide 10) ---- */
.sub-question-list,
.stuck-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: clamp(0.5rem, 1.4vh, 1rem);
}

.sub-question-list li,
.stuck-list li {
    display: flex;
    align-items: baseline;
    gap: clamp(0.5rem, 1vw, 0.75rem);
    font-size: var(--body-size);
}

.status-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
    background: var(--status-untouched);
}
.status-dot[data-status="closed"]    { background: var(--status-closed); }
.status-dot[data-status="exploring"] { background: var(--status-exploring); }
.status-dot[data-status="stuck"]     { background: var(--status-stuck); }
.status-dot[data-status="untouched"] { background: var(--status-untouched); }

.sub-question-text {
    flex: 1;
    color: var(--ink-primary);
}

.sub-question-status-label {
    font-family: var(--font-mono);
    font-size: var(--meta-size);
    color: var(--ink-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
}

/* ---- Boundary cards (slide 05) ---- */
.boundary-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));
    gap: var(--element-gap);
}

.boundary-card {
    background: var(--surface-card);
    border: 1px solid var(--surface-inset);
    border-left: 3px solid var(--ink-secondary);
    padding: clamp(0.75rem, 2vw, 1.25rem);
    font-family: var(--font-serif);
    line-height: 1.6;
    box-shadow: var(--shadow-sm);
}

/* ---- Lens evolution (slide 06) ---- */
.lens-chain {
    margin-bottom: var(--content-gap);
}

.lens-version {
    display: flex;
    align-items: baseline;
    gap: clamp(0.5rem, 1.5vw, 1rem);
    padding: clamp(0.4rem, 1vh, 0.75rem) 0;
    border-bottom: 1px solid var(--surface-inset);
}

.version-mono {
    font-family: var(--font-mono);
    font-size: var(--meta-size);
    color: var(--ink-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    flex-shrink: 0;
}

.lens-name-serif {
    font-family: var(--font-serif);
    font-weight: 600;
    color: var(--ink-primary);
    flex-shrink: 0;
}

.lens-rationale-sans {
    font-family: var(--font-sans);
    font-size: var(--small-size);
    color: var(--ink-secondary);
    line-height: 1.5;
}

.lens-arrow {
    display: block;
    text-align: center;
    color: var(--ink-tertiary);
    margin: clamp(0.2rem, 0.5vh, 0.4rem) 0;
}

/* ---- Evidence cards (slide 07 / slide 08) ---- */
.evidence-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--element-gap);
}

.evidence-card,
.unexpected-card {
    background: var(--surface-card);
    border: 1px solid var(--surface-inset);
    padding: clamp(0.75rem, 2vw, 1.25rem);
    box-shadow: var(--shadow-sm);
    border-radius: 4px;
    display: flex;
    flex-direction: column;
    gap: clamp(0.3rem, 1vh, 0.6rem);
}

.unexpected-card {
    background: var(--surface-card);
    border-left: 4px solid var(--accent-tension);
}

.layer-pill {
    display: inline-block;
    font-family: var(--font-mono);
    font-size: var(--meta-size);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 2px 6px;
    border: 1px solid currentColor;
    border-radius: 2px;
    align-self: flex-start;
}
.layer-pill[data-layer="structure"]  { color: var(--layer-structure); }
.layer-pill[data-layer="mechanism"]  { color: var(--layer-mechanism); }
.layer-pill[data-layer="phenomenon"] { color: var(--layer-phenomenon); }

.evidence-body-serif {
    font-family: var(--font-serif);
    font-size: var(--body-size);
    line-height: 1.6;
    color: var(--ink-primary);
    margin: 0;
}

.confidence-meta-mono {
    font-family: var(--font-mono);
    font-size: var(--meta-size);
    color: var(--ink-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    align-self: flex-end;
}

/* ---- Prediction cards (slide 09) ---- */
.prediction-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: var(--element-gap);
}

.prediction-card {
    background: var(--surface-card);
    border: 1px solid var(--surface-inset);
    border-left: 3px solid var(--ink-secondary);
    padding: clamp(0.75rem, 2vw, 1.25rem);
    display: flex;
    flex-direction: column;
    gap: clamp(0.3rem, 1vh, 0.5rem);
}

.prediction-claim-serif {
    font-family: var(--font-serif);
    font-size: var(--body-size);
    font-weight: 600;
    line-height: 1.5;
    color: var(--ink-primary);
    margin: 0;
}

.killer-evidence-sans {
    font-family: var(--font-sans);
    font-size: var(--small-size);
    color: var(--ink-secondary);
    margin: 0;
}

.prediction-status {
    font-family: var(--font-mono);
    font-size: var(--meta-size);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 2px 6px;
    border: 1px solid currentColor;
    border-radius: 2px;
    align-self: flex-start;
    color: var(--ink-tertiary);
}
.prediction-status[data-status="supported"] { color: var(--status-closed); }
.prediction-status[data-status="refuted"]   { color: var(--status-stuck); }
.prediction-status[data-status="modified"]  { color: var(--status-exploring); }
.prediction-status[data-status="pending"]   { color: var(--ink-tertiary); }

/* ---- Signature slide (slide 12) ---- */
.slide--signature {
    background: var(--bg-cream);
    text-align: center;
}

.signature-mono {
    font-family: var(--font-mono);
    font-size: var(--small-size);
    color: var(--ink-secondary);
    margin: 0;
}

/* ---- Navigation UI (standalone mode only) ---- */
.nav-dots {
    position: fixed;
    bottom: clamp(1rem, 3vh, 2rem);
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    gap: 0.5rem;
    z-index: 10;
}
.nav-dots button {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    border: none;
    background: var(--ink-tertiary);
    opacity: 0.5;
    cursor: pointer;
    padding: 0;
    transition: opacity 0.2s ease, transform 0.2s ease;
}
.nav-dots button.active {
    opacity: 1;
    background: var(--ink-primary);
    transform: scale(1.3);
}

.keyboard-hint {
    position: fixed;
    bottom: clamp(0.5rem, 2vh, 1rem);
    right: clamp(0.5rem, 2vw, 1rem);
    font-family: var(--font-mono);
    font-size: var(--meta-size);
    color: var(--ink-tertiary);
    background: var(--surface-card);
    padding: 0.25rem 0.5rem;
    border-radius: 2px;
    border: 1px solid var(--surface-inset);
    z-index: 10;
}

.progress-bar {
    position: fixed;
    top: 0;
    left: 0;
    height: 2px;
    background: var(--ink-primary);
    transition: width 0.3s ease;
    z-index: 10;
}

/* ---- Embed mode: hide all chrome ---- */
body.embed .nav-dots,
body.embed .keyboard-hint,
body.embed .progress-bar {
    display: none;
}

/* Embed mode: keep scroll-snap on so each slide locks into view inside the
   iframe. We deviate from UNVEILING_DECK_RECIPE.md §5 (which assumes
   parent-controlled nav) — there is no parent-side controller, so the iframe
   itself owns scrolling. */
body.embed {
    overflow-x: hidden;
    overflow-y: auto;
}
body.embed html {
    scroll-snap-type: y mandatory;
}
"""

# Standalone-mode JS: arrow keys + click-to-advance + nav-dots + progress bar.
# In embed mode we don't emit this — see _render_html.
KEYBOARD_JS_STANDALONE = """
<script>
(function () {
    const slides = Array.from(document.querySelectorAll('.slide'));
    const dots = Array.from(document.querySelectorAll('.nav-dots button'));
    const progress = document.querySelector('.progress-bar');
    let current = 0;

    function goTo(i) {
        if (i < 0 || i >= slides.length) return;
        current = i;
        slides[i].scrollIntoView({ behavior: 'smooth', block: 'start' });
        dots.forEach((d, idx) => d.classList.toggle('active', idx === i));
        if (progress) {
            progress.style.width = ((i + 1) / slides.length * 100) + '%';
        }
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {
            e.preventDefault();
            goTo(current + 1);
        } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
            e.preventDefault();
            goTo(current - 1);
        }
    });

    document.addEventListener('click', (e) => {
        if (e.target.closest('button, a, .nav-dots')) return;
        goTo(current + 1);
    });

    dots.forEach((dot, i) => dot.addEventListener('click', () => goTo(i)));

    // Initialize progress on first paint.
    if (progress) progress.style.width = (1 / slides.length * 100) + '%';
})();
</script>
"""


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------

def _esc(value: Any) -> str:
    """HTML-escape any value, coercing to string first.

    None becomes empty string — empty-fallback handling is done by callers,
    not here, because what counts as "missing" depends on the slide.
    """
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def _truncate(text: str, limit: int) -> str:
    """Shorten a string to ``limit`` characters, appending an ellipsis."""
    if not text:
        return ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _split_boundary(text: str | None, max_items: int = 4) -> list[str]:
    """Split a boundary-condition paragraph into ≤``max_items`` bullets.

    Splits on Chinese 。/英文 ./;/；, drops empties, preserves order.
    """
    if not text:
        return []
    parts = re.split(r"[。\.;；]+", text)
    items = [p.strip() for p in parts if p.strip()]
    return items[:max_items]


def _phase_label(phase: str | None) -> str:
    if not phase:
        return ""
    return VOCAB_PHASE.get(phase, phase)


def _sub_question_label(status: str | None) -> str:
    if not status:
        return ""
    return VOCAB_SUB_QUESTION_STATUS.get(status, status)


def _evidence_layer_label(layer: str | None) -> str:
    if not layer:
        return ""
    return VOCAB_EVIDENCE_LAYER.get(layer, layer)


def _evidence_confidence_label(conf: str | None) -> str:
    if not conf:
        return ""
    return VOCAB_EVIDENCE_CONFIDENCE.get(conf, conf)


def _prediction_status_label(status: str | None) -> str:
    if not status:
        return ""
    return VOCAB_PREDICTION_STATUS.get(status, status)


def _prep_sub_questions(sub_qs: list[dict]) -> list[dict]:
    """Sort by (status priority, descending evidence_count) and clip to 5."""
    def key(sq: dict) -> tuple[int, int]:
        status = sq.get("status", "untouched")
        priority = SUB_QUESTION_PRIORITY.get(status, 9)
        evidence_count = sq.get("evidence_count", 0) or 0
        return (priority, -evidence_count)

    return sorted(sub_qs, key=key)[:5]


def _to_payload(source: Any) -> dict:
    """Normalize input to a payload dict.

    - dict → returned as-is (after a shallow sanity check)
    - State (or anything with model_dump) → serialized via frontend.payload
    """
    if isinstance(source, dict):
        return source

    # Lazy import — keeps the generator usable in environments where Flask /
    # full State models aren't available (the slide tests, for instance).
    from frontend.payload import serialize_state

    return serialize_state(source)


# ---------------------------------------------------------------------------
# Per-slide renderers.
# Each returns a complete <section class="slide">…</section> string.
# ---------------------------------------------------------------------------

def _slide(extra_class: str, inner_html: str, *, mode_badge: str = "") -> str:
    """Wrap inner content in the canonical .slide / .slide-inner shell."""
    badge_html = (
        f'<span class="mode-badge">{_esc(mode_badge)}</span>' if mode_badge else ""
    )
    return (
        f'<section class="slide {extra_class}">'
        f"{badge_html}"
        f'<div class="slide-inner">'
        f"{inner_html}"
        f"</div>"
        f"</section>"
    )


def _render_slide_01_cover(payload: dict) -> str:
    question = _esc(payload.get("driving_question") or "未命名的问题")
    mode = _phase_label(payload.get("phase"))
    inner = (
        f'<h1 class="hero-serif">{question}</h1>'
        f'<p class="kicker-mono">UNVEILING · 类比分析</p>'
    )
    return _slide("slide--cover", inner, mode_badge=mode)


def _render_slide_02_question(payload: dict) -> str:
    question = _esc(payload.get("driving_question") or "")
    sub_questions = _prep_sub_questions(payload.get("sub_questions") or [])

    if sub_questions:
        bullets = "".join(
            (
                f"<li>"
                f'<span class="status-dot" data-status="{_esc(sq.get("status", "untouched"))}"></span>'
                f'<span class="sub-question-text">{_esc(sq.get("content", ""))}</span>'
                f'<span class="sub-question-status-label">{_esc(_sub_question_label(sq.get("status")))}</span>'
                f"</li>"
            )
            for sq in sub_questions
        )
        list_html = f'<ul class="sub-question-list">{bullets}</ul>'
    else:
        list_html = (
            '<p class="kicker-sans">这个问题暂时没拆出小问题——它本身已经足够具体。</p>'
        )

    inner = (
        '<h2 class="section-serif">你问的是</h2>'
        f'<blockquote class="pull-quote rule-ink">{question}</blockquote>'
        '<p class="kicker-sans">我们把它拆成了这些小问题:</p>'
        f"{list_html}"
    )
    return _slide("slide--question", inner)


def _render_slide_03_takeaway(payload: dict) -> str:
    conclusion = payload.get("conclusion") or {}
    finding = (conclusion.get("convergent_finding") or "").strip()

    if finding:
        body = f'<p class="hero-serif rule-ink">{_esc(finding)}</p>'
        return _slide("slide--takeaway", _wrap_section("总的来看", body))

    # Empty fallback — sand panel + concession copy.
    body = f'<p class="body-serif">{_esc(EMPTY_FALLBACK["convergent_finding"])}</p>'
    return _slide("slide--takeaway slide--empty", _wrap_section("总的来看", body))


def _render_slide_04_tension(payload: dict) -> str:
    conclusion = payload.get("conclusion") or {}
    tension = (conclusion.get("tension") or "").strip()

    if tension:
        body = f'<blockquote class="pull-quote rule-tension">{_esc(tension)}</blockquote>'
        return _slide("slide--tension", _wrap_section("拉扯之处", body))

    body = f'<p class="body-serif">{_esc(EMPTY_FALLBACK["tension"])}</p>'
    return _slide("slide--tension slide--empty", _wrap_section("拉扯之处", body))


def _render_slide_05_boundary(payload: dict) -> str:
    conclusion = payload.get("conclusion") or {}
    items = _split_boundary(conclusion.get("boundary_condition"))

    if items:
        bullets = "".join(f'<li class="boundary-card">{_esc(item)}</li>' for item in items)
        body = f'<ul class="boundary-list">{bullets}</ul>'
        return _slide("slide--boundary", _wrap_section("什么时候不成立", body))

    body = f'<p class="body-serif">{_esc(EMPTY_FALLBACK["boundary_condition"])}</p>'
    return _slide("slide--boundary slide--empty", _wrap_section("什么时候不成立", body))


def _render_slide_06_lens_evolution(payload: dict) -> str | None:
    chains = payload.get("lens_chains") or []
    if not chains:
        return None

    chain_blocks: list[str] = []
    for chain in chains[:2]:
        versions = (chain.get("chain") or [])[:3]
        if not versions:
            continue
        rows = []
        for i, lens in enumerate(versions, start=1):
            rows.append(
                f'<div class="lens-version">'
                f'<span class="version-mono">v{i}</span>'
                f'<span class="lens-name-serif">{_esc(lens.get("name", ""))}</span>'
                f'<span class="lens-rationale-sans">{_esc(_truncate(lens.get("rationale") or "", 60))}</span>'
                f"</div>"
            )
            if i < len(versions):
                rows.append('<span class="lens-arrow">↓</span>')
        chain_blocks.append(f'<div class="lens-chain">{"".join(rows)}</div>')

    if not chain_blocks:
        return None

    body = "".join(chain_blocks)
    return _slide("slide--lens-evolution", _wrap_section("我们换过几次角度", body))


def _render_slide_07_evidence(payload: dict) -> str:
    evidence = payload.get("evidence") or []
    if evidence:
        cards = []
        for e in evidence[:3]:
            layer = e.get("layer") or ""
            conf = e.get("confidence") or ""
            cards.append(
                f'<article class="evidence-card">'
                f'<span class="layer-pill" data-layer="{_esc(layer)}">{_esc(_evidence_layer_label(layer))}</span>'
                f'<p class="evidence-body-serif">{_esc(e.get("content", ""))}</p>'
                f'<span class="confidence-meta-mono">分量:{_esc(_evidence_confidence_label(conf))}</span>'
                f"</article>"
            )
        body = f'<div class="evidence-grid">{"".join(cards)}</div>'
        return _slide("slide--evidence", _wrap_section("我们找到了什么", body))

    body = f'<p class="body-serif">{_esc(EMPTY_FALLBACK["evidence"])}</p>'
    return _slide("slide--evidence slide--empty", _wrap_section("我们找到了什么", body))


def _render_slide_08_unexpected(payload: dict) -> str | None:
    evidence = payload.get("evidence") or []
    unexpected = [e for e in evidence if e.get("is_unexpected")]
    if not unexpected:
        return None

    cards = []
    for e in unexpected[:2]:
        layer = e.get("layer") or ""
        cards.append(
            f'<article class="unexpected-card">'
            f'<p class="evidence-body-serif">{_esc(e.get("content", ""))}</p>'
            f'<span class="layer-pill" data-layer="{_esc(layer)}">{_esc(_evidence_layer_label(layer))}</span>'
            f"</article>"
        )

    inner = (
        '<h2 class="section-serif">意外发现</h2>'
        '<p class="kicker-sans">这些没在原本的设想里:</p>'
        f'{"".join(cards)}'
    )
    return _slide("slide--unexpected", inner)


def _render_slide_09_predictions(payload: dict) -> str | None:
    preds = [
        p for p in (payload.get("predictions") or [])
        if (p.get("killer_evidence") or "").strip()
    ]
    if not preds:
        return None

    items = []
    for p in preds[:3]:
        status = p.get("status") or "pending"
        items.append(
            f'<li class="prediction-card">'
            f'<p class="prediction-claim-serif">{_esc(p.get("claim", ""))}</p>'
            f'<p class="killer-evidence-sans">决定性证据:{_esc(p.get("killer_evidence", ""))}</p>'
            f'<span class="prediction-status" data-status="{_esc(status)}">'
            f'{_esc(_prediction_status_label(status))}</span>'
            f"</li>"
        )
    body = f'<ul class="prediction-list">{"".join(items)}</ul>'
    return _slide("slide--predictions", _wrap_section("几个敢打赌的猜想", body))


def _render_slide_10_unresolved(payload: dict) -> str:
    conclusion = payload.get("conclusion") or {}
    unresolved = (conclusion.get("unresolved") or "").strip()
    stuck = [
        sq for sq in (payload.get("sub_questions") or [])
        if sq.get("status") == "stuck"
    ]

    parts: list[str] = []
    if unresolved:
        parts.append(f'<p class="body-serif">{_esc(unresolved)}</p>')

    if stuck:
        rows = "".join(
            (
                f'<li>'
                f'<span class="status-dot" data-status="stuck"></span>'
                f'<span class="sub-question-text">{_esc(sq.get("content", ""))}</span>'
                f"</li>"
            )
            for sq in stuck
        )
        parts.append('<p class="kicker-sans">这几个小问题卡住了:</p>')
        parts.append(f'<ul class="stuck-list">{rows}</ul>')

    if not parts:
        parts.append(f'<p class="body-serif">{_esc(EMPTY_FALLBACK["unresolved"])}</p>')

    body = "".join(parts)
    return _slide("slide--unresolved", _wrap_section("还没想清楚的", body))


def _render_slide_11_implication(payload: dict) -> str:
    conclusion = payload.get("conclusion") or {}
    implication = (conclusion.get("implication") or "").strip()

    if implication:
        body = f'<p class="hero-serif rule-ink">{_esc(implication)}</p>'
        return _slide("slide--implication", _wrap_section("给你的提醒", body))

    body = f'<p class="body-serif">{_esc(EMPTY_FALLBACK["implication"])}</p>'
    return _slide("slide--implication slide--empty", _wrap_section("给你的提醒", body))


def _render_slide_12_signature(payload: dict) -> str:
    integrity = payload.get("integrity") or {}
    rounds = integrity.get("round_count") or 0
    tokens = integrity.get("token_spent") or 0
    chain_count = len(payload.get("lens_chains") or [])

    inner = (
        '<p class="signature-mono">'
        f'走了 {int(rounds)} 回合 · 用了 {int(tokens)} token · 换过 {chain_count} 次角度'
        '</p>'
        '<p class="kicker-mono">UNVEILING</p>'
    )
    return _slide("slide--signature", inner)


def _wrap_section(title: str, body_html: str) -> str:
    return f'<h2 class="section-serif">{_esc(title)}</h2>{body_html}'


# ---------------------------------------------------------------------------
# Top-level renderer.
# ---------------------------------------------------------------------------

def _render_slides(payload: dict) -> list[str]:
    """Return the list of rendered <section> strings in canonical order."""
    pipeline = [
        _render_slide_01_cover(payload),
        _render_slide_02_question(payload),
        _render_slide_03_takeaway(payload),
        _render_slide_04_tension(payload),
        _render_slide_05_boundary(payload),
        _render_slide_06_lens_evolution(payload),   # optional
        _render_slide_07_evidence(payload),
        _render_slide_08_unexpected(payload),       # optional
        _render_slide_09_predictions(payload),      # optional
        _render_slide_10_unresolved(payload),
        _render_slide_11_implication(payload),
        _render_slide_12_signature(payload),
    ]
    return [s for s in pipeline if s]


def _render_chrome(slide_count: int) -> str:
    """Nav-dots + keyboard-hint + progress bar — standalone-mode chrome."""
    dots = "".join(
        f'<button data-index="{i}" aria-label="第 {i + 1} 页"></button>'
        for i in range(slide_count)
    )
    return (
        f'<div class="progress-bar" style="width: 0;"></div>'
        f'<nav class="nav-dots">{dots}</nav>'
        f'<span class="keyboard-hint">← → 切换 · Space 下一张</span>'
    )


def _render_html(payload: dict, *, embed: bool) -> str:
    """Assemble the full HTML document."""
    title = payload.get("driving_question") or "Unveiling 分析结果"
    slides = _render_slides(payload)
    slides_html = "\n".join(slides)

    chrome_html = "" if embed else _render_chrome(len(slides))
    keyboard_js = "" if embed else KEYBOARD_JS_STANDALONE
    body_class = "embed" if embed else "standalone"

    viewport_css = _load_viewport_css()

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UNVEILING · {_esc(_truncate(title, 40))}</title>
<style>
{viewport_css}
{UNVEILING_PAPER_CSS}
</style>
</head>
<body class="{body_class}">
{chrome_html}
{slides_html}
{keyboard_js}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------

def generate_slides(
    source: Any,
    output_path: Path | str | None = None,
    *,
    embed: bool = False,
) -> Path | str:
    """Render a Unveiling Analysis Deck from a State or payload dict.

    Parameters
    ----------
    source
        Either an analysis ``State`` (legacy CLI flow) or a payload dict
        produced by ``frontend.payload.serialize_state``.
    output_path
        Where to write the HTML. When ``None``, returns the HTML string
        instead of touching the filesystem — used by the Flask deck route.
    embed
        ``True`` when the deck will be loaded inside an iframe on the result
        page. Hides nav-dots/keyboard-hint/progress-bar and locks body
        overflow. Default ``False`` for standalone single-file decks.

    Returns
    -------
    Path
        If ``output_path`` was provided — the path that was written.
    str
        Otherwise — the rendered HTML.
    """
    payload = _to_payload(source)
    html_doc = _render_html(payload, embed=embed)

    if output_path is None:
        return html_doc

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_doc, encoding="utf-8")
    return output_path
