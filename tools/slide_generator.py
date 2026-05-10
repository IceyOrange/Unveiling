import json
from typing import Type, List
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class SlideGeneratorInput(BaseModel):
    topic: str = Field(..., description="The original analysis topic")
    lenses_json: str = Field(..., description="JSON array of lens name strings")
    vertical_instances_json: str = Field(..., description="JSON array of vertical discovered instances")
    horizontal_instances_json: str = Field(..., description="JSON array of horizontal discovered instances")
    vertical_comparisons_json: str = Field(..., description="JSON array of vertical pairwise comparisons")
    horizontal_comparisons_json: str = Field(..., description="JSON array of horizontal pairwise comparisons")
    validated_commonalities_json: str = Field(..., description="JSON array of validated commonalities")
    rejected_commonalities_json: str = Field(..., description="JSON array of rejected commonalities")
    insights_json: str = Field(..., description="JSON array of synthesis insights")
    core_thesis: str = Field(..., description="The core thesis")
    prediction: str = Field(..., description="Forward-looking prediction")
    recommendations_json: str = Field(..., description="JSON array of recommendation strings")
    style_preset: str = Field(default="swiss-modern", description="Style preset name")


STYLE_PRESETS = {
    "swiss-modern": {
        "bg_primary": "#ffffff",
        "bg_secondary": "#f5f5f5",
        "text_primary": "#0a0a0a",
        "text_secondary": "#555555",
        "accent": "#ff3300",
        "accent_light": "rgba(255, 51, 0, 0.1)",
        "font_display": "'Archivo', sans-serif",
        "font_body": "'Nunito', sans-serif",
        "font_url": "https://fonts.googleapis.com/css2?family=Archivo:wght@400;700;800&family=Nunito:wght@400;500;600&display=swap",
    },
    "bold-signal": {
        "bg_primary": "#1a1a1a",
        "bg_secondary": "#2d2d2d",
        "text_primary": "#ffffff",
        "text_secondary": "#aaaaaa",
        "accent": "#FF5722",
        "accent_light": "rgba(255, 87, 34, 0.2)",
        "font_display": "'Archivo Black', sans-serif",
        "font_body": "'Space Grotesk', sans-serif",
        "font_url": "https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Grotesk:wght@400;500&display=swap",
    },
    "neon-cyber": {
        "bg_primary": "#0a0f1c",
        "bg_secondary": "#111827",
        "text_primary": "#ffffff",
        "text_secondary": "#9ca3af",
        "accent": "#00ffcc",
        "accent_light": "rgba(0, 255, 204, 0.15)",
        "font_display": "'Clash Display', sans-serif",
        "font_body": "'Satoshi', sans-serif",
        "font_url": "https://api.fontshare.com/v2/css?f[]=clash-display@700&f[]=satoshi@400,500&display=swap",
    },
}


