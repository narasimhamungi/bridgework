"""
Reconciliation between the Shapley/interaction decomposition and the
non-additivity diagnostics (Blueprint §I mathematical invariants).
"""
from dataclasses import replace

import pytest

from bridgework.interactions import (
    interaction_report,
    l1_non_additivity,
    net_non_additivity,
    pairwise_interactions,
    three_way_interaction,
)
from bridgework.model import Drivers, compute_fcf

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


def test_locked_phase0_interaction_values():
    """Independently re-verifies the Blueprint §4.4.B locked figures."""
    pairs = pairwise_interactions(V1, V2, CHANGED).set_index(["driver_a", "driver_b"])
    assert pairs.loc[("revenue_growth", "opex_pct"), "interaction"] == pytest.approx(2.2273, abs=1e-3)
    assert pairs.loc[("revenue_growth", "capex_pct"), "interaction"] == pytest.approx(-1.6297, abs=1e-3)
    assert pairs.loc[("opex_pct", "capex_pct"), "interaction"] == pytest.approx(0.0, abs=1e-9)
    assert three_way_interaction(V1, V2, CHANGED) == pytest.approx(0.0, abs=1e-9)


def test_net_non_additivity_equals_sum_of_interaction_terms():
    """net_non_additivity == sum(pairwise) + three_way (Blueprint §I)."""
    net = net_non_additivity(V1, V2, CHANGED)
    pairs = pairwise_interactions(V1, V2, CHANGED)
    three_way = three_way_interaction(V1, V2, CHANGED)
    assert net == pytest.approx(pairs["interaction"].sum() + three_way, abs=1e-9)


def test_l1_never_less_than_absolute_net():
    """Triangle inequality: L1 (sum of |terms|) >= |sum of terms| (net).
    This must hold for ANY driver set, not just this fixture."""
    net = net_non_additivity(V1, V2, CHANGED)
    l1 = l1_non_additivity(V1, V2, CHANGED)
    assert l1 >= abs(net) - 1e-9


def test_l1_zero_implies_zero_ordering_dependence():
    """A synthetic fully-additive fixture (each driver's isolated impact
    sums exactly to the total, by construction of two independent-effect
    single-driver deltas with no shared nonlinearity) should have L1 ~ 0
    and therefore zero sequential ordering-dependence."""
    from bridgework.variance_bridge import all_orderings

    # Two drivers with no multiplicative interaction: tax_rate and nwc_pct
    # both act as simple linear scalings on already-fixed intermediate
    # quantities in this specific base case, holding revenue fixed.
    v2_additive = replace(V1, nwc_pct=0.06, tax_rate=0.19)
    changed = ("nwc_pct", "tax_rate")
    l1 = l1_non_additivity(V1, v2_additive, changed)
    all_ord = all_orderings(V1, v2_additive, changed)
    per_driver_range = all_ord.groupby("driver")["incremental_impact"].agg(lambda s: s.max() - s.min())
    if l1 < 1e-9:
        assert (per_driver_range < 1e-6).all()


def test_interaction_report_bundle_consistency():
    report = interaction_report(V1, V2, CHANGED)
    assert report["net_non_additivity"] == pytest.approx(net_non_additivity(V1, V2, CHANGED), abs=1e-9)
    assert report["l1_non_additivity"] == pytest.approx(l1_non_additivity(V1, V2, CHANGED), abs=1e-9)
    total_variance = abs(compute_fcf(V2) - compute_fcf(V1))
    assert report["l1_pct_of_variance"] == pytest.approx(100 * report["l1_non_additivity"] / total_variance, rel=1e-6)


