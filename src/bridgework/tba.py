"""
Threshold & Break-Point Analysis (TBA) — Blueprint §D, §G, Phase 2,
conditional on the monotonicity guard (challenge 3).

Definition: the input value of a single driver at which a defined
predicate flips (e.g. FCF < 0). Method: scipy.optimize.brentq bisection.

MANDATORY monotonicity precondition (hard constraint: no silent
fallback): before invoking Brent's method, scan a coarse grid across the
driver's search range and count sign changes in the target function. If
the count != 1, TBA refuses with an explicit "threshold undefined --
non-monotone in search range" result rather than returning a spurious
root. This exists because the tax floor (MAX(EBIT,0)) makes some
driver/predicate combinations genuinely non-monotone -- Phase 1's
synthetic edge case 5 (tests/test_synthetic_edge_cases.py) proved the
Efficiency axiom survives crossing that kink; this module is what makes
the kink safe to search across, or safely refuse to.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

import numpy as np
from scipy.optimize import brentq

from .model import Drivers, compute_fcf

DEFAULT_GRID_POINTS = 11

# Default search ranges per canonical driver role (Assumption #3,
# documented and overridable) -- wide enough to plausibly reach FCF=0 for
# an economically sensible model, narrow enough to avoid nonsensical
# negative-revenue-multiplier territory (revenue_growth > -1).
DEFAULT_SEARCH_RANGES: dict[str, tuple] = {
    "revenue_growth": (-0.95, 3.0),
    "cogs_pct": (0.0, 1.5),
    "opex_pct": (0.0, 1.5),
    "tax_rate": (0.0, 1.5),
    "nwc_pct": (0.0, 1.5),
    "capex_pct": (0.0, 1.5),
    # DCF model drivers. WACC's lower bound sits above plausible terminal
    # growth so the search cannot wander into the WACC <= g region where
    # the model is undefined (dcf.InvalidDCFError).
    "growth_explicit": (-0.50, 1.00),
    "wacc": (0.045, 0.40),
    "terminal_growth": (-0.20, 0.040),
    "net_debt": (0.0, 500000.0),
}


@dataclass
class ThresholdResult:
    driver: str
    target_name: str
    target_value: float
    search_low: float
    search_high: float
    defined: bool
    threshold: float | None
    n_sign_changes: int
    reason: str


def _target_fn_default(target: str):
    if target == "fcf":
        return compute_fcf
    raise ValueError(f"Unknown built-in target {target!r}; pass target_fn explicitly")


def find_threshold(
    base: Drivers,
    driver: str,
    search_range: Sequence[float],
    target: float = 0.0,
    target_fn: Callable[[Drivers], float] | None = None,
    target_name: str = "fcf",
    n_grid: int = DEFAULT_GRID_POINTS,
) -> ThresholdResult:
    """Find the value of `driver` (holding all others at `base`'s values)
    at which target_fn(...) crosses `target` (default: FCF crosses 0).

    Refuses (defined=False) rather than guessing if the function is not
    monotone across search_range -- confirmed via an n_grid-point coarse
    scan counting sign changes in (g(x) - target).
    """
    if target_fn is None:
        target_fn = _target_fn_default(target_name)

    lo, hi = search_range
    if lo >= hi:
        raise ValueError(f"search_range must be (low, high) with low < high, got {search_range}")

    def g(x: float) -> float:
        return target_fn(replace(base, **{driver: x})) - target

    grid = np.linspace(lo, hi, n_grid)
    values = np.array([g(x) for x in grid])

    if np.any(values == 0):
        # An exact hit on the grid -- still validate monotonicity around it
        # rather than short-circuiting, since a zero coinciding with a
        # local extremum is exactly the ambiguous case this guard exists
        # to catch.
        values = values + 0.0  # no-op, keeps the sign-change logic below uniform

    signs = np.sign(values)
    signs_nonzero = signs[signs != 0]
    sign_changes = int(np.sum(np.diff(signs_nonzero) != 0)) if len(signs_nonzero) > 1 else 0

    if sign_changes != 1:
        if sign_changes == 0:
            reason = (
                f"threshold undefined — target never crossed within search range "
                f"[{lo}, {hi}]: 0 sign changes across {n_grid}-point grid scan. The "
                f"function may be perfectly monotone here; the crossing simply lies "
                f"outside this range. Widen search_range to locate it."
            )
        else:
            reason = (
                f"threshold undefined — non-monotone in search range [{lo}, {hi}]: "
                f"found {sign_changes} sign changes across {n_grid}-point grid scan "
                f"(exactly 1 required for a well-defined root). Multiple crossings "
                f"exist; narrow search_range to isolate the one of interest."
            )
        return ThresholdResult(
            driver=driver,
            target_name=target_name,
            target_value=target,
            search_low=lo,
            search_high=hi,
            defined=False,
            threshold=None,
            n_sign_changes=sign_changes,
            reason=reason,
        )

    # Exactly one sign change: locate the bracketing grid interval and
    # hand it to Brent's method for a precise root.
    bracket_lo = bracket_hi = None
    for i in range(len(grid) - 1):
        if values[i] == 0:
            return ThresholdResult(
                driver=driver,
                target_name=target_name,
                target_value=target,
                search_low=lo,
                search_high=hi,
                defined=True,
                threshold=float(grid[i]),
                n_sign_changes=1,
                reason="exact grid hit",
            )
        if values[i] * values[i + 1] < 0:
            bracket_lo, bracket_hi = grid[i], grid[i + 1]
            break

    if bracket_lo is None:
        return ThresholdResult(  # pragma: no cover — defensive, should be unreachable given sign_changes==1
            driver=driver,
            target_name=target_name,
            target_value=target,
            search_low=lo,
            search_high=hi,
            defined=False,
            threshold=None,
            n_sign_changes=sign_changes,
            reason="threshold undefined — could not bracket the sign change for Brent's method",
        )

    root = brentq(g, bracket_lo, bracket_hi, xtol=1e-9)

    # Post-check: brentq brackets a SIGN CHANGE, which a discontinuity also
    # produces. On a step function it converges to the jump and reports a
    # confident root where none exists. Verify the residual actually
    # vanishes before claiming a threshold (adversarial review finding).
    residual = abs(g(root))
    scale = max(abs(target), 1.0)
    if residual > 1e-6 * scale:
        return ThresholdResult(
            driver=driver,
            target_name=target_name,
            target_value=target,
            search_low=lo,
            search_high=hi,
            defined=False,
            threshold=None,
            n_sign_changes=1,
            reason=(
                f"threshold undefined — the sign change at ~{root:.6g} is a discontinuity, "
                f"not a root: |f(x) - target| = {residual:.3g} there. The target jumps across "
                f"the level without ever equalling it."
            ),
        )

    return ThresholdResult(
        driver=driver,
        target_name=target_name,
        target_value=target,
        search_low=lo,
        search_high=hi,
        defined=True,
        threshold=float(root),
        n_sign_changes=1,
        reason="monotone in search range; root located via Brent's method",
    )


__all__ = ["DEFAULT_GRID_POINTS", "DEFAULT_SEARCH_RANGES", "ThresholdResult", "find_threshold"]
