"""
HTML reporting — Blueprint §J, Phase 3.

Definition of done (Blueprint §K): a non-technical reviewer can read this
report and understand the V1->V2 story without opening Python.

Deterministic and template-generated: every string is derived from the
PipelineResult's already-computed numbers. Nothing here is LLM-authored
(hard constraint 2) and nothing is recomputed (Blueprint §J).

Charts are embedded as base64 PNGs so the report is a single portable
file with no external asset dependencies -- it survives being emailed,
attached to a workpaper, or opened offline.

Design: the visual language is the audit workpaper -- cross-reference
letters, tickmarks, exception flags -- because that is the actual
vernacular of the reader this is written for.
"""
from __future__ import annotations

import base64
from pathlib import Path

from .report import PipelineResult, decision_priority_table, executive_summary

_CSS = """
:root {
  --paper:      #F5F6F3;
  --card:       #FFFFFF;
  --ink:        #141A1F;
  --ink-soft:   #4A5560;
  --ink-faint:  #7C8891;
  --rule:       #DCE0DA;
  --positive:   #1D6B45;
  --negative:   #9B2C2C;
  --flag:       #B45309;
  --verified:   #2C5F7C;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: "Source Serif 4", Georgia, serif;
  font-size: 16px;
  line-height: 1.65;
}
.label, .rail-ref, th, .stamp, h1, h2, .eyebrow {
  font-family: Archivo, "Helvetica Neue", Arial, sans-serif;
}
.num, .figure, td.n, .thesis-val {
  font-family: "IBM Plex Mono", "SF Mono", Menlo, monospace;
  font-variant-numeric: tabular-nums;
}
.wrap { max-width: 1080px; margin: 0 auto; padding: 0 24px 96px; }

/* ---------- masthead ---------- */
.masthead { padding: 56px 0 32px; border-bottom: 2px solid var(--ink); }
.eyebrow {
  font-size: 11px; letter-spacing: .18em; text-transform: uppercase;
  color: var(--ink-faint); font-weight: 600; margin: 0 0 14px;
}
h1 { font-size: clamp(30px, 5vw, 46px); line-height: 1.08; margin: 0 0 18px; font-weight: 700; letter-spacing: -.02em; }
.sub { color: var(--ink-soft); max-width: 62ch; margin: 0; font-size: 17px; }
.meta-strip {
  display: flex; flex-wrap: wrap; gap: 28px; margin-top: 28px;
  font-size: 12px; color: var(--ink-faint);
}
.meta-strip .num { color: var(--ink); }

/* ---------- the thesis (signature element) ---------- */
.thesis { margin: 48px 0 8px; padding: 32px; background: var(--card); border: 1px solid var(--rule); }
.thesis h2 { font-size: 13px; letter-spacing: .14em; text-transform: uppercase; margin: 0 0 6px; color: var(--flag); }
.thesis .q { font-size: 21px; line-height: 1.45; margin: 0 0 28px; max-width: 60ch; }
.answers { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 1px; background: var(--rule); }
.answer { background: var(--card); padding: 20px; }
.answer.chosen { background: #F0F5F1; box-shadow: inset 3px 0 0 var(--positive); }
.answer .how { font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: var(--ink-faint); margin-bottom: 10px; font-family: Archivo, sans-serif; }
.thesis-val { font-size: 30px; font-weight: 500; letter-spacing: -.02em; }
.answer .note { font-size: 13px; color: var(--ink-soft); margin-top: 8px; line-height: 1.4; }
.answer.chosen .note { color: var(--positive); font-weight: 600; }
.thesis .verdict { margin: 26px 0 0; padding-top: 20px; border-top: 1px solid var(--rule); font-size: 15px; color: var(--ink-soft); max-width: 68ch; }

/* ---------- workpaper sections ---------- */
section { display: grid; grid-template-columns: 62px 1fr; gap: 0; margin-top: 44px; }
.rail { border-right: 1px solid var(--rule); padding-top: 4px; }
.rail-ref { font-size: 13px; font-weight: 700; letter-spacing: .06em; color: var(--ink-faint); }
.tick { display: block; margin-top: 8px; font-size: 15px; line-height: 1; }
.tick.ok { color: var(--verified); }
.tick.flag { color: var(--flag); }
.body { padding-left: 26px; min-width: 0; }
h2.sec { font-size: 12px; letter-spacing: .16em; text-transform: uppercase; margin: 0 0 4px; font-weight: 700; }
.sec-lede { color: var(--ink-soft); margin: 0 0 20px; max-width: 66ch; font-size: 15px; }

/* ---------- tables ---------- */
table { width: 100%; border-collapse: collapse; margin: 0 0 8px; font-size: 14px; }
th {
  text-align: left; font-size: 10.5px; letter-spacing: .11em; text-transform: uppercase;
  color: var(--ink-faint); font-weight: 600; padding: 0 12px 8px 0; border-bottom: 1px solid var(--ink);
}
th.r, td.n { text-align: right; }
td { padding: 9px 12px 9px 0; border-bottom: 1px solid var(--rule); }
tbody tr:last-child td { border-bottom: none; }
.pos { color: var(--positive); }
.neg { color: var(--negative); }
.rank { color: var(--ink-faint); width: 1%; padding-right: 16px; }

/* ---------- callouts ---------- */
.callout { border-left: 3px solid var(--flag); padding: 14px 0 14px 18px; margin: 20px 0; background: #FDF9F2; }
.callout .label { font-size: 10.5px; letter-spacing: .12em; text-transform: uppercase; color: var(--flag); font-weight: 700; }
.callout p { margin: 6px 0 0; font-size: 14.5px; color: var(--ink-soft); }
.callout .num { color: var(--ink); font-weight: 600; }

figure { margin: 24px 0 0; }
figure img { width: 100%; height: auto; display: block; border: 1px solid var(--rule); background: #fff; }
figcaption { font-size: 12.5px; color: var(--ink-faint); margin-top: 8px; font-family: Archivo, sans-serif; }

.checks { list-style: none; padding: 0; margin: 0; font-size: 14px; }
.checks li { padding: 7px 0; border-bottom: 1px solid var(--rule); display: flex; gap: 12px; align-items: baseline; }
.checks li:last-child { border-bottom: none; }
.checks .mark { flex: 0 0 auto; font-size: 13px; }
.checks .mark.ok { color: var(--verified); }
.checks .mark.bad { color: var(--negative); }
.checks .what { flex: 1; }
.checks .detail { color: var(--ink-faint); font-size: 13px; }

.limits { font-size: 14.5px; color: var(--ink-soft); }
.limits li { margin-bottom: 9px; }

footer { margin-top: 64px; padding-top: 22px; border-top: 2px solid var(--ink); font-size: 12.5px; color: var(--ink-faint); }
footer .num { color: var(--ink-soft); }
footer dl { display: grid; grid-template-columns: max-content 1fr; gap: 5px 20px; margin: 12px 0 0; }
footer dt { font-family: Archivo, sans-serif; font-size: 10.5px; letter-spacing: .1em; text-transform: uppercase; }

@media (max-width: 680px) {
  section { grid-template-columns: 1fr; }
  .rail { border-right: none; border-bottom: 1px solid var(--rule); padding-bottom: 8px; margin-bottom: 16px; display: flex; gap: 12px; align-items: center; }
  .rail .tick { margin-top: 0; }
  .body { padding-left: 0; }
  .thesis { padding: 22px; }
  table { font-size: 13px; }
}
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
@media print {
  body { background: #fff; }
  section { break-inside: avoid; }
  .thesis { break-inside: avoid; }
}
"""


