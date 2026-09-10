import pytest

from bridgework.dia import morris_screening, sobol_indices, tornado
from bridgework.model import Drivers, compute_fcf

V1 = Drivers(
    revenue_prior=4527.0,
    revenue_growth=0.031,
    cogs_pct=0.240,
    opex_pct=0.520,
    tax_rate=0.180,
    nwc_pct=0.050,
    capex_pct=0.030,
)
ALL_DRIVERS = ("revenue_growth", "cogs_pct", "opex_pct", "tax_rate", "nwc_pct", "capex_pct")


def test_tornado_ranks_by_impact_descending():
    df = tornado(V1, ALL_DRIVERS)
    assert list(df["impact_range"]) == sorted(df["impact_range"], reverse=True)


def test_tornado_fcf_base_matches_compute_fcf():
    df = tornado(V1, ALL_DRIVERS)
    expected = compute_fcf(V1)
    assert all(v == pytest.approx(expected, abs=1e-9) for v in df["fcf_base"])


def test_tornado_opex_dominates_this_fixture():
    """Sanity check against a known property of this specific model: opex_pct
    (52% base, largest absolute driver-to-output leverage) should dominate
    the tornado ranking over a low-base driver like revenue_growth (3.1%)."""
    df = tornado(V1, ALL_DRIVERS).set_index("driver")
    assert df.loc["opex_pct", "impact_range"] > df.loc["revenue_growth", "impact_range"]


def test_tornado_single_driver():
    df = tornado(V1, ("opex_pct",))
    assert len(df) == 1
    assert df.iloc[0]["driver"] == "opex_pct"


def test_sobol_indices_sum_reasonably_close_to_one():
    """For a near-linear model with independent uniform inputs, sum(S1) +
    (residual interaction) should be close to 1; loosely bound rather than
    tightly, since this is a Monte-Carlo-based estimate."""
    df = sobol_indices(V1, ALL_DRIVERS, base_n=256, seed=1)
    assert 0.5 <= df["S1"].sum() <= 1.3


def test_sobol_st_at_least_s1_within_noise():
    """Total-order should be >= first-order for each driver, up to Monte
    Carlo sampling noise (allow a small negative-noise tolerance rather
    than asserting the strict inequality, which can fail by float dust on
    a driver with near-zero true sensitivity)."""
    df = sobol_indices(V1, ALL_DRIVERS, base_n=256, seed=1)
    assert (df["ST"] >= df["S1"] - 0.05).all()


def test_sobol_dominant_driver_matches_tornado():
    """DIA's two methods (local tornado, global Sobol) should broadly
    agree on which driver dominates output uncertainty for this fixture."""
    tornado_top = tornado(V1, ALL_DRIVERS).iloc[0]["driver"]
    sobol_top = sobol_indices(V1, ALL_DRIVERS, base_n=256, seed=1).iloc[0]["driver"]
    assert tornado_top == sobol_top


def test_sobol_reveals_driver_shapley_never_saw():
    """DIA answers a different question than Shapley (Blueprint §C,
    challenge 2): cogs_pct never changed in the Phase-0 V1->V2 move, so
    Shapley assigns it nothing -- but DIA shows it materially drives
    output UNCERTAINTY. Confirm cogs_pct ranks materially above a
    near-zero-sensitivity driver like nwc_pct."""
    df = sobol_indices(V1, ALL_DRIVERS, base_n=256, seed=1).set_index("driver")
    assert df.loc["cogs_pct", "ST"] > df.loc["nwc_pct", "ST"]


def test_morris_screening_runs_and_ranks():
    df = morris_screening(V1, ALL_DRIVERS, trajectories=10, seed=1)
    assert len(df) == len(ALL_DRIVERS)
    assert list(df["mu_star"]) == sorted(df["mu_star"], reverse=True)


def test_morris_and_sobol_broadly_agree_on_top_driver():
    morris_top = morris_screening(V1, ALL_DRIVERS, trajectories=10, seed=1).iloc[0]["driver"]
    sobol_top = sobol_indices(V1, ALL_DRIVERS, base_n=256, seed=1).iloc[0]["driver"]
    assert morris_top == sobol_top
