"""
Model registry — Phase 6.

Bridgework's engine (attribution, interactions, sensitivity, thresholds)
is model-agnostic: it needs only a deterministic function from a frozen
driver dataclass to a scalar. A ModelSpec bundles everything the
*pipeline* additionally needs — driver vocabulary, Excel layout, output
labels — so adding a model is a registry entry rather than a rewrite.

Honest scope note: the Blueprint §M mapping-only rule was proven for
adding a *company* (three YAML files, zero source changes). Adding a
*model* is a different and larger thing: it needs a new compute function
and Excel contract, so it is a code change by nature. This registry is
what keeps that change contained to one new module plus one entry here.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from . import dcf as _dcf
from . import model as _fcf


@dataclass(frozen=True)
class ModelSpec:
    """Everything the pipeline needs to run a given model end to end."""

    key: str
    display_name: str
    drivers_cls: type
    roles: tuple[str, ...]
    labels: dict[str, str]
    compute: Callable[[object], float]
    line_items: Callable[[object], dict[str, float]]
    calc_lines: tuple  # (label, formula_template, note) — Excel Calc sheet
    output_label: str
    output_unit: str
    money_format: str  # "M" for $M totals, "share" for per-share


# --------------------------------------------------------------------- #
# FCF model (Phases 1-5) — unchanged behaviour, now described declaratively
# --------------------------------------------------------------------- #
_FCF_CALC_LINES = (
    ("Revenue (prior)", "={ref[revenue_prior]}", "Anchor: prior-period revenue"),
    ("Revenue", "=B4*(1+{ref[revenue_growth]})", "prior * (1 + growth)"),
    ("Gross Profit", "=B5*(1-{ref[cogs_pct]})", "Revenue * (1 - COGS%)"),
    ("Opex", "=B5*{ref[opex_pct]}", "Revenue * Opex%"),
    ("EBIT", "=B6-B7", "Gross Profit - Opex"),
    ("Taxes", "=MAX(B8,0)*{ref[tax_rate]}", "max(EBIT,0) * tax rate"),
    ("NOPAT", "=B8-B9", "EBIT - Taxes"),
    ("Delta NWC", "=B5*{ref[nwc_pct]}-B4*{ref[nwc_pct]}", "(Rev - PriorRev) * NWC%"),
    ("CapEx", "=B5*{ref[capex_pct]}", "Revenue * CapEx%"),
    ("Free Cash Flow", "=B10-B11-B12", "NOPAT - dNWC - CapEx"),
)

FCF_MODEL = ModelSpec(
    key="fcf",
    display_name="Unlevered Free Cash Flow",
    drivers_cls=_fcf.Drivers,
    roles=_fcf.CANONICAL_ROLES,
    labels=_fcf.DRIVER_LABELS,
    compute=_fcf.compute_fcf,
    line_items=_fcf.compute_line_items,
    calc_lines=_FCF_CALC_LINES,
    output_label="Free Cash Flow",
    output_unit="$M",
    money_format="M",
)


# --------------------------------------------------------------------- #
# DCF valuation model (Phase 6)
# --------------------------------------------------------------------- #
# Drivers sit at Drivers!B4:B9 in canonical order:
#   B4 fcf_base, B5 growth_explicit, B6 wacc,
#   B7 terminal_growth, B8 net_debt, B9 shares_outstanding
#
# Calc sheet rows 4..: five explicit-period FCFs, five PVs, then the
# terminal-value bridge down to implied share price.
_DCF_CALC_LINES = (
    ("FCF year 1", "={ref[fcf_base]}*(1+{ref[growth_explicit]})", "base * (1+g)"),
    ("FCF year 2", "=B4*(1+{ref[growth_explicit]})", "prior year * (1+g)"),
    ("FCF year 3", "=B5*(1+{ref[growth_explicit]})", "prior year * (1+g)"),
    ("FCF year 4", "=B6*(1+{ref[growth_explicit]})", "prior year * (1+g)"),
    ("FCF year 5", "=B7*(1+{ref[growth_explicit]})", "prior year * (1+g)"),
    ("PV of year 1", "=B4/(1+{ref[wacc]})^1", "discounted at WACC"),
    ("PV of year 2", "=B5/(1+{ref[wacc]})^2", "discounted at WACC"),
    ("PV of year 3", "=B6/(1+{ref[wacc]})^3", "discounted at WACC"),
    ("PV of year 4", "=B7/(1+{ref[wacc]})^4", "discounted at WACC"),
    ("PV of year 5", "=B8/(1+{ref[wacc]})^5", "discounted at WACC"),
    ("PV of explicit period", "=SUM(B9:B13)", "sum of discounted FCFs"),
    ("Terminal value", "=B8*(1+{ref[terminal_growth]})/({ref[wacc]}-{ref[terminal_growth]})", "Gordon Growth on year-5 FCF"),
    ("PV of terminal value", "=B15/(1+{ref[wacc]})^5", "TV discounted 5 years"),
    ("Enterprise value", "=B14+B16", "PV explicit + PV terminal"),
    ("Net debt", "={ref[net_debt]}", "input"),
    ("Equity value", "=B17-B18", "EV - net debt"),
    ("Shares outstanding", "={ref[shares_outstanding]}", "input"),
    ("Implied share price", "=B19/B20", "equity value / shares"),
)

DCF_MODEL = ModelSpec(
    key="dcf",
    display_name="DCF Valuation (implied share price)",
    drivers_cls=_dcf.DCFDrivers,
    roles=_dcf.DCF_ROLES,
    labels=_dcf.DCF_LABELS,
    compute=_dcf.compute_share_price,
    line_items=_dcf.compute_dcf_line_items,
    calc_lines=_DCF_CALC_LINES,
    output_label="Implied share price",
    output_unit="$/share",
    money_format="share",
)


MODELS: dict[str, ModelSpec] = {
    FCF_MODEL.key: FCF_MODEL,
    DCF_MODEL.key: DCF_MODEL,
}

DEFAULT_MODEL_KEY = "fcf"


def get_model(key: str | None) -> ModelSpec:
    if key is None:
        return MODELS[DEFAULT_MODEL_KEY]
    if key not in MODELS:
        raise ValueError(f"Unknown model {key!r}. Available: {sorted(MODELS)}")
    return MODELS[key]


def diff_changed(v1, v2, spec: ModelSpec) -> tuple:
    """Roles whose value differs between two driver sets, in canonical order."""
    return tuple(r for r in spec.roles if getattr(v1, r) != getattr(v2, r))


__all__ = ["DCF_MODEL", "DEFAULT_MODEL_KEY", "FCF_MODEL", "MODELS", "ModelSpec", "diff_changed", "get_model"]