class SlideGeneratorTool(BaseTool):
    name: str = "slide_generator"
    description: str = (
        "Generates a complete HTML slide presentation from structured "
        "analogy analysis data. Produces a self-contained HTML file "
        "with inline CSS/JS following the frontend-slides framework patterns."
    )
    args_schema: Type[BaseModel] = SlideGeneratorInput

    def _run(self, **kwargs) -> str:
        topic = kwargs["topic"]
        lenses = self._parse_json_list(kwargs.get("lenses_json", "[]"))
        v_instances = self._parse_json_list(kwargs.get("vertical_instances_json", "[]"))
        h_instances = self._parse_json_list(kwargs.get("horizontal_instances_json", "[]"))
        v_comparisons = self._parse_json_list(kwargs.get("vertical_comparisons_json", "[]"))
        h_comparisons = self._parse_json_list(kwargs.get("horizontal_comparisons_json", "[]"))
        validated = self._parse_json_list(kwargs.get("validated_commonalities_json", "[]"))
        rejected = self._parse_json_list(kwargs.get("rejected_commonalities_json", "[]"))
        insights = self._parse_json_list(kwargs.get("insights_json", "[]"))
        core_thesis = kwargs.get("core_thesis", "")
        prediction = kwargs.get("prediction", "")
        recommendations = self._parse_json_list(kwargs.get("recommendations_json", "[]"))
        preset_name = kwargs.get("style_preset", "swiss-modern")

        style = STYLE_PRESETS.get(preset_name, STYLE_PRESETS["swiss-modern"])

        viewport_css = self._read_viewport_css()
        slides_html = self._build_all_slides(
            topic, lenses, v_instances, h_instances,
            v_comparisons, h_comparisons,
            validated, rejected, insights,
            core_thesis, prediction, recommendations,
        )
        html = self._assemble_html(topic, style, viewport_css, slides_html)

        output_dir = Path(__file__).parent.parent / "output"
        output_dir.mkdir(exist_ok=True)
        safe_name = topic.replace(" ", "_").replace("/", "-")[:50]
        output_path = output_dir / f"{safe_name}_analysis.html"
        output_path.write_text(html, encoding="utf-8")

        return f"Presentation generated: {output_path}"

    def _read_viewport_css(self) -> str:
        css_path = Path(__file__).parent.parent / "skills" / "frontend-slides" / "viewport-base.css"
        if css_path.exists():
            return css_path.read_text()
        return ""

    def _parse_json_list(self, raw: str) -> list:
        if not raw or raw == "null":
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
            return []
        except Exception:
            return []

    def _safe_str(self, val) -> str:
        if val is None:
            return ""
        return str(val)

    def _safe_list(self, val) -> list:
        if isinstance(val, list):
            return [str(v) for v in val if v is not None and str(v).strip()]
        if isinstance(val, str) and val.strip():
            return [val]
        return []

    def _build_all_slides(self, topic, lenses, v_inst, h_inst,
                          v_comp, h_comp, validated, rejected,
                          insights, thesis, prediction, recs) -> str:
        slides = []
        slides.append(self._title_slide(topic, lenses))
        if lenses:
            slides.append(self._lenses_overview_slide(lenses))
        if v_inst:
            slides.append(self._vertical_timeline_slide(v_inst))
        if v_comp:
            slides.append(self._vertical_comparison_slide(v_comp))
        if h_inst:
            slides.append(self._horizontal_map_slide(h_inst))
        if h_comp:
            slides.append(self._horizontal_comparison_slide(h_comp))
        if validated or rejected:
            slides.append(self._causal_validation_slide(validated, rejected))
        if thesis:
            slides.append(self._thesis_slide(thesis))
        if insights:
            for i, insight in enumerate(insights[:6]):
                slide = self._insight_slide(insight, i + 1)
                if slide:
                    slides.append(slide)
        if prediction or recs:
            slides.append(self._prediction_slide(prediction, recs))
        slides.append(self._closing_slide(topic))
        return "\n".join(slides)

    # ── Individual slide builders ──

    def _title_slide(self, topic: str, lenses: list) -> str:
        lens_text = " / ".join(lenses[:3]) if lenses else "Analogy Analysis"
        return f'''
    <section class="slide title-slide">
      <div class="slide-content" style="justify-content: center; align-items: center; text-align: center;">
        <p class="reveal" style="font-size: var(--small-size); letter-spacing: 0.2em; text-transform: uppercase; opacity: 0.6;">Unveiling</p>
        <h1 class="reveal" style="font-size: var(--title-size); margin-top: var(--element-gap); max-width: 80%;">{self._esc(topic)}</h1>
        <p class="reveal" style="font-size: var(--h3-size); margin-top: var(--content-gap); opacity: 0.7;">{self._esc(lens_text)}</p>
        <div class="reveal" style="width: 60px; height: 3px; background: var(--accent); margin-top: var(--content-gap);"></div>
      </div>
    </section>'''

    def _lenses_overview_slide(self, lenses: list) -> str:
        items = ""
        for i, lens in enumerate(lenses):
            lens_str = self._safe_str(lens)
            items += f'''
        <div class="reveal lens-card" style="background: var(--accent-light); border-left: 4px solid var(--accent); padding: clamp(0.5rem, 1.5vw, 1rem) clamp(0.75rem, 2vw, 1.5rem); margin-bottom: var(--element-gap);">
          <p style="font-size: var(--small-size); opacity: 0.6;">Lens {i+1}</p>
          <p style="font-size: var(--h3-size); font-weight: 700;">{self._esc(lens_str)}</p>
        </div>'''
        return f'''
    <section class="slide">
      <div class="slide-content">
        <p class="reveal" style="font-size: var(--small-size); letter-spacing: 0.15em; text-transform: uppercase; opacity: 0.5;">Abstraction</p>
        <h2 class="reveal" style="font-size: var(--h2-size); margin-bottom: var(--content-gap);">Abstract Lenses</h2>
        <div style="max-height: min(60vh, 500px); overflow-y: auto;">
          {items}
        </div>
      </div>
    </section>'''

    def _vertical_timeline_slide(self, instances: list) -> str:
        nodes = ""
        for inst in instances[:8]:
            if not isinstance(inst, dict):
                continue
            era = self._safe_str(inst.get("era_or_domain", ""))
            name = self._safe_str(inst.get("name", ""))
            brief = self._safe_str(inst.get("brief", ""))
            if not name:
                continue
            nodes += f'''
        <div class="reveal timeline-node" style="display: flex; gap: clamp(0.5rem, 1.5vw, 1rem); align-items: flex-start; margin-bottom: var(--element-gap);">
          <div style="min-width: clamp(60px, 10vw, 100px); font-size: var(--small-size); font-weight: 700; opacity: 0.6; text-align: right;">{self._esc(era)}</div>
          <div style="width: 3px; min-height: 40px; align-self: stretch; background: var(--accent);"></div>
          <div>
            <p style="font-size: var(--body-size); font-weight: 600;">{self._esc(name)}</p>
            <p style="font-size: var(--small-size); opacity: 0.7;">{self._esc(brief[:120])}</p>
          </div>
        </div>'''
        if not nodes:
            return ""
        return f'''
    <section class="slide">
      <div class="slide-content">
        <p class="reveal" style="font-size: var(--small-size); letter-spacing: 0.15em; text-transform: uppercase; opacity: 0.5;">Vertical — Across Time</p>
        <h2 class="reveal" style="font-size: var(--h2-size); margin-bottom: var(--content-gap);">Historical Instances</h2>
        <div style="max-height: min(60vh, 500px); overflow-y: auto;">
          {nodes}
        </div>
      </div>
    </section>'''

    def _vertical_comparison_slide(self, comparisons: list) -> str:
        cards = ""
        for comp in comparisons[:4]:
            if not isinstance(comp, dict):
                continue
            name = self._safe_str(comp.get("instance_name", ""))
            if not name:
                continue
            commons = self._safe_list(comp.get("commonalities", []))
            dists = self._safe_list(comp.get("distinctions", []))
            comm_items = "".join(f'<li>{self._esc(c)}</li>' for c in commons[:3])
            dist_items = "".join(f'<li>{self._esc(d)}</li>' for d in dists[:2])
            if not comm_items and not dist_items:
                continue
            cards += f'''
        <div class="reveal" style="background: var(--bg-secondary); padding: clamp(0.5rem, 1.5vw, 1rem); margin-bottom: var(--element-gap); border-radius: 6px;">
          <p style="font-size: var(--h3-size); font-weight: 700; margin-bottom: var(--element-gap);">{self._esc(name)}</p>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--element-gap);">
            <div><p style="font-size: var(--small-size); font-weight: 600; opacity: 0.6;">Commonalities</p><ul class="bullet-list" style="padding-left: 1em;">{comm_items or "<li>—</li>"}</ul></div>
            <div><p style="font-size: var(--small-size); font-weight: 600; opacity: 0.6;">Distinctions</p><ul class="bullet-list" style="padding-left: 1em;">{dist_items or "<li>—</li>"}</ul></div>
          </div>
        </div>'''
        if not cards:
            return ""
        return f'''
    <section class="slide">
      <div class="slide-content">
        <p class="reveal" style="font-size: var(--small-size); letter-spacing: 0.15em; text-transform: uppercase; opacity: 0.5;">Vertical Comparison</p>
        <h2 class="reveal" style="font-size: var(--h2-size); margin-bottom: var(--content-gap);">vs. Historical Precedents</h2>
        <div style="max-height: min(60vh, 500px); overflow-y: auto;">{cards}</div>
      </div>
    </section>'''

    def _horizontal_map_slide(self, instances: list) -> str:
        cards = ""
        for inst in instances[:8]:
            if not isinstance(inst, dict):
                continue
            domain = self._safe_str(inst.get("era_or_domain", ""))
            name = self._safe_str(inst.get("name", ""))
            brief = self._safe_str(inst.get("brief", ""))
            if not name:
                continue
            cards += f'''
        <div class="reveal" style="background: var(--bg-secondary); padding: clamp(0.5rem, 1.5vw, 1rem); border-radius: 6px; border-top: 3px solid var(--accent);">
          <p style="font-size: var(--small-size); opacity: 0.6;">{self._esc(domain)}</p>
          <p style="font-size: var(--body-size); font-weight: 600;">{self._esc(name)}</p>
          <p style="font-size: var(--small-size); opacity: 0.7; margin-top: 0.25em;">{self._esc(brief[:100])}</p>
        </div>'''
        if not cards:
            return ""
        return f'''
    <section class="slide">
      <div class="slide-content">
        <p class="reveal" style="font-size: var(--small-size); letter-spacing: 0.15em; text-transform: uppercase; opacity: 0.5;">Horizontal — Across Domains</p>
        <h2 class="reveal" style="font-size: var(--h2-size); margin-bottom: var(--content-gap);">Cross-Domain Instances</h2>
        <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr));">
          {cards}
        </div>
      </div>
    </section>'''

    def _horizontal_comparison_slide(self, comparisons: list) -> str:
        cards = ""
        for comp in comparisons[:4]:
            if not isinstance(comp, dict):
                continue
            name = self._safe_str(comp.get("instance_name", ""))
            if not name:
                continue
            commons = self._safe_list(comp.get("commonalities", []))
            dists = self._safe_list(comp.get("distinctions", []))
            comm_items = "".join(f'<li>{self._esc(c)}</li>' for c in commons[:3])
            dist_items = "".join(f'<li>{self._esc(d)}</li>' for d in dists[:2])
            if not comm_items and not dist_items:
                continue
            cards += f'''
        <div class="reveal" style="background: var(--bg-secondary); padding: clamp(0.5rem, 1.5vw, 1rem); margin-bottom: var(--element-gap); border-radius: 6px;">
          <p style="font-size: var(--h3-size); font-weight: 700; margin-bottom: var(--element-gap);">{self._esc(name)}</p>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--element-gap);">
            <div><p style="font-size: var(--small-size); font-weight: 600; opacity: 0.6;">Commonalities</p><ul class="bullet-list" style="padding-left: 1em;">{comm_items or "<li>—</li>"}</ul></div>
            <div><p style="font-size: var(--small-size); font-weight: 600; opacity: 0.6;">Distinctions</p><ul class="bullet-list" style="padding-left: 1em;">{dist_items or "<li>—</li>"}</ul></div>
          </div>
        </div>'''
        if not cards:
            return ""
        return f'''
    <section class="slide">
      <div class="slide-content">
        <p class="reveal" style="font-size: var(--small-size); letter-spacing: 0.15em; text-transform: uppercase; opacity: 0.5;">Horizontal Comparison</p>
        <h2 class="reveal" style="font-size: var(--h2-size); margin-bottom: var(--content-gap);">vs. Cross-Domain Peers</h2>
        <div style="max-height: min(60vh, 500px); overflow-y: auto;">{cards}</div>
      </div>
    </section>'''

    def _causal_validation_slide(self, validated: list, rejected: list) -> str:
        val_items = ""
        for v in validated[:5]:
            if not isinstance(v, dict):
                continue
            comm = self._safe_str(v.get("commonality", ""))
            chain = self._safe_str(v.get("causal_chain", ""))
            conf = v.get("confidence", 0)
            if not comm:
                continue
            val_items += f'''
        <div class="reveal" style="display: flex; gap: var(--element-gap); align-items: flex-start; margin-bottom: var(--element-gap);">
          <span style="font-size: var(--h3-size); color: #22c55e;">&#10003;</span>
          <div>
            <p style="font-size: var(--body-size); font-weight: 600;">{self._esc(comm)}</p>
            <p style="font-size: var(--small-size); opacity: 0.7;">{self._esc(chain[:120])}</p>
            <p style="font-size: var(--small-size); opacity: 0.5;">Confidence: {conf:.0%}</p>
          </div>
        </div>'''
        rej_items = ""
        for r in rejected[:3]:
            if not isinstance(r, dict):
                continue
            comm = self._safe_str(r.get("commonality", ""))
            reason = self._safe_str(r.get("rejection_reason", ""))
            if not comm:
                continue
            rej_items += f'''
        <div class="reveal" style="display: flex; gap: var(--element-gap); align-items: flex-start; margin-bottom: var(--element-gap); opacity: 0.6;">
          <span style="font-size: var(--h3-size); color: #ef4444;">&#10007;</span>
          <div>
            <p style="font-size: var(--body-size);">{self._esc(comm)}</p>
            <p style="font-size: var(--small-size); opacity: 0.7;">{self._esc(reason[:100])}</p>
          </div>
        </div>'''
        if not val_items and not rej_items:
            return ""
        return f'''
    <section class="slide">
      <div class="slide-content">
        <p class="reveal" style="font-size: var(--small-size); letter-spacing: 0.15em; text-transform: uppercase; opacity: 0.5;">Causal Validation</p>
        <h2 class="reveal" style="font-size: var(--h2-size); margin-bottom: var(--content-gap);">Validated vs. Rejected</h2>
        <div style="max-height: min(60vh, 500px); overflow-y: auto;">
          {val_items}
          {rej_items}
        </div>
      </div>
    </section>'''

    def _thesis_slide(self, thesis: str) -> str:
        thesis_str = self._safe_str(thesis)
        if not thesis_str:
            return ""
        return f'''
    <section class="slide">
      <div class="slide-content" style="justify-content: center; align-items: center; text-align: center; max-width: min(80vw, 700px); margin: auto;">
        <p class="reveal" style="font-size: var(--small-size); letter-spacing: 0.15em; text-transform: uppercase; opacity: 0.5;">Core Thesis</p>
        <h2 class="reveal" style="font-size: var(--h2-size); margin-top: var(--content-gap); line-height: 1.3;">{self._esc(thesis_str)}</h2>
        <div class="reveal" style="width: 60px; height: 3px; background: var(--accent); margin-top: var(--content-gap);"></div>
      </div>
    </section>'''

    def _insight_slide(self, insight: dict, index: int) -> str:
        if not isinstance(insight, dict):
            return ""
        title = self._safe_str(insight.get("title", f"Insight {index}"))
        desc = self._safe_str(insight.get("description", ""))
        v_ev = self._safe_str(insight.get("vertical_evidence", ""))
        h_ev = self._safe_str(insight.get("horizontal_evidence", ""))
        if not title and not desc and not v_ev and not h_ev:
            return ""
        return f'''
    <section class="slide">
      <div class="slide-content">
        <p class="reveal" style="font-size: var(--small-size); letter-spacing: 0.15em; text-transform: uppercase; opacity: 0.5;">Insight {index}</p>
        <h2 class="reveal" style="font-size: var(--h2-size); margin-bottom: var(--content-gap);">{self._esc(title)}</h2>
        <p class="reveal" style="font-size: var(--body-size); margin-bottom: var(--content-gap);">{self._esc(desc)}</p>
        <div class="reveal" style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--content-gap);">
          <div style="background: var(--accent-light); padding: clamp(0.5rem, 1.5vw, 1rem); border-radius: 6px;">
            <p style="font-size: var(--small-size); font-weight: 600; opacity: 0.6;">Vertical Evidence</p>
            <p style="font-size: var(--small-size);">{self._esc(v_ev[:200])}</p>
          </div>
          <div style="background: var(--accent-light); padding: clamp(0.5rem, 1.5vw, 1rem); border-radius: 6px;">
            <p style="font-size: var(--small-size); font-weight: 600; opacity: 0.6;">Horizontal Evidence</p>
            <p style="font-size: var(--small-size);">{self._esc(h_ev[:200])}</p>
          </div>
        </div>
      </div>
    </section>'''

    def _prediction_slide(self, prediction: str, recommendations: list) -> str:
        pred_str = self._safe_str(prediction)
        rec_items = ""
        for r in recommendations[:5]:
            r_str = self._safe_str(r)
            if r_str:
                rec_items += f'<li class="reveal" style="font-size: var(--body-size);">{self._esc(r_str)}</li>'
        return f'''
    <section class="slide">
      <div class="slide-content">
        <p class="reveal" style="font-size: var(--small-size); letter-spacing: 0.15em; text-transform: uppercase; opacity: 0.5;">Prediction</p>
        <h2 class="reveal" style="font-size: var(--h2-size); margin-bottom: var(--content-gap);">Forward Look</h2>
        <p class="reveal" style="font-size: var(--body-size); margin-bottom: var(--content-gap);">{self._esc(pred_str)}</p>
        {f'<p class="reveal" style="font-size: var(--small-size); font-weight: 600; opacity: 0.6; margin-bottom: var(--element-gap);">Recommendations</p><ul class="feature-list" style="padding-left: 1em;">{rec_items}</ul>' if rec_items else ""}
      </div>
    </section>'''

    def _closing_slide(self, topic: str) -> str:
        return f'''
    <section class="slide">
      <div class="slide-content" style="justify-content: center; align-items: center; text-align: center;">
        <p class="reveal" style="font-size: var(--small-size); letter-spacing: 0.15em; text-transform: uppercase; opacity: 0.5;">Unveiling</p>
        <h1 class="reveal" style="font-size: var(--title-size); margin-top: var(--element-gap);">{self._esc(topic)}</h1>
        <p class="reveal" style="font-size: var(--body-size); margin-top: var(--content-gap); opacity: 0.6;">Understanding through analogy across space and time</p>
        <div class="reveal" style="width: 60px; height: 3px; background: var(--accent); margin-top: var(--content-gap);"></div>
      </div>
    </section>'''

    # ── HTML assembly ──

    def _assemble_html(self, title: str, style: dict, viewport_css: str, slides_html: str) -> str:
        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{self._esc(title)} — Unveiling</title>
  <link rel="stylesheet" href="{style['font_url']}">
  <style>
    :root {{
      --bg-primary: {style['bg_primary']};
      --bg-secondary: {style['bg_secondary']};
      --text-primary: {style['text_primary']};
      --text-secondary: {style['text_secondary']};
      --accent: {style['accent']};
      --accent-light: {style['accent_light']};
      --font-display: {style['font_display']};
      --font-body: {style['font_body']};
      --title-size: clamp(1.5rem, 5vw, 4rem);
      --h2-size: clamp(1.25rem, 3.5vw, 2.5rem);
      --h3-size: clamp(1rem, 2.5vw, 1.75rem);
      --body-size: clamp(0.75rem, 1.5vw, 1.125rem);
      --small-size: clamp(0.65rem, 1vw, 0.875rem);
      --slide-padding: clamp(1rem, 4vw, 4rem);
      --content-gap: clamp(0.5rem, 2vw, 2rem);
      --element-gap: clamp(0.25rem, 1vw, 1rem);
      --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
      --duration-normal: 0.6s;
    }}
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: var(--font-body);
      background: var(--bg-primary);
      color: var(--text-primary);
    }}
    {viewport_css}
    h1, h2, h3 {{ font-family: var(--font-display); }}

    /* Progress bar */
    .progress-bar {{
      position: fixed; top: 0; left: 0; height: 3px; z-index: 100;
      background: var(--accent); transition: width 0.3s;
    }}

    /* Nav dots */
    .nav-dots {{
      position: fixed; right: 16px; top: 50%; transform: translateY(-50%);
      display: flex; flex-direction: column; gap: 8px; z-index: 100;
    }}
    .nav-dot {{
      width: 8px; height: 8px; border-radius: 50%;
      background: var(--text-secondary); opacity: 0.3;
      cursor: pointer; transition: all 0.3s;
    }}
    .nav-dot.active {{ opacity: 1; background: var(--accent); transform: scale(1.3); }}

    /* Reveal animations */
    .reveal {{
      opacity: 0; transform: translateY(30px);
      transition: opacity var(--duration-normal) var(--ease-out-expo),
                  transform var(--duration-normal) var(--ease-out-expo);
    }}
    .slide.visible .reveal {{ opacity: 1; transform: translateY(0); }}
    .reveal:nth-child(1) {{ transition-delay: 0.1s; }}
    .reveal:nth-child(2) {{ transition-delay: 0.2s; }}
    .reveal:nth-child(3) {{ transition-delay: 0.3s; }}
    .reveal:nth-child(4) {{ transition-delay: 0.4s; }}
    .reveal:nth-child(5) {{ transition-delay: 0.5s; }}
    .reveal:nth-child(6) {{ transition-delay: 0.6s; }}

    ul {{ list-style: disc; }}
    li {{ line-height: 1.5; }}

    @media (max-width: 600px) {{
      .nav-dots {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="progress-bar" id="progressBar"></div>
  <nav class="nav-dots" id="navDots"></nav>

{slides_html}

  <script>
    class SlidePresentation {{
      constructor() {{
        this.slides = document.querySelectorAll('.slide');
        this.currentSlide = 0;
        this.setupIntersectionObserver();
        this.setupKeyboardNav();
        this.setupTouchNav();
        this.setupProgressBar();
        this.setupNavDots();
      }}

      setupIntersectionObserver() {{
        const observer = new IntersectionObserver((entries) => {{
          entries.forEach(entry => {{
            if (entry.isIntersecting) {{
              entry.target.classList.add('visible');
              const idx = Array.from(this.slides).indexOf(entry.target);
              this.currentSlide = idx;
              this.updateProgressBar();
              this.updateNavDots();
            }}
          }});
        }}, {{ threshold: 0.5 }});
        this.slides.forEach(s => observer.observe(s));
      }}

      setupKeyboardNav() {{
        document.addEventListener('keydown', (e) => {{
          if (e.key === 'ArrowDown' || e.key === ' ' || e.key === 'PageDown') {{
            e.preventDefault(); this.goTo(this.currentSlide + 1);
          }} else if (e.key === 'ArrowUp' || e.key === 'PageUp') {{
            e.preventDefault(); this.goTo(this.currentSlide - 1);
          }} else if (e.key === 'Home') {{
            e.preventDefault(); this.goTo(0);
          }} else if (e.key === 'End') {{
            e.preventDefault(); this.goTo(this.slides.length - 1);
          }}
        }});
      }}

      setupTouchNav() {{
        let startY = 0;
        document.addEventListener('touchstart', (e) => {{ startY = e.touches[0].clientY; }});
        document.addEventListener('touchend', (e) => {{
          const diff = startY - e.changedTouches[0].clientY;
          if (Math.abs(diff) > 50) {{
            if (diff > 0) this.goTo(this.currentSlide + 1);
            else this.goTo(this.currentSlide - 1);
          }}
        }});
      }}

      setupProgressBar() {{
        this.progressBar = document.getElementById('progressBar');
      }}

      updateProgressBar() {{
        const pct = ((this.currentSlide + 1) / this.slides.length) * 100;
        this.progressBar.style.width = pct + '%';
      }}

      setupNavDots() {{
        const container = document.getElementById('navDots');
        container.innerHTML = '';
        this.slides.forEach((_, i) => {{
          const dot = document.createElement('div');
          dot.className = 'nav-dot' + (i === 0 ? ' active' : '');
          dot.addEventListener('click', () => this.goTo(i));
          container.appendChild(dot);
        }});
      }}

      updateNavDots() {{
        document.querySelectorAll('.nav-dot').forEach((d, i) => {{
          d.classList.toggle('active', i === this.currentSlide);
        }});
      }}

      goTo(idx) {{
        idx = Math.max(0, Math.min(idx, this.slides.length - 1));
        this.slides[idx].scrollIntoView({{ behavior: 'smooth' }});
      }}
    }}

    new SlidePresentation();
  </script>
</body>
</html>'''

    @staticmethod
    def _esc(text: str) -> str:
        if not text:
            return ""
        return (text.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace('"', "&quot;"))
