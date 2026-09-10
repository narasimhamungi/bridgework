"""
DCF valuation model — Phase 6.

Output: implied share price. This is the IB / equity-research native
question ("why did our price target move from $52 to $58 between last
week's model and this week's?"), and it is a materially better
demonstration of the attribution problem than the FCF model, because a
DCF is severely non-linear where the FCF model is nearly bilinear.

The reason is the Gordon Growth denominator. Terminal value is

    TV = FCF_n * (1 + g) / (WACC - g)

so WACC and terminal growth interact multiplicatively through a
*difference in the denominator*. Measured on a realistic fixture with a
tight WACC-g spread (7.5% / 3.5%), L1 non-additivity is ~23% of the total
change versus ~10% on the Zoom FCF model, and the WACC x terminal-growth
pair alone accounts for over half of it. A sequential bridge is therefore
not marginally misleading here -- it is materially misleading.

Forecast horizon is a fixed model constant (5 years), not a driver:
it is an integer and would not behave sensibly under Shapley coalition
enumeration or continuous sensitivity perturbation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

FORECAST_YEARS = 5

DCF_ROLES = (
    "fcf_base",
    "growth_explicit",
    "wacc",
    "terminal_growth",
    "net_debt",
    "shares_outstanding",
)

DCF_LABELS = {
    "fcf_base": "Base-year free cash flow ($M)",
    "growth_explicit": "FCF growth, explicit period (%)",
    "wacc": "Weighted average cost of capital (%)",
    "terminal_growth": "Terminal growth rate (%)",
    "net_debt": "Net debt ($M)",
    "shares_outstanding": "Shares outstanding (M)",
}


class InvalidDCFError(ValueError):
    """Raised when a driver combination makes the DCF undefined.

    This matters more than it first appears. Shapley attribution evaluates
    every *coalition* -- every mix of V1 and V2 driver values -- so a
    coalition can pair V1's WACC with V2's terminal growth and produce
    WACC <= g even when V1 and V2 are each perfectly valid on their own.
    The model refuses explicitly rather than returning a negative or
    absurd terminal value, in the same spirit as the TBA monotonicity
    guard: no silent nonsense in the calculation path.
    """


@dataclass(frozen=True)
class DCFDrivers:
    """Six drivers of an implied share price."""

    fcf_base: float
    growth_explicit: float
    wacc: float
    terminal_growth: float
    net_debt: float
    shares_outstanding: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, float]) -> DCFDrivers:
        missing = set(DCF_ROLES) - set(d)
        if missing:
            raise ValueError(f"Missing DCF driver roles: {sorted(missing)}")
        extra = set(d) - set(DCF_ROLES)
        if extra:
            raise ValueError(f"Unknown DCF driver roles: {sorted(extra)}")
        return cls(**{role: float(d[role]) for role in DCF_ROLES})


def _validate(d: DCFDrivers) -> None:
    if d.wacc <= d.terminal_growth:
        raise InvalidDCFError(
            f"DCF undefined: WACC ({d.wacc:.4f}) must exceed terminal growth "
            f"({d.terminal_growth:.4f}). Note this can arise from a Shapley "
            f"coalition mixing V1 and V2 values even when both versions are "
            f"individually valid — check that min(WACC) > max(terminal growth) "
            f"across the two versions being compared."
        )
    if d.shares_outstanding <= 0:
        raise InvalidDCFError(f"shares_outstanding must be > 0, got {d.shares_outstanding}")


def compute_share_price(d: DCFDrivers) -> float:
    """Implied share price. Deterministic, no I/O, no randomness."""
    _validate(d)
    pv_explicit = 0.0
    fcf = d.fcf_base
    for t in range(1, FORECAST_YEARS + 1):
        fcf *= 1.0 + d.growth_explicit
        pv_explicit += fcf / ((1.0 + d.wacc) ** t)
    terminal_value = fcf * (1.0 + d.terminal_growth) / (d.wacc - d.terminal_growth)
    pv_terminal = terminal_value / ((1.0 + d.wacc) ** FORECAST_YEARS)
    enterprise_value = pv_explicit + pv_terminal
    equity_value = enterprise_value - d.net_debt
    return equity_value / d.shares_outstanding


def compute_dcf_line_items(d: DCFDrivers) -> dict[str, float]:
    """Every intermediate, in calculation order — used by the Excel
    exporter and the model snapshot."""
    _validate(d)
    items: dict[str, float] = {}
    pv_explicit = 0.0
    fcf = d.fcf_base
    for t in range(1, FORECAST_YEARS + 1):
        fcf *= 1.0 + d.growth_explicit
        pv = fcf / ((1.0 + d.wacc) ** t)
        pv_explicit += pv
        items[f"FCF year {t}"] = fcf
        items[f"PV of year {t}"] = pv
    terminal_value = fcf * (1.0 + d.terminal_growth) / (d.wacc - d.terminal_growth)
    pv_terminal = terminal_value / ((1.0 + d.wacc) ** FORECAST_YEARS)
    enterprise_value = pv_explicit + pv_terminal
    equity_value = enterprise_value - d.net_debt
    items["PV of explicit period"] = pv_explicit
    items["Terminal value"] = terminal_value
    items["PV of terminal value"] = pv_terminal
    items["Enterprise value"] = enterprise_value
    items["Net debt"] = d.net_debt
    items["Equity value"] = equity_value
    items["Shares outstanding"] = d.shares_outstanding
    items["Implied share price"] = equity_value / d.shares_outstanding
    return items


def terminal_value_share(d: DCFDrivers) -> float:
    """Fraction of enterprise value sitting in the terminal value. A
    standard IB sanity check — above ~75% the valuation is mostly an
    assumption about perpetuity, not about the forecast."""
    items = compute_dcf_line_items(d)
    return items["PV of terminal value"] / items["Enterprise value"]


__all__ = [
    "DCF_LABELS",
    "DCF_ROLES",
    "FORECAST_YEARS",
    "DCFDrivers",
    "InvalidDCFError",
    "compute_dcf_line_items",
    "compute_share_price",
    "terminal_value_share",
]