def _b64_img(path: Path) -> str | None:
    if not path.exists():
        return None
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _sign_class(v: float) -> str:
    return "pos" if v >= 0 else "neg"


def _fmt(v: float, dp: int = 2, signed: bool = True) -> str:
    fmt = f"{{:+,.{dp}f}}" if signed else f"{{:,.{dp}f}}"
    return fmt.format(v)


def _money(v: float, dp: int = 2, per_share: bool = False) -> str:
    """Signed currency with the sign OUTSIDE the symbol: -$4.10M, not $-4.10M."""
    sign = "-" if v < 0 else "+"
    suffix = "/share" if per_share else "M"
    return f"{sign}${abs(v):,.{dp}f}{suffix}"


def _figure(outputs: Path, filename: str, caption: str) -> str:
    b64 = _b64_img(outputs / filename)
    if b64 is None:
        return ""
    return (
        f'<figure><img src="data:image/png;base64,{b64}" alt="{caption}">'
        f"<figcaption>{caption}</figcaption></figure>"
    )


def build_html_report(result: PipelineResult, outputs: Path) -> str:
    """Render the full report as a single self-contained HTML document."""
    from .model_spec import FCF_MODEL

    r = result
    spec = r.spec or FCF_MODEL
    per_share = spec.money_format == "share"
    out_label = spec.output_label
    unit_sfx = "/share" if per_share else "M"

    def _m(v: float, dp: int = 2) -> str:
        """Signed CHANGE: always shows + or -."""
        return _money(v, dp, per_share=per_share)

    def _lvl(v: float, dp: int = 2) -> str:
        """A LEVEL: negative sign outside the currency symbol (-$152.88M,
        never $-152.88M), positive unadorned."""
        sign = "-" if v < 0 else ""
        return f"{sign}${abs(v):,.{dp}f}" + ("/share" if per_share else "M")

    ref = iter("ABCDEFGH")

    # ---- the thesis: same driver, different answers -------------------
    thesis_html = ""
    if len(r.changed) > 0:
        shap_idx = r.shapley.set_index("driver")
        spreads = (r.comparison["sequential_max"] - r.comparison["sequential_min"]).sort_values(ascending=False)
        focus = spreads.index[0]
        seq_min = r.comparison.loc[focus, "sequential_min"]
        seq_max = r.comparison.loc[focus, "sequential_max"]
        shap_val = shap_idx.loc[focus, "shapley_contribution"]
        spread = seq_max - seq_min
        spread_pct = 100 * spread / abs(shap_val) if shap_val else 0

        thesis_html = f"""
<div class="thesis">
  <h2>The problem this report solves</h2>
  <p class="q">Walk the drivers in a different order and <strong>{focus}</strong> gets credited
     with a different number &mdash; without a single assumption changing.</p>
  <div class="answers">
    <div class="answer">
      <div class="how">Walked one way</div>
      <div class="thesis-val">{_fmt(seq_min)}</div>
      <div class="note">Sequential bridge, least favourable ordering</div>
    </div>
    <div class="answer">
      <div class="how">Walked another way</div>
      <div class="thesis-val">{_fmt(seq_max)}</div>
      <div class="note">Sequential bridge, most favourable ordering</div>
    </div>
    <div class="answer chosen">
      <div class="how">Order-independent</div>
      <div class="thesis-val">{_fmt(shap_val)}</div>
      <div class="note">&#10003; Shapley &mdash; the figure of record</div>
    </div>
  </div>
  <p class="verdict">That is a <span class="num">${spread:,.2f}{unit_sfx}</span> spread
     (<span class="num">{spread_pct:.0f}%</span> of the driver&rsquo;s own value) created purely by
     a presentation choice. The Shapley figure removes it: it is the same regardless of ordering, and
     the three driver figures still sum exactly to the total variance.</p>
</div>"""

    # ---- A. Structural integrity -------------------------------------
    def checks_list(rep) -> str:
        items = []
        for c in rep.results:
            mark = "&#10003;" if c.passed else "&#10007;";
            cls = "ok" if c.passed else "bad"
            items.append(
                f'<li><span class="mark {cls}">{mark}</span>'
                f'<span class="what">{c.name.replace("_", " ")}</span>'
                f'<span class="detail">{c.message}</span></li>'
            )
        return "".join(items)

    sia_pass = r.sia_v1.passed and r.sia_v2.passed
    sia_section = f"""
<section>
  <div class="rail"><div class="rail-ref">{next(ref)}</div>
    <span class="tick {'ok' if sia_pass else 'flag'}">{'&#10003;' if sia_pass else '&#9888;'}</span></div>
  <div class="body">
    <h2 class="sec">Structural integrity</h2>
    <p class="sec-lede">Mechanical conformance checks against the controlled model schema. These run
       <em>before</em> any attribution &mdash; a failure here stops the pipeline, because attributing
       variance in a structurally unsound model produces confident nonsense.</p>
    <ul class="checks">{checks_list(r.sia_v1)}</ul>
  </div>
</section>"""

    # ---- B. What changed ---------------------------------------------
    change_rows = "".join(
        f"<tr><td>{d}</td>"
        f'<td class="n num">{getattr(r.v1, d):,.4g}</td>'
        f'<td class="n num">{getattr(r.v2, d):,.4g}</td>'
        f'<td class="n num {_sign_class(getattr(r.v2, d) - getattr(r.v1, d))}">'
        f"{_fmt(getattr(r.v2, d) - getattr(r.v1, d), 4)}</td></tr>"
        for d in r.changed
    )
    changed_section = f"""
<section>
  <div class="rail"><div class="rail-ref">{next(ref)}</div></div>
  <div class="body">
    <h2 class="sec">What changed</h2>
    <p class="sec-lede">{len(r.changed)} of {len(spec.roles)} drivers moved between versions. {out_label} went from
       <span class="num">{_lvl(r.v1_fcf)}</span> to <span class="num">{_lvl(r.v2_fcf)}</span>,
       a change of <span class="num {_sign_class(r.total_variance)}">{_m(r.total_variance)}</span>.</p>
    <table><thead><tr><th>Driver</th><th class="r">V1</th><th class="r">V2</th><th class="r">Change</th></tr></thead>
    <tbody>{change_rows}</tbody></table>
  </div>
</section>"""

    # ---- C. Attribution ----------------------------------------------
    attr_rows = "".join(
        f'<tr><td>{row.driver}</td>'
        f'<td class="n num {_sign_class(row.shapley_contribution)}">{_fmt(row.shapley_contribution)}</td>'
        f'<td class="n num">{row.pct_of_variance:,.0f}%</td>'
        f'<td class="n num">{r.comparison.loc[row.driver, "sequential_min"]:,.2f} &ndash; '
        f'{r.comparison.loc[row.driver, "sequential_max"]:,.2f}</td></tr>'
        for row in r.shapley.itertuples()
    )
    attribution_section = f"""
<section>
  <div class="rail"><div class="rail-ref">{next(ref)}</div>
    <span class="tick ok">&#10003;</span></div>
  <div class="body">
    <h2 class="sec">Attribution</h2>
    <p class="sec-lede">Each driver&rsquo;s share of the total change, computed as a Shapley value &mdash;
       the average of its contribution across every possible ordering. Percentages can exceed 100% or
       go negative when drivers push against each other; that is the honest picture, not an error.</p>
    <table><thead><tr><th>Driver</th><th class="r">Shapley ({unit_sfx.lstrip("/") if per_share else "$M"})</th><th class="r">Share</th>
      <th class="r">Sequential range</th></tr></thead>
    <tbody>{attr_rows}</tbody></table>
    {_figure(outputs, "shapley_attribution.png", "Shapley contribution per driver; black whisker shows the full sequential range the ordering choice could have produced.")}
  </div>
</section>"""

    # ---- D. Interaction ----------------------------------------------
    inter = r.interactions
    pair_rows = "".join(
        f'<tr><td>{row.driver_a} &times; {row.driver_b}</td>'
        f'<td class="n num {_sign_class(row.interaction)}">{_fmt(row.interaction, 4)}</td></tr>'
        for row in inter["pairwise"].itertuples()
    )
    l1_pct = inter["l1_pct_of_variance"]
    interaction_section = f"""
<section>
  <div class="rail"><div class="rail-ref">{next(ref)}</div>
    <span class="tick {'flag' if l1_pct > 10 else 'ok'}">{'&#9888;' if l1_pct > 10 else '&#10003;'}</span></div>
  <div class="body">
    <h2 class="sec">Interaction &amp; non-additivity</h2>
    <p class="sec-lede">How much of the change comes from drivers acting <em>together</em> rather than
       independently. This is what makes ordering matter in the first place.</p>
    <div class="callout">
      <div class="label">Read the L1 figure, not the net figure</div>
      <p>Net non-additivity is <span class="num">{_m(inter['net_non_additivity'])}</span> &mdash; but
         that number partly cancels itself out and understates the risk. The L1 figure sums the
         interaction terms without letting them cancel:
         <span class="num">${inter['l1_non_additivity']:,.2f}{unit_sfx}</span>, or
         <span class="num">{l1_pct:.1f}%</span> of the total change. If L1 were zero, ordering could not
         matter at all.</p>
    </div>
    <table><thead><tr><th>Driver pair</th><th class="r">Interaction ($M)</th></tr></thead>
    <tbody>{pair_rows}</tbody></table>
  </div>
</section>"""

    # ---- E. Priority --------------------------------------------------
    prio = decision_priority_table(r)
    prio_rows = "".join(
        f'<tr><td class="rank num">{i}</td><td>{row.driver}</td>'
        f'<td class="n num {_sign_class(row.shapley_contribution)}">{_fmt(row.shapley_contribution)}</td>'
        f'<td class="n num">{row.priority_score:.3f}</td></tr>'
        for i, row in enumerate(prio.itertuples(), start=1)
    )
    basis = prio.iloc[0]["method"] if len(prio) else "n/a"
    priority_section = f"""
<section>
  <div class="rail"><div class="rail-ref">{next(ref)}</div></div>
  <div class="body">
    <h2 class="sec">Where to look first</h2>
    <p class="sec-lede">Drivers ranked by how much they warrant attention. Basis: {basis}.</p>
    <table><thead><tr><th></th><th>Driver</th><th class="r">Shapley ({unit_sfx.lstrip("/") if per_share else "$M"})</th><th class="r">Priority</th></tr></thead>
    <tbody>{prio_rows}</tbody></table>
  </div>
</section>"""

    # ---- F. Sensitivity (Phase 2, optional) ---------------------------
    sensitivity_section = ""
    if r.dia_sobol is not None:
        unchanged_top = r.dia_sobol[~r.dia_sobol["driver"].isin(r.changed)]
        surprise = ""
        if len(unchanged_top) and unchanged_top.iloc[0]["ST"] > 0.05:
            d = unchanged_top.iloc[0]
            surprise = f"""
    <div class="callout">
      <div class="label">Did not change &mdash; but should be watched</div>
      <p><span class="num">{d['driver']}</span> contributed nothing to this variance because it did not
         move. Yet it accounts for <span class="num">{d['ST']:.0%}</span> of the model&rsquo;s output
         uncertainty. The attribution above is silent on it by construction; this section is not.</p>
    </div>"""
        sob_rows = "".join(
            f'<tr><td>{row.driver}</td><td class="n num">{row.S1:.4f}</td>'
            f'<td class="n num">{row.ST:.4f}</td>'
            f'<td class="n num">{row.interaction_gap:+.4f}</td></tr>'
            for row in r.dia_sobol.itertuples()
        )
        sensitivity_section = f"""
<section>
  <div class="rail"><div class="rail-ref">{next(ref)}</div></div>
  <div class="body">
    <h2 class="sec">Sensitivity &mdash; a different question</h2>
    <p class="sec-lede">Attribution explains what <em>did</em> happen. This explains what <em>could</em>
       happen: each driver&rsquo;s share of output uncertainty under a &plusmn;20% assumed range,
       whether or not it moved this time.</p>
    {surprise}
    <table><thead><tr><th>Driver</th><th class="r">First-order</th><th class="r">Total-order</th>
      <th class="r">Interaction gap</th></tr></thead>
    <tbody>{sob_rows}</tbody></table>
    {_figure(outputs, "dia_sobol.png", "Sobol sensitivity indices. The gap between total-order and first-order bars indicates variance carried by interactions.")}
  </div>
</section>"""

    # ---- G. Thresholds (Phase 2, optional) ----------------------------
    threshold_section = ""
    if r.tba_results is not None:
        t_rows = []
        for name, tr in r.tba_results.items():
            if tr.defined:
                base_val = getattr(r.v1, name)
                headroom = tr.threshold - base_val
                t_rows.append(
                    f'<tr><td>{name}</td><td class="n num">{base_val:,.4g}</td>'
                    f'<td class="n num">{tr.threshold:,.4f}</td>'
                    f'<td class="n num">{_fmt(headroom, 4)}</td></tr>'
                )
            else:
                t_rows.append(
                    f'<tr><td>{name}</td><td class="n num">{getattr(r.v1, name):,.4g}</td>'
                    f'<td class="n" colspan="2" style="color:var(--ink-faint);font-size:13px">'
                    f"no crossing in searched range</td></tr>"
                )
        threshold_section = f"""
<section>
  <div class="rail"><div class="rail-ref">{next(ref)}</div></div>
  <div class="body">
    <h2 class="sec">Break points</h2>
    <p class="sec-lede">The value at which each driver alone would push free cash flow through zero,
       holding everything else at V1. Headroom is the distance from today&rsquo;s value to that point.</p>
    <table><thead><tr><th>Driver</th><th class="r">V1 value</th><th class="r">Breaks at</th>
      <th class="r">Headroom</th></tr></thead>
    <tbody>{"".join(t_rows)}</tbody></table>
  </div>
</section>"""

    # ---- H. Limitations -----------------------------------------------
    limits_section = f"""
<section>
  <div class="rail"><div class="rail-ref">{next(ref)}</div>
    <span class="tick flag">&#9888;</span></div>
  <div class="body">
    <h2 class="sec">What this does not tell you</h2>
    <p class="sec-lede">Stated up front rather than buried, because a diagnostic tool that hides its
       own limits is worse than none.</p>
    <ul class="limits">
      <li>The structural checks confirm schema conformance only. They cannot catch a driver that is
          internally consistent but economically wrong.</li>
      <li>This free cash flow figure is unlevered and will not reconcile to a reported non-GAAP FCF:
          stock compensation, interest income and one-off items are excluded by design.</li>
      <li>Driver values are inputs supplied by the analyst. Nothing here is a forecast.</li>
      <li>Sensitivity results depend on an assumed &plusmn;20% input range that has not been calibrated
          against observed driver volatility.</li>
      <li>Break points move one driver at a time. Real stress arrives in combination.</li>
    </ul>
  </div>
</section>"""

    manifest_dl = "".join(f"<dt>{k.replace('_', ' ')}</dt><dd class='num'>{v}</dd>" for k, v in r.manifest.items())

    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Bridgework &mdash; Variance Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=IBM+Plex+Mono:wght@400;500&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap" rel="stylesheet">
<style>{_CSS}</style>
</head><body>
<div class="wrap">
  <header class="masthead">
    <p class="eyebrow">Bridgework &middot; Variance Attribution Workpaper</p>
    <h1>Why {out_label.lower()} moved<br>{_m(r.total_variance)} between versions</h1>
    <p class="sub">{executive_summary(r)}</p>
    <div class="meta-strip">
      <span>V1 <span class="num">{_lvl(r.v1_fcf)}</span></span>
      <span>V2 <span class="num">{_lvl(r.v2_fcf)}</span></span>
      <span>Drivers moved <span class="num">{len(r.changed)}</span></span>
      <span>Reference <span class="num">{r.manifest.get('input_hash', 'n/a')}</span></span>
    </div>
  </header>
  {thesis_html}
  {sia_section}
  {changed_section}
  {attribution_section}
  {interaction_section}
  {priority_section}
  {sensitivity_section}
  {threshold_section}
  {limits_section}
  <footer>
    <strong>Reproducibility.</strong> Every figure above is deterministic: the same inputs and code
    version reproduce this document exactly. No estimate, narrative or ranking on this page was
    generated by a language model.
    <dl>{manifest_dl}</dl>
  </footer>
</div>
</body></html>"""


__all__ = ["build_html_report"]
