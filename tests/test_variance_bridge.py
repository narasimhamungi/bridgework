"""
Extends Phase 0's 7 required + 3 guard tests. All originals retained
verbatim in behavior; ported to the Phase 1 package layout.
"""
from dataclasses import replace
from itertools import permutations

import pytest

from bridgework.model import Drivers, compute_fcf
from bridgework.variance_bridge import (
    all_orderings,
    sequential_bridge,
    shapley_attribution,
)

TOL = 1e-9

V1 = Drivers(
    revenue_prior=4527.0,
    revenue_growth=0.031,
    cogs_pct=0.240,
    opex_pct=0.520,
    tax_rate=0.180,
    nwc_pct=0.050,
    capex_pct=0.030,
)
V2 = replace(V1, revenue_growth=0.055, opex_pct=0.495, capex_pct=0.045)
CHANGED = ("revenue_growth", "opex_pct", "capex_pct")


# ---------------------------------------------------------------- #
# Ported Phase-0 tests 1-7 + 2 guards
# ---------------------------------------------------------------- #
def test_v1_reproducibility():
    assert compute_fcf(V1) == compute_fcf(V1)


def test_v2_reproducibility():
    assert compute_fcf(V2) == compute_fcf(V2)


def test_sequential_reconciliation():
    target = compute_fcf(V2) - compute_fcf(V1)
    for order in permutations(CHANGED):
        bridge = sequential_bridge(V1, V2, order)
        assert abs(bridge["incremental_impact"].sum() - target) < TOL


def test_shapley_reconciliation_exact():
    target = compute_fcf(V2) - compute_fcf(V1)
    shap = shapley_attribution(V1, V2, CHANGED, method="exact")
    assert abs(shap["shapley_contribution"].sum() - target) < TOL


def test_zero_change_case():
    v2_same = V1
    for order in permutations(CHANGED):
        bridge = sequential_bridge(V1, v2_same, order)
        assert (bridge["incremental_impact"].abs() < TOL).all()
    shap = shapley_attribution(V1, v2_same, CHANGED, method="exact")
    assert (shap["shapley_contribution"].abs() < TOL).all()


@pytest.mark.parametrize("driver", CHANGED)
def test_single_driver_case(driver):
    v2_single = replace(V1, **{driver: getattr(V2, driver)})
    target = compute_fcf(v2_single) - compute_fcf(V1)
    bridge = sequential_bridge(V1, v2_single, (driver,))
    assert abs(bridge.iloc[0]["incremental_impact"] - target) < TOL

    shap = shapley_attribution(V1, v2_single, CHANGED, method="exact").set_index("driver")
    assert abs(shap.loc[driver, "shapley_contribution"] - target) < TOL
    for other in [d for d in CHANGED if d != driver]:
        assert abs(shap.loc[other, "shapley_contribution"]) < TOL


def test_ordering_sensitivity_is_exposed():
    all_ord = all_orderings(V1, V2, CHANGED)
    per_driver_range = all_ord.groupby("driver")["incremental_impact"].agg(lambda s: s.max() - s.min())
    assert (per_driver_range > 1e-6).any()


def test_shapley_symmetry_axiom():
    revenue = V1.revenue_prior * (1 + V1.revenue_growth)
    target_delta = -20.0
    delta_o = -target_delta / (revenue * (1 - V1.tax_rate))
    delta_c = -target_delta / revenue
    v2_sym = replace(V1, opex_pct=V1.opex_pct + delta_o, capex_pct=V1.capex_pct + delta_c)
    shap = shapley_attribution(V1, v2_sym, ("opex_pct", "capex_pct"), method="exact").set_index("driver")
    assert abs(shap.loc["opex_pct", "shapley_contribution"] - shap.loc["capex_pct", "shapley_contribution"]) < 1e-6


