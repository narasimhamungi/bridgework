"""
Reporting — Blueprint §J. Every artefact here is a pure function of
already-computed numeric results; nothing is recomputed, and nothing is
LLM-authored (hard constraint 2: no LLM in the calculation OR the
executive-summary path). The executive summary is a deterministic template
filled from the same numbers that appear in the tables.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from .model import Drivers


def money(v: float, dp: int = 2) -> str:
    """Signed currency with the sign OUTSIDE the symbol: -$4.10M, not $-4.10M."""
    sign = "-" if v < 0 else "+"
    return f"{sign}${abs(v):,.{dp}f}M"
from .sia import SIAReport


def change_register(v1, v2, changed: tuple, spec=None) -> pd.DataFrame:
    from .model_spec import FCF_MODEL
    spec = spec or FCF_MODEL
    v1d, v2d = asdict(v1), asdict(v2)
    rows = []
    for role in spec.roles:
        v1v, v2v = v1d[role], v2d[role]
        rows.append(
            {
                "driver": role,
                "label": spec.labels[role],
                "v1": v1v,
                "v2": v2v,
                "absolute_change": v2v - v1v,
                "pct_change": ((v2v - v1v) / v1v * 100.0) if v1v else float("nan"),
                "changed": role in changed,
            }
        )
    return pd.DataFrame(rows)


def model_snapshot(v1, v2, spec=None) -> pd.DataFrame:
    from .model_spec import FCF_MODEL
    spec = spec or FCF_MODEL
    li_v1, li_v2 = spec.line_items(v1), spec.line_items(v2)
    snap = pd.DataFrame({"V1": pd.Series(li_v1), "V2": pd.Series(li_v2)})
    snap["V2 - V1"] = snap["V2"] - snap["V1"]
    return snap


def sequential_vs_shapley(
    bridge_canonical: pd.DataFrame, ordering_matrix: pd.DataFrame, shapley_df: pd.DataFrame, changed: tuple
) -> pd.DataFrame:
    seq = bridge_canonical.set_index("driver")["incremental_impact"]
    cmp = pd.DataFrame(
        {
            "sequential_canonical": seq,
            "sequential_min": ordering_matrix[list(changed)].min(),
            "sequential_max": ordering_matrix[list(changed)].max(),
            "shapley": shapley_df.set_index("driver")["shapley_contribution"],
        }
    )
    cmp["seq_range"] = cmp["sequential_max"] - cmp["sequential_min"]
    cmp["seq_minus_shapley"] = cmp["sequential_canonical"] - cmp["shapley"]
    return cmp


@dataclass
class PipelineResult:
    v1: Drivers
    v2: Drivers
    changed: tuple
    v1_fcf: float
    v2_fcf: float
    total_variance: float
    sia_v1: SIAReport
    sia_v2: SIAReport
    bridge_canonical: pd.DataFrame
    ordering_matrix: pd.DataFrame
    shapley: pd.DataFrame
    comparison: pd.DataFrame
    interactions: dict[str, object]
    manifest: dict[str, str]
    spec: object = None            # ModelSpec; None => FCF (back-compat)
    dia_tornado: pd.DataFrame | None = None
    dia_sobol: pd.DataFrame | None = None
    tba_results: dict[str, object] | None = None  # driver -> ThresholdResult


def decision_priority_table(
    result: PipelineResult, w1: float = 0.5, w2: float = 0.3, w3: float = 0.2
) -> pd.DataFrame:
    """Blueprint §J decision-priority ranking.

    Phase 1 (no DIA/TBA present): pure Shapley-magnitude ranking.
    Phase 2 (DIA and/or TBA present): full 3-factor weighted formula,
    each term rescaled to [0,1] before combining so no metric's natural
    scale dominates by accident (Blueprint §J, Assumption #2). Any
    missing factor (DIA not run, or a given driver's TBA threshold
    undefined) contributes 0 for that term rather than raising."""
    df = result.shapley[["driver", "shapley_contribution"]].copy()
    shap_abs = df["shapley_contribution"].abs()
    shap_norm = shap_abs / shap_abs.max() if shap_abs.max() > 0 else shap_abs * 0

    if result.dia_sobol is None and result.tba_results is None:
        df["priority_score"] = shap_norm
        df["method"] = "shapley_magnitude_only (Phase 1)"
        return df.sort_values("priority_score", ascending=False).reset_index(drop=True)

    if result.dia_sobol is not None:
        sobol_by_driver = result.dia_sobol.set_index("driver")["ST"]
        sobol_vals = df["driver"].map(sobol_by_driver).fillna(0.0)
        sobol_norm = sobol_vals / sobol_vals.max() if sobol_vals.max() > 0 else sobol_vals * 0
    else:
        sobol_norm = shap_norm * 0

    if result.tba_results is not None:
        proximity = []
        for name in df["driver"]:
            tr = result.tba_results.get(name)
            if tr is not None and getattr(tr, "defined", False):
                base_val = getattr(result.v1, name)
                distance = abs(tr.threshold - base_val)
                proximity.append(1.0 / (1.0 + distance))
            else:
                proximity.append(0.0)
        proximity = pd.Series(proximity, index=df.index)
    else:
        proximity = shap_norm * 0

    df["priority_score"] = w1 * shap_norm + w2 * sobol_norm + w3 * proximity
    df["method"] = f"weighted (w1={w1}, w2={w2}, w3={w3}) (Phase 2)"
    return df.sort_values("priority_score", ascending=False).reset_index(drop=True)


def executive_summary(result: PipelineResult, max_words: int = 200) -> str:
    """Deterministic, template-generated executive summary. Never
    LLM-authored (hard constraint 2)."""
    from .model_spec import FCF_MODEL
    spec = result.spec or FCF_MODEL
    out = spec.output_label
    per_share = spec.money_format == "share"

    def amt(v: float) -> str:
        """Magnitude only — for the SIZE of a change, where the direction is
        carried by the surrounding word ('increased by')."""
        return f"${abs(v):,.2f}/share" if per_share else f"${abs(v):,.2f}M"

    def level(v: float) -> str:
        """A LEVEL, which must keep its sign — free cash flow and equity
        value can both be negative, and stripping the minus misstates the
        headline figure."""
        sign = "-" if v < 0 else ""
        return f"{sign}${abs(v):,.2f}/share" if per_share else f"{sign}${abs(v):,.2f}M"

    def samt(v: float) -> str:
        return (("-" if v < 0 else "+") + f"${abs(v):,.2f}") + ("/share" if per_share else "M")

    direction = "increased" if result.total_variance >= 0 else "decreased"

    if len(result.changed) == 0:
        lines = [
            f"No drivers changed between V1 and V2 — {out} is unchanged at "
            f"{level(result.v1_fcf)} (zero-variance case, Blueprint §M edge case 1).",
            f"Structural integrity checks: V1 {'PASS' if result.sia_v1.passed else 'FAIL'}, "
            f"V2 {'PASS' if result.sia_v2.passed else 'FAIL'}.",
        ]
        return " ".join(lines)

    top = result.shapley.reindex(result.shapley["shapley_contribution"].abs().sort_values(ascending=False).index)
    top_driver = top.iloc[0]
    l1_pct = result.interactions["l1_pct_of_variance"]

    lines = [
        f"{out} {direction} by {amt(result.total_variance)} "
        f"(V1 {level(result.v1_fcf)} \u2192 V2 {level(result.v2_fcf)}) across "
        f"{len(result.changed)} changed driver{'' if len(result.changed) == 1 else 's'}: "
        f"{', '.join(result.changed)}.",
        f"The largest single contributor is {top_driver['driver']} at "
        f"{samt(top_driver['shapley_contribution'])} ({top_driver['pct_of_variance']:.0f}% of variance), "
        f"attributed via exact Shapley decomposition (order-independent, "
        f"reconciles to the total variance to 1e-9 tolerance).",
        f"L1 non-additivity is {amt(result.interactions['l1_non_additivity'])} "
        f"({l1_pct:.1f}% of |total variance|) — this is the sum of all pairwise (and higher-order) "
        f"interaction terms and never cancels, unlike the smaller net non-additivity figure "
        f"({samt(result.interactions['net_non_additivity'])}).",
        f"Structural integrity checks: V1 {'PASS' if result.sia_v1.passed else 'FAIL'}, "
        f"V2 {'PASS' if result.sia_v2.passed else 'FAIL'}.",
    ]
    text = " ".join(lines)
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]) + "..."
    return text


def build_report_markdown(result: PipelineResult) -> str:
    """Full deterministic markdown report (Blueprint §J artefact list)."""
    r = result
    md = []
    md.append("# Bridgework — Variance Bridge Report\n")
    md.append("## Executive Conclusion\n")
    md.append(executive_summary(r) + "\n")

    md.append("## Structural Integrity Findings (SIA)\n")
    md.append("```\n" + r.sia_v1.summary() + "\n```\n")
    md.append("```\n" + r.sia_v2.summary() + "\n```\n")

    md.append("## Primary Output Change\n")
    md.append(f"| | Value ($M) |\n|---|---:|\n"
               f"| V1 FCF | {r.v1_fcf:,.4f} |\n"
               f"| V2 FCF | {r.v2_fcf:,.4f} |\n"
               f"| **Total variance** | **{r.total_variance:+,.4f}** |\n")

    md.append("\n## Shapley Attribution (primary, order-independent)\n")
    md.append(r.shapley[["driver", "shapley_contribution", "pct_of_variance", "method"]]
              .to_markdown(index=False, floatfmt=",.3f"))

    md.append("\n\n## Sequential vs Shapley (diagnostic)\n")
    md.append(r.comparison.round(3).to_markdown())

    md.append("\n\n## Non-Additivity Diagnostics\n")
    md.append(
        f"- Net non-additivity: ${r.interactions['net_non_additivity']:+,.4f}M "
        f"(can partially cancel — not the recommended headline risk metric)\n"
        f"- L1 non-additivity: ${r.interactions['l1_non_additivity']:,.4f}M "
        f"({r.interactions['l1_pct_of_variance']:.2f}% of |total variance| — recommended risk metric)\n"
    )
    md.append("\nPairwise interaction terms:\n\n")
    md.append(r.interactions["pairwise"].round(4).to_markdown(index=False))

    md.append("\n\n## Decision-Priority Table\n")
    ranked = decision_priority_table(r)
    md.append(ranked.to_markdown(index=False, floatfmt=",.3f"))

    if r.dia_tornado is not None:
        md.append("\n\n## Driver Impact Analysis — Tornado (local, one-way)\n")
        md.append(
            r.dia_tornado[["driver", "fcf_low", "fcf_high", "impact_range"]]
            .to_markdown(index=False, floatfmt=",.2f")
        )

    if r.dia_sobol is not None:
        md.append("\n\n## Driver Impact Analysis — Sobol (global, variance-based)\n")
        md.append(
            "Answers a different question than Shapley: variance contribution under an "
            "assumed input distribution (±20% uniform, Assumption #1), not the realized "
            "V1→V2 change. A driver can rank highly here even if it never changed.\n\n"
        )
        md.append(r.dia_sobol.round(4).to_markdown(index=False))

    if r.tba_results is not None:
        md.append("\n\n## Threshold & Break-Point Analysis (TBA)\n")
        for name, tr in r.tba_results.items():
            if tr.defined:
                md.append(f"- **{name}**: FCF crosses 0 at {name} = {tr.threshold:.4f} "
                           f"(monotone in [{tr.search_low}, {tr.search_high}])\n")
            else:
                md.append(f"- **{name}**: {tr.reason}\n")

    md.append("\n## Audit Trail\n")
    for k, v in r.manifest.items():
        md.append(f"- **{k}**: {v}\n")

    md.append("\n## Limitations\n")
    md.append(
        "See `docs/limitations.md` for the full register. Key items: unlevered FCF does not "
        "reconcile to reported non-GAAP FCF; model is bilinear (no nonlinear-kink case tested "
        "in this run); Shapley on a discrete V1->V2 change is not Aumann-Shapley.\n"
    )
    return "\n".join(md)


__all__ = [
    "PipelineResult",
    "build_report_markdown",
    "change_register",
    "decision_priority_table",
    "executive_summary",
    "model_snapshot",
    "sequential_vs_shapley",
]
