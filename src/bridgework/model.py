"""
Bridgework — canonical calculation module.

This is the single source of truth for the financial calculation. Excel
workbooks are a byproduct (Blueprint §B, LOCKED decision): they are
generated from this module's formulas and are never themselves parsed for
the calculation logic. This module has zero I/O and zero dependence on
company identity — it operates purely on the seven canonical driver roles
defined in schema/canonical_schema.yaml. A new company/industry requires a
new mapping into these seven fields, never a change to this file
(Blueprint §D, §M mapping-only rule).

    Revenue        = revenue_prior * (1 + revenue_growth)
    Gross Profit   = Revenue * (1 - cogs_pct)
    EBIT           = Gross Profit - Revenue * opex_pct
    Taxes          = max(EBIT, 0) * tax_rate
    NOPAT          = EBIT - Taxes
    Delta NWC      = Revenue * nwc_pct - Revenue_prior * nwc_pct
    CapEx          = Revenue * capex_pct
    FCF            = NOPAT - Delta NWC - CapEx
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

SCHEMA_VERSION = "1.0.0"

CANONICAL_ROLES = (
    "revenue_prior",
    "revenue_growth",
    "cogs_pct",
    "opex_pct",
    "tax_rate",
    "nwc_pct",
    "capex_pct",
)

DRIVER_LABELS: dict[str, str] = {
    "revenue_prior": "Revenue (prior year, $M)",
    "revenue_growth": "Revenue growth (%)",
    "cogs_pct": "COGS (% of revenue)",
    "opex_pct": "Opex (% of revenue)",
    "tax_rate": "Effective tax rate (%)",
    "nwc_pct": "NWC intensity (% of revenue)",
    "capex_pct": "CapEx (% of revenue)",
}


@dataclass(frozen=True)
class Drivers:
    """The seven canonical drivers of the Bridgework FCF model.

    Frozen so a Drivers instance is hashable & immutable — required for
    safe Shapley coalition enumeration (Blueprint §B, LOCKED).
    """

    revenue_prior: float
    revenue_growth: float
    cogs_pct: float
    opex_pct: float
    tax_rate: float
    nwc_pct: float
    capex_pct: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, float]) -> Drivers:
        missing = set(CANONICAL_ROLES) - set(d)
        if missing:
            raise ValueError(f"Missing canonical driver roles: {sorted(missing)}")
        extra = set(d) - set(CANONICAL_ROLES)
        if extra:
            raise ValueError(f"Unknown driver roles (not in canonical schema): {sorted(extra)}")
        return cls(**{role: float(d[role]) for role in CANONICAL_ROLES})


def compute_fcf(d: Drivers) -> float:
    """Deterministic Free Cash Flow calculation. No randomness, no I/O."""
    revenue = d.revenue_prior * (1.0 + d.revenue_growth)
    gross_profit = revenue * (1.0 - d.cogs_pct)
    opex = revenue * d.opex_pct
    ebit = gross_profit - opex
    taxes = max(ebit, 0.0) * d.tax_rate
    nopat = ebit - taxes
    delta_nwc = revenue * d.nwc_pct - d.revenue_prior * d.nwc_pct
    capex = revenue * d.capex_pct
    return nopat - delta_nwc - capex


def compute_line_items(d: Drivers) -> dict[str, float]:
    """Expose every intermediate line item, in calculation order — used by
    the Excel exporter and by SIA's cross-reference checks."""
    revenue = d.revenue_prior * (1.0 + d.revenue_growth)
    gross_profit = revenue * (1.0 - d.cogs_pct)
    opex = revenue * d.opex_pct
    ebit = gross_profit - opex
    taxes = max(ebit, 0.0) * d.tax_rate
    nopat = ebit - taxes
    delta_nwc = revenue * d.nwc_pct - d.revenue_prior * d.nwc_pct
    capex = revenue * d.capex_pct
    fcf = nopat - delta_nwc - capex
    return {
        "Revenue (prior)": d.revenue_prior,
        "Revenue": revenue,
        "Gross Profit": gross_profit,
        "Opex": opex,
        "EBIT": ebit,
        "Taxes": taxes,
        "NOPAT": nopat,
        "Delta NWC": delta_nwc,
        "CapEx": capex,
        "Free Cash Flow": fcf,
    }


def diff_changed_drivers(v1: Drivers, v2: Drivers) -> tuple:
    """Return the tuple of canonical role names whose value differs
    between v1 and v2, in canonical order."""
    return tuple(
        role for role in CANONICAL_ROLES if getattr(v1, role) != getattr(v2, role)
    )


__all__ = [
    "CANONICAL_ROLES",
    "DRIVER_LABELS",
    "SCHEMA_VERSION",
    "Drivers",
    "compute_fcf",
    "compute_line_items",
    "diff_changed_drivers",
]