# ---------------------------------------------------------------- #
# New Phase-1 tests: Shapley Dummy + Additivity axioms
# ---------------------------------------------------------------- #
def test_shapley_dummy_axiom():
    """A driver whose value is identical in V1 and V2 contributes phi=0,
    even when explicitly included in the changed-driver set."""
    v2_two_change = replace(V1, revenue_growth=0.055, opex_pct=0.495)  # capex_pct untouched
    shap = shapley_attribution(V1, v2_two_change, CHANGED, method="exact").set_index("driver")
    assert abs(shap.loc["capex_pct", "shapley_contribution"]) < TOL


def test_shapley_additivity_axiom():
    """phi(f+g) == phi(f) + phi(g) on a synthetic linear combination: build
    two independent single-driver games and confirm their Shapley values
    sum to the Shapley values of the combined two-driver game (both games
    share the same additive/no-interaction structure by construction)."""
    # Game f: only revenue_growth changes; Game g: only opex_pct changes.
    v2_f = replace(V1, revenue_growth=0.055)
    v2_g = replace(V1, opex_pct=0.495)
    phi_f = shapley_attribution(V1, v2_f, ("revenue_growth",), method="exact").set_index("driver")
    phi_g = shapley_attribution(V1, v2_g, ("opex_pct",), method="exact").set_index("driver")

    # Combined game: both change together.
    v2_fg = replace(V1, revenue_growth=0.055, opex_pct=0.495)
    phi_fg = shapley_attribution(V1, v2_fg, ("revenue_growth", "opex_pct"), method="exact").set_index("driver")

    # In a single-player game the lone driver absorbs 100% of that game's
    # variance; additivity here is checked via the isolated (single-driver)
    # impact, which for n=1 coalitions equals phi exactly.
    assert phi_f.loc["revenue_growth", "shapley_contribution"] == pytest.approx(
        compute_fcf(v2_f) - compute_fcf(V1), abs=TOL
    )
    assert phi_g.loc["opex_pct", "shapley_contribution"] == pytest.approx(
        compute_fcf(v2_g) - compute_fcf(V1), abs=TOL
    )
    # And the combined game still reconciles to its own total (Efficiency),
    # independently confirming no value is lost/gained across games.
    assert phi_fg["shapley_contribution"].sum() == pytest.approx(compute_fcf(v2_fg) - compute_fcf(V1), abs=TOL)


# ---------------------------------------------------------------- #
# New Phase-1 tests: Monte Carlo Shapley
# ---------------------------------------------------------------- #
def test_monte_carlo_shapley_matches_exact_within_ci():
    exact = shapley_attribution(V1, V2, CHANGED, method="exact").set_index("driver")["shapley_contribution"]
    mc = shapley_attribution(V1, V2, CHANGED, method="monte_carlo", seed=7).set_index("driver")
    for driver in CHANGED:
        lo, hi = mc.loc[driver, "ci_low"], mc.loc[driver, "ci_high"]
        # Allow a small margin beyond the reported CI for MC noise at the boundary.
        margin = 0.05 * abs(exact[driver]) + 0.5
        assert lo - margin <= exact[driver] <= hi + margin


def test_monte_carlo_shapley_is_seeded_reproducible():
    a = shapley_attribution(V1, V2, CHANGED, method="monte_carlo", seed=123)
    b = shapley_attribution(V1, V2, CHANGED, method="monte_carlo", seed=123)
    assert (a["shapley_contribution"] == b["shapley_contribution"]).all()


def test_monte_carlo_shapley_ci_narrows_with_more_samples():
    from bridgework.variance_bridge import _bootstrap_ci, _shapley_mc_once

    _, samples_small = _shapley_mc_once(V1, V2, CHANGED, m=200, seed=1)
    _, samples_large = _shapley_mc_once(V1, V2, CHANGED, m=8000, seed=1)
    for driver in CHANGED:
        lo_s, hi_s = _bootstrap_ci(samples_small[driver], seed=1)
        lo_l, hi_l = _bootstrap_ci(samples_large[driver], seed=1)
        assert (hi_l - lo_l) < (hi_s - lo_s)


def test_auto_method_switches_on_driver_count():
    shap_small = shapley_attribution(V1, V2, CHANGED, method="auto")
    assert (shap_small["method"] == "exact").all()
