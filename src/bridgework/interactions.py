"""
Interaction diagnostics: pairwise interaction indices, net non-additivity,
L1 non-additivity (Blueprint §D).

Implements the GENERAL Grabisch & Roubens (1999) weighted pairwise Shapley
interaction index unconditionally -- never the plain-pair shortcut
I(i,j) = f({i,j}) - f({i}) - f({j}) + f(emptyset) directly. Blueprint
Decision 2 (LOCKED): those two formulas coincide only when the model's
three-way (and higher) term is exactly zero, which is a property of the
Phase-0 Zoom fixture, not a general property. Implementing the general
formula keeps this module correct beyond that fixture.

For a pair {i, j} in an n-player game, the weighted formula averages the
plain term over every subset S of the OTHER n-2 players:

    I(i,j) = sum_{S subseteq N \\ {i,j}} w(|S|, n) *
                 ( f(S+{i,j}) - f(S+{i}) - f(S+{j}) + f(S) )
    w(s, n) = s! * (n-s-2)! / (n-1)!

When n=2 this has exactly one term (S=empty) with weight 1, reducing to the
plain formula -- consistent with, not contradicting, the shortcut.
"""
from __future__ import annotations

from collections.abc import Sequence
from itertools import chain, combinations
from math import factorial

import pandas as pd

from .model import compute_fcf
from .variance_bridge import coalition_values, interaction_size


def _powerset(iterable) -> list:
    items = list(iterable)
    return list(chain.from_iterable(combinations(items, r) for r in range(len(items) + 1)))


def pairwise_interactions(v1, v2, changed: Sequence[str], model_fn=compute_fcf) -> pd.DataFrame:
    """General Grabisch-Roubens pairwise Shapley interaction index for
    every pair of changed drivers. Returns columns: driver_a, driver_b,
    interaction."""
    changed = tuple(changed)
    n = len(changed)
    values = coalition_values(v1, v2, changed, model_fn=model_fn)

    def f(subset: tuple[str, ...]) -> float:
        return values[tuple(sorted(subset))]

    rows = []
    for i, j in combinations(changed, 2):
        others = [d for d in changed if d not in (i, j)]
        total = 0.0
        for subset in _powerset(others):
            s = len(subset)
            weight = factorial(s) * factorial(n - s - 2) / factorial(n - 1)
            term = (
                f(subset + (i, j))
                - f(subset + (i,))
                - f(subset + (j,))
                + f(subset)
            )
            total += weight * term
        rows.append({"driver_a": i, "driver_b": j, "interaction": total})
    return pd.DataFrame(rows, columns=["driver_a", "driver_b", "interaction"])


def three_way_interaction(v1, v2, changed: Sequence[str], model_fn=compute_fcf) -> float:
    """For exactly 3 changed drivers, the (only) three-way interaction
    term. Generalizes as the Mobius/inclusion-exclusion term over the full
    set; only meaningful to report when n_changed == 3."""
    if len(changed) != 3:
        raise ValueError("three_way_interaction is defined for exactly 3 changed drivers")
    values = coalition_values(v1, v2, changed, model_fn=model_fn)
    a, b, c = changed

    def f(subset) -> float:
        return values[tuple(sorted(subset))]

    return (
        f((a, b, c))
        - f((a, b))
        - f((a, c))
        - f((b, c))
        + f((a,))
        + f((b,))
        + f((c,))
        - f(())
    )


def net_non_additivity(v1, v2, changed: Sequence[str], model_fn=compute_fcf) -> float:
    """Actual variance minus the sum of isolated one-at-a-time impacts.
    Can partially cancel across pairs -- this is the imprecise "interaction
    effect" figure from Phase 0, correctly named per Blueprint §4.4.A."""
    return interaction_size(v1, v2, changed, model_fn=model_fn)


def mobius_terms(v1, v2, changed: Sequence[str], model_fn=compute_fcf) -> dict[tuple, float]:
    """Möbius (Harsanyi dividend) coefficients for every subset:

        m(T) = sum_{S subseteq T} (-1)^(|T|-|S|) f(S)

    These are the natural basis for non-additivity: a player's marginal
    contribution in any ordering is the sum of m(T) over the subsets T
    containing that player whose other members already precede it. That is
    why the sum of |m(T)| over |T| >= 2 bounds the ordering spread, and
    why an aggregate built from pairwise indices alone does not."""
    changed = tuple(changed)
    values = coalition_values(v1, v2, changed, model_fn=model_fn)

    def f(subset) -> float:
        return values[tuple(sorted(subset))]

    terms: dict[tuple, float] = {}
    for r in range(len(changed) + 1):
        for T in combinations(changed, r):
            total = 0.0
            for r2 in range(len(T) + 1):
                for S in combinations(T, r2):
                    total += ((-1) ** (len(T) - len(S))) * f(S)
            terms[T] = total
    return terms


def l1_non_additivity(v1, v2, changed: Sequence[str], model_fn=compute_fcf) -> float:
    """Sum of absolute interaction terms across EVERY order, via the Möbius
    coefficients: L1 = sum over |T| >= 2 of |m(T)|.

    This is an upper bound on the maximum sequential ordering spread, and
    L1 == 0 if and only if the model is additive over the changed drivers
    (in which case every ordering yields identical results).

    Implementation note. An earlier version summed the absolute pairwise
    Grabisch-Roubens indices and added the three-way term only when exactly
    three drivers changed. That silently discarded all higher-order terms
    at n >= 4, and the resulting invariant was false: a four-driver game
    exists whose six pairwise indices are all ~0 (so the old L1 read ~0)
    while every player's sequential marginal still swings by 0.278. The
    Möbius formulation has no such hole. See
    tests/test_shapley_axioms.py::test_l1_captures_higher_order_interaction.
    """
    terms = mobius_terms(v1, v2, changed, model_fn=model_fn)
    return sum(abs(x) for T, x in terms.items() if len(T) >= 2)


def interaction_report(v1, v2, changed: Sequence[str], model_fn=compute_fcf) -> dict[str, object]:
    """Full interaction diagnostic bundle for the reporting layer."""
    pairs = pairwise_interactions(v1, v2, changed, model_fn=model_fn)
    net = net_non_additivity(v1, v2, changed, model_fn=model_fn)
    terms = mobius_terms(v1, v2, changed, model_fn=model_fn)
    l1 = sum(abs(x) for T, x in terms.items() if len(T) >= 2)
    total_variance = abs(model_fn(v2) - model_fn(v1))
    return {
        "pairwise": pairs,
        "mobius": {T: x for T, x in terms.items() if len(T) >= 2},
        "three_way": three_way_interaction(v1, v2, changed, model_fn=model_fn) if len(changed) == 3 else None,
        "net_non_additivity": net,
        "l1_non_additivity": l1,
        "l1_pct_of_variance": (100.0 * l1 / total_variance) if total_variance else 0.0,
    }


__all__ = [
    "interaction_report",
    "l1_non_additivity",
    "mobius_terms",
    "net_non_additivity",
    "pairwise_interactions",
    "three_way_interaction",
]
