from dataclasses import replace

import pytest

from bridgework.model import Drivers, compute_fcf
from bridgework.tba import find_threshold

V1 = Drivers(
    revenue_prior=4527.0,
    revenue_growth=0.031,
    cogs_pct=0.240,
    opex_pct=0.520,
    tax_rate=0.180,
    nwc_pct=0.050,
    capex_pct=0.030,
)


def test_monotone_case_finds_correct_root():
    r = find_threshold(V1, "opex_pct", (0.30, 0.99))
    assert r.defined
    assert r.n_sign_changes == 1
    fcf_at_root = compute_fcf(replace(V1, opex_pct=r.threshold))
    assert abs(fcf_at_root) < 1e-6


def test_zero_sign_changes_refuses():
    """Search range too narrow to ever reach FCF=0 -- must refuse, not
    guess by extrapolation, AND must say the crossing is outside the
    range rather than falsely blaming non-monotonicity."""
    r = find_threshold(V1, "opex_pct", (0.30, 0.35))
    assert not r.defined
    assert r.n_sign_changes == 0
    assert "never crossed within search range" in r.reason
    assert "non-monotone" not in r.reason
    assert r.threshold is None


def test_zero_and_multiple_crossings_give_distinct_diagnoses():
    """A no-crossing result and a multiple-crossing result are different
    problems with different fixes (widen vs narrow the range) -- the
    reason strings must not conflate them."""

    def parabola_target(d: Drivers) -> float:
        return -((d.opex_pct - 0.6) ** 2) + 0.01

    zero_case = find_threshold(V1, "opex_pct", (0.30, 0.35))
    multi_case = find_threshold(
        V1, "opex_pct", (0.30, 0.90), target_fn=parabola_target, target_name="synthetic_parabola"
    )
    assert "Widen" in zero_case.reason
    assert "narrow" in multi_case.reason.lower()
    assert zero_case.reason != multi_case.reason


def test_multiple_sign_changes_refuses():
    """Core monotonicity-guard logic, exercised via a deliberately
    non-monotone synthetic target_fn (a parabola) -- proves the guard
    itself is correct independent of whether compute_fcf can produce a
    hump for any single driver (see test_fcf_is_provably_single_driver_
    monotone below: it cannot, for this model's specific algebra)."""

    def parabola_target(d: Drivers) -> float:
        x = d.opex_pct
        return -((x - 0.6) ** 2) + 0.01  # crosses zero at x=0.5 and x=0.7

    r = find_threshold(V1, "opex_pct", (0.30, 0.90), target_fn=parabola_target, target_name="synthetic_parabola")
    assert not r.defined
    assert r.n_sign_changes == 2
    assert r.threshold is None


def test_invalid_search_range_raises():
    with pytest.raises(ValueError, match="low < high"):
        find_threshold(V1, "opex_pct", (0.9, 0.3))


def test_exact_grid_hit_is_handled():
    """If FCF happens to land exactly on zero at a grid point, the result
    must still report defined=True with that exact value, not error."""
    # opex_pct at the known root from test_monotone_case_finds_correct_root
    # is ~0.7216; construct a search range whose grid lands very close to
    # it isn't guaranteed exact, so instead test the mechanism directly
    # via a target_fn engineered to hit exactly zero on the grid.
    root_x = 0.5

    def linear_target(d: Drivers) -> float:
        return d.opex_pct - root_x

    r = find_threshold(V1, "opex_pct", (0.3, 0.7), target_fn=linear_target, target_name="synthetic_linear", n_grid=5)
    assert r.defined
    assert r.threshold == pytest.approx(root_x, abs=1e-9)


def test_fcf_is_provably_single_driver_monotone():
    """Documents a real, mathematically-grounded finding about this
    model's structure (Blueprint §4.4.E caveat, extended): holding all
    other drivers fixed, FCF is monotone (or constant) in EVERY single
    canonical driver across its full economically-valid range, including
    across the tax floor kink -- because each driver enters FCF through
    at most a two-piece piecewise-LINEAR relationship whose pieces never
    have opposite-sign slopes for this specific formula. A genuine
    'hump' non-monotonicity is therefore impossible for a single-driver
    TBA sweep on this model; the guard exists for the general case
    (verified above) and for future, richer models, not because this
    particular fixture needs it."""
    import numpy as np

    for driver in ("revenue_growth", "cogs_pct", "opex_pct", "tax_rate", "nwc_pct", "capex_pct"):
        base_val = getattr(V1, driver)
        xs = np.linspace(max(base_val - 5.0, -0.99), base_val + 5.0, 200)
        ys = np.array([compute_fcf(replace(V1, **{driver: x})) for x in xs])
        diffs = np.diff(ys)
        signs = np.sign(diffs[diffs != 0])
        # A monotone (possibly piecewise-linear with a slope-magnitude-only
        # kink) function has all successive differences of the SAME sign.
        assert len(set(signs)) <= 1, f"{driver} was NOT single-driver monotone -- update this finding"


def test_discontinuity_is_refused_not_reported_as_a_root():
    """Adversarial review finding: brentq brackets a SIGN CHANGE, which a
    discontinuity produces just as a root does. On a step function the old
    implementation returned defined=True with a confident threshold at the
    jump, where the function never actually equals the target. The residual
    post-check closes the only path where TBA lied."""

    def step(d: Drivers) -> float:
        return -1.0 if d.opex_pct < 0.75 else 1.0

    r = find_threshold(V1, "opex_pct", (0.3, 1.2), target_fn=step, target_name="step")
    assert not r.defined
    assert r.threshold is None
    assert "discontinuity" in r.reason


def test_genuine_root_still_accepted_after_residual_check():
    """The post-check must not reject real roots."""
    r = find_threshold(V1, "opex_pct", (0.30, 0.99))
    assert r.defined
    assert abs(compute_fcf(replace(V1, opex_pct=r.threshold))) < 1e-6
