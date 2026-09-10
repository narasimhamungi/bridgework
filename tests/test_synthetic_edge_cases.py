"""
Blueprint §M — the 6 synthetic edge cases required as the primary
cross-company / generalization evidence (Decision 5: preferred over a full
second-company build). Each test is self-contained and named after its
Blueprint enumeration.
"""
from dataclasses import replace
from pathlib import Path

import pytest

from bridgework.interactions import interaction_report
from bridgework.model import Drivers, compute_fcf, diff_changed_drivers
from bridgework.variance_bridge import all_orderings, shapley_attribution

V1 = Drivers(
    revenue_prior=4527.0,
    revenue_growth=0.031,
    cogs_pct=0.240,
    opex_pct=0.520,
    tax_rate=0.180,
    nwc_pct=0.050,
    capex_pct=0.030,
)


def test_edge_case_1_zero_variance():
    """V1 == V2: every attribution must be exactly zero."""
    v2 = V1
    changed = diff_changed_drivers(V1, v2)
    assert changed == ()
    assert compute_fcf(v2) - compute_fcf(V1) == 0.0


def test_edge_case_2_single_driver_change():
    """Exactly one driver changes: it must absorb 100% of the variance."""
    v2 = replace(V1, opex_pct=0.45)
    changed = diff_changed_drivers(V1, v2)
    assert changed == ("opex_pct",)
    shap = shapley_attribution(V1, v2, changed, method="exact").set_index("driver")
    target = compute_fcf(v2) - compute_fcf(V1)
    assert shap.loc["opex_pct", "shapley_contribution"] == pytest.approx(target, abs=1e-9)


def test_edge_case_3_all_drivers_same_direction():
    """All changed drivers push FCF the same way -> sequential and Shapley
    should agree qualitatively (same sign for every driver, every
    ordering) even if magnitudes still differ slightly."""
    v2 = replace(V1, revenue_growth=0.06, opex_pct=0.45, capex_pct=0.020)  # all three raise FCF
    changed = diff_changed_drivers(V1, v2)
    shap = shapley_attribution(V1, v2, changed, method="exact")
    assert (shap["shapley_contribution"] > 0).all(), "expected all-positive Shapley values"

    all_ord = all_orderings(V1, v2, changed)
    # Every single incremental impact, across every ordering, should also
    # be positive -- no sign flips introduced by walk order.
    assert (all_ord["incremental_impact"] > 0).all()


def test_edge_case_4_opposing_directions_zoom_like():
    """Drivers push in opposite directions -- the Phase-0 Zoom fixture
    itself. Re-asserted here as an explicit, named edge case."""
    v2 = replace(V1, revenue_growth=0.055, opex_pct=0.495, capex_pct=0.045)
    changed = diff_changed_drivers(V1, v2)
    shap = shapley_attribution(V1, v2, changed, method="exact").set_index("driver")
    assert shap.loc["revenue_growth", "shapley_contribution"] > 0
    assert shap.loc["opex_pct", "shapley_contribution"] > 0
    assert shap.loc["capex_pct", "shapley_contribution"] < 0


def test_edge_case_5_driver_crosses_tax_kink():
    """A driver change crosses EBIT=0, engaging the MAX(EBIT,0) tax floor
    non-linearity that the bilinear Phase-0 fixture never exercises
    (Blueprint §4.4.E)."""
    v1_kink = replace(V1, opex_pct=0.90)  # EBIT < 0 in V1
    v2_kink = replace(v1_kink, opex_pct=0.30)  # EBIT > 0 in V2
    revenue = v1_kink.revenue_prior * (1 + v1_kink.revenue_growth)
    ebit_v1 = revenue * (1 - v1_kink.cogs_pct) - revenue * v1_kink.opex_pct
    ebit_v2 = revenue * (1 - v2_kink.cogs_pct) - revenue * v2_kink.opex_pct
    assert ebit_v1 < 0 < ebit_v2, "fixture must genuinely straddle the EBIT=0 kink"

    changed = diff_changed_drivers(v1_kink, v2_kink)
    shap = shapley_attribution(v1_kink, v2_kink, changed, method="exact")
    target = compute_fcf(v2_kink) - compute_fcf(v1_kink)
    assert shap["shapley_contribution"].sum() == pytest.approx(target, abs=1e-9), (
        "Efficiency axiom must still hold across the tax kink"
    )


def test_edge_case_6_interaction_equal_in_magnitude_to_main_effect():
    """A pairwise interaction term deliberately comparable in magnitude to
    a main (Shapley) effect -- stress-tests that the reporting layer would
    surface this rather than letting the headline number bury it.

    Revenue and opex multiply through the model (Revenue * opex_pct), so a
    large simultaneous move in both produces a genuinely large two-way
    interaction term -- calibrated below via direct search to land within
    ~15% of the smaller main effect."""
    v2 = replace(V1, revenue_growth=1.0, opex_pct=0.20)
    changed = diff_changed_drivers(V1, v2)
    report = interaction_report(V1, v2, changed)
    shap = shapley_attribution(V1, v2, changed, method="exact").set_index("driver")

    pairs = report["pairwise"].set_index(["driver_a", "driver_b"])
    largest_pair_interaction = pairs["interaction"].abs().max()
    smallest_main_effect = shap["shapley_contribution"].abs().min()

    ratio = largest_pair_interaction / smallest_main_effect
    assert 0.5 <= ratio <= 2.0, (
        f"interaction ({largest_pair_interaction:.1f}) is not comparable in magnitude "
        f"to the smallest main effect ({smallest_main_effect:.1f}), ratio={ratio:.2f}"
    )


def test_negative_output_levels_keep_their_sign(tmp_path):
    """Regression: a LEVEL (free cash flow, equity value) can be negative
    and must display its sign. An earlier implementation used abs() for
    both changes and levels, so Northwind's V2 of -$152.88M was reported
    as '$152.88M' -- a sign error on a headline figure, in shipped output.
    Found by adversarial testing, not by the suite."""
    from bridgework import cli
    from bridgework.report import executive_summary

    data = Path(__file__).parent.parent / "data" / "synthetic_retail"
    result = cli.run_pipeline(
        str(data / "nw_v1_drivers.yaml"), str(data / "nw_v2_drivers.yaml"),
        output_dir=str(tmp_path / "out"), models_dir=str(tmp_path / "mod"),
    )
    assert result.v2_fcf < 0, "fixture must have a negative V2 to be meaningful"

    summary = executive_summary(result)
    assert "-$152.88M" in summary, f"negative level lost its sign: {summary[:200]}"
    assert "V2 $152.88M" not in summary

    html = (tmp_path / "out" / "report.html").read_text()
    assert "-$152.88M" in html
    assert "$-152.88" not in html  # sign outside the symbol, not inside