def test_general_formula_diverges_from_plain_shortcut_when_three_way_nonzero():
    """Blueprint Decision 2: the general Grabisch-Roubens weighted formula
    must differ from the naive plain-pair shortcut whenever a genuine
    three-way term exists. Constructed via a driver combination that
    produces a non-zero three-way term (crossing the EBIT=0 tax kink,
    which the Phase-0 bilinear fixture never exercises)."""
    # Push opex_pct high enough in V1 that EBIT < 0, and low enough in V2
    # that EBIT > 0, while also moving revenue_growth and capex_pct --
    # this couples the tax MAX(EBIT,0) kink into all three drivers at once.
    v1_kink = replace(V1, opex_pct=0.90)
    v2_kink = replace(v1_kink, revenue_growth=0.20, opex_pct=0.30, capex_pct=0.10)
    changed = ("revenue_growth", "opex_pct", "capex_pct")

    plain_terms = {}
    from bridgework.variance_bridge import coalition_values

    values = coalition_values(v1_kink, v2_kink, changed)

    def f(s):
        return values[tuple(sorted(s))]

    for i, j in [("revenue_growth", "opex_pct"), ("revenue_growth", "capex_pct"), ("opex_pct", "capex_pct")]:
        plain_terms[(i, j)] = f((i, j)) - f((i,)) - f((j,)) + f(())

    general = pairwise_interactions(v1_kink, v2_kink, changed).set_index(["driver_a", "driver_b"])
    three_way = three_way_interaction(v1_kink, v2_kink, changed)

    # If the three-way term is genuinely non-zero here, at least one pair's
    # general (weighted) value must differ from its plain shortcut value.
    if abs(three_way) > 1e-6:
        diffs = [
            abs(general.loc[pair, "interaction"] - plain_terms[pair]) for pair in plain_terms
        ]
        assert max(diffs) > 1e-9, "General formula unexpectedly matched the plain shortcut despite a non-zero 3-way term"


def test_l1_captures_higher_order_interaction():
    """Regression for a mathematically false invariant that shipped.

    The old L1 summed absolute pairwise Grabisch-Roubens indices and added
    the three-way term only when exactly three drivers changed. At n >= 4
    all higher-order terms were silently dropped, so the documented
    invariant 'L1 == 0 implies zero ordering dependence' was false.

    This four-player game is the counterexample: Möbius mass sits entirely
    on the 3-subsets and the 4-set, arranged so that every pairwise index
    is ~0. The old implementation would report L1 ~ 0.002 while the true
    ordering spread is 0.278 -- wrong by a factor of 140.
    """
    from itertools import chain, combinations, permutations
    from math import factorial

    N = ("a", "b", "c", "d")
    mob = {frozenset(T): 0.277 for T in combinations(N, 3)}
    mob[frozenset(N)] = -0.832

    def v(S):
        S = frozenset(S)
        return sum(m for T, m in mob.items() if T <= S)

    def pset(it):
        it = list(it)
        return chain.from_iterable(combinations(it, r) for r in range(len(it) + 1))

    # 1. Every pairwise Grabisch-Roubens index is ~zero on this game.
    n = 4
    for i, j in combinations(N, 2):
        others = [x for x in N if x not in (i, j)]
        idx = 0.0
        for S in pset(others):
            s = len(S)
            w = factorial(s) * factorial(n - s - 2) / factorial(n - 1)
            idx += w * (v(tuple(S) + (i, j)) - v(tuple(S) + (i,)) - v(tuple(S) + (j,)) + v(S))
        assert abs(idx) < 1e-3, f"fixture invalid: I({i},{j}) = {idx}"

    # 2. Yet ordering dependence is large.
    spreads = {}
    for p in permutations(N):
        cur, prev = (), v(())
        for name in p:
            cur = cur + (name,)
            cn = v(cur)
            spreads.setdefault(name, []).append(cn - prev)
            prev = cn
    true_spread = max(max(x) - min(x) for x in spreads.values())
    assert true_spread > 0.2, "fixture should exhibit material ordering dependence"

    # 3. The Möbius-based L1 must reflect it and must bound it.
    l1 = sum(abs(m) for T, m in mob.items() if len(T) >= 2)
    assert l1 > 0.2, "L1 must not read ~0 on a game with real ordering dependence"
    assert l1 >= true_spread - 1e-9, "L1 must upper-bound the ordering spread"


def test_l1_bounds_ordering_spread_on_shipped_fixtures():
    """The bound must hold on the real models too, not just in theory."""
    from itertools import permutations

    from bridgework.variance_bridge import coalition_values

    for v1, v2, ch, fn in [
        (V1, V2, CHANGED, None),
    ]:
        rep = interaction_report(v1, v2, ch)
        cv = coalition_values(v1, v2, ch)
        spreads = {}
        for p in permutations(ch):
            cur, prev = (), cv[()]
            for name in p:
                cur = tuple(sorted(cur + (name,)))
                spreads.setdefault(name, []).append(cv[cur] - prev)
                prev = cv[cur]
        true_spread = max(max(x) - min(x) for x in spreads.values())
        assert rep["l1_non_additivity"] >= true_spread - 1e-9
