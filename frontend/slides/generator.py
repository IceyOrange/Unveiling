from __future__ import annotations

from pathlib import Path
from datetime import datetime

from models.state import State


def generate_slides(state: State, output_path: Path | str, style_preset: str = "swiss-modern") -> Path:
    """Generate a self-contained HTML slide deck from analysis state.

    MVP: single-page HTML with all conclusions, issue tree, and hypotheses.
    """
    output_path = Path(output_path)

    # Build latest node lookup
    latest = {}
    for node in state.issue_tree:
        latest[node.id] = node

    driving = next((n for n in latest.values() if n.parent_id is None), None)
    sub_questions = [n for n in latest.values() if n.parent_id is not None]

    lenses = [h for h in state.hypothesis_zone if hasattr(h, "name")]
    predictions = [h for h in state.hypothesis_zone if hasattr(h, "claim")]

    conclusion = state.conclusion_zone[-1] if state.conclusion_zone else None

    # HTML generation
    html = _build_html(
        driving=driving,
        sub_questions=sub_questions,
        lenses=lenses,
        predictions=predictions,
        conclusion=conclusion,
        token_spent=state.token_spent,
        round_count=state.round_count,
        style_preset=style_preset,
    )

    output_path.write_text(html, encoding="utf-8")
    return output_path


def _build_html(driving, sub_questions, lenses, predictions, conclusion, token_spent, round_count, style_preset):
    _styles = {
        "swiss-modern": {
            "bg": "#ffffff", "text": "#1a1a1a", "accent": "#ff3300",
            "secondary": "#f5f5f5", "muted": "#666666",
        },
        "bold-signal": {
            "bg": "#1a1a1a", "text": "#ffffff", "accent": "#FF5722",
            "secondary": "#2d2d2d", "muted": "#aaaaaa",
        },
    }
    s = _styles.get(style_preset, _styles["swiss-modern"])

    # Issue tree rows
    issue_rows = ""
    for sq in sub_questions:
        status_color = {"untouched": s["muted"], "exploring": s["accent"], "closed": "#22c55e", "stuck": "#eab308"}.get(sq.node_status.value, s["muted"])
        issue_rows += f'<div class="sq"><span class="status" style="color:{status_color}">●</span> {sq.content}</div>\n'

    # Lenses
    lens_rows = ""
    for lens in lenses:
        lens_rows += f'<div class="lens"><strong>{lens.name}</strong><p>{lens.rationale}</p></div>\n'

    # Predictions
    pred_rows = ""
    for p in predictions:
        pred_rows += f'<div class="pred"><strong>{p.claim}</strong><br><span class="muted">[{p.prediction_status.value}]</span></div>\n'

    # Conclusion
    conclusion_html = ""
    if conclusion:
        conclusion_html = f"""
        <div class="card conclusion">
            <h2>Convergent Finding</h2>
            <p>{conclusion.convergent_finding}</p>
            <h3>Tension</h3>
            <p class="tension">{conclusion.tension}</p>
            <h3>Boundary Condition</h3>
            <p>{conclusion.boundary_condition}</p>
            <h3>Unresolved</h3>
            <p>{conclusion.unresolved}</p>
            <h3>Implication</h3>
            <p>{conclusion.implication}</p>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Unveiling — {driving.content if driving else 'Analysis'}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: {s['bg']};
    color: {s['text']};
    line-height: 1.6;
    padding: 2rem 1rem;
}}
.container {{ max-width: 800px; margin: 0 auto; }}
h1 {{ font-size: 2rem; margin-bottom: 0.5rem; }}
.meta {{ color: {s['muted']}; font-size: 0.875rem; margin-bottom: 2rem; }}
.card {{
    background: {s['secondary']};
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}}
.card h2 {{ font-size: 1.25rem; margin-bottom: 1rem; color: {s['accent']}; }}
.card h3 {{ font-size: 1rem; margin: 1rem 0 0.5rem; }}
.sq {{ padding: 0.5rem 0; border-bottom: 1px solid rgba(128,128,128,0.2); }}
.sq:last-child {{ border-bottom: none; }}
.status {{ margin-right: 0.5rem; }}
.lens {{ margin-bottom: 1rem; }}
.lens p {{ color: {s['muted']}; margin-top: 0.25rem; }}
.pred {{ padding: 0.75rem; background: rgba(128,128,128,0.05); border-radius: 8px; margin-bottom: 0.5rem; }}
.muted {{ color: {s['muted']}; }}
.tension {{ color: {s['accent']}; font-weight: 600; }}
.conclusion p {{ margin-bottom: 0.75rem; }}
</style>
</head>
<body>
<div class="container">
    <h1>{driving.content if driving else 'Analysis Result'}</h1>
    <div class="meta">
        Rounds: {round_count} | Tokens: {token_spent} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
    </div>

    <div class="card">
        <h2>Issue Tree ({len(sub_questions)} sub-questions)</h2>
        {issue_rows}
    </div>

    <div class="card">
        <h2>Lenses ({len(lenses)})</h2>
        {lens_rows or '<p class="muted">No lenses generated.</p>'}
    </div>

    <div class="card">
        <h2>Predictions ({len(predictions)})</h2>
        {pred_rows or '<p class="muted">No predictions generated.</p>'}
    </div>

    {conclusion_html}
</div>
</body>
</html>"""
