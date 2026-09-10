"""
Sequential Variance Bridge + Shapley Attribution.

Sequential bridge: walks V1 -> V2 one driver at a time and records the
incremental FCF impact of each step. Kept strictly as a DIAGNOSTIC
(Blueprint §B, LOCKED) — never the headline output.

Shapley: for n changed drivers, phi_i is the average marginal contribution
of driver i across all n! permutations, equivalently the weighted sum over
all coalitions S not containing i:

    phi_i = sum_{S subseteq N minus i} w(|S|, n) * (f(S union {i}) - f(S))
    w(s, n) = s! * (n-s-1)! / n!

where f(S) = model output with drivers in S set to their V2 value and all
others held at V1. Exact enumeration for n_changed <= 8 (2^n coalitions);
Monte Carlo permutation sampling (Castro, Gomez & Tejada 2009) above that
(Blueprint §G, Decision 4).

Two invariants are asserted at run time for the sequential bridge:
    1. Sum of incremental impacts == V2 FCF - V1 FCF   (exact reconciliation)
    2. Starting output of step k == ending output of step k-1 (path continuity)

And for Shapley:
    3. Efficiency axiom: sum_i phi_i == V2 FCF - V1 FCF (exact for "exact"
       method at 1e-9 tolerance; approximate, with a reported CI, for "mc")
"""
from __future__ import annotations

import random
from collections.abc import Callable, Iterable, Sequence
from dataclasses import replace
from itertools import chain, combinations, permutations
from math import factorial

import pandas as pd

from .model import Drivers, compute_fcf

EXACT_SHAPLEY_MAX_DRIVERS = 8
SEQUENTIAL_FULL_ENUMERATION_MAX = 6
DEFAULT_MC_SAMPLES = 10_000
MC_CI_RELATIVE_THRESHOLD = 0.02  # 2% of |total variance|
MC_MAX_RETRIES = 3
RECONCILIATION_TOL = 1e-9


class ReconciliationError(AssertionError):
    """A mathematical invariant (bridge reconciliation, Shapley efficiency)
    failed. Subclasses AssertionError so existing callers catching that
    still work, but is raised explicitly so `python -O` cannot strip it."""


# --------------------------------------------------------------------- #
# Sequential bridge (diagnostic only)
# --------------------------------------------------------------------- #
def sequential_bridge(
    v1, v2, order: Sequence[str], model_fn: Callable[[object], float] = compute_fcf
) -> pd.DataFrame:
    """Sequential bridge for a single ordering. Returns a DataFrame with
    columns: step, driver, start_fcf, end_fcf, incremental_impact.

    model_fn defaults to compute_fcf so existing callers are unaffected;
    pass dcf.compute_share_price to attribute a valuation change instead.
    The columns keep their 'fcf' names for backwards compatibility — they
    hold whatever scalar model_fn returns."""
    columns = ["step", "driver", "start_fcf", "end_fcf", "incremental_impact"]
    rows: list[dict] = []
    current = v1
    for step, name in enumerate(order, start=1):
        start_fcf = model_fn(current)
        current = replace(current, **{name: getattr(v2, name)})
        end_fcf = model_fn(current)
        rows.append(
            {
                "step": step,
                "driver": name,
                "start_fcf": start_fcf,
                "end_fcf": end_fcf,
                "incremental_impact": end_fcf - start_fcf,
            }
        )
    # Explicit columns so the zero-changed-drivers edge case (Blueprint §M
    # edge case 1) still yields a well-formed, zero-row DataFrame rather
    # than one with no columns at all.
    df = pd.DataFrame(rows, columns=columns)

    # Explicit raises, not asserts: assertions are stripped under `python -O`,
    # which would silently disable the reconciliation invariant in exactly
    # the optimised runs a user is most likely to trust.
    total = model_fn(v2) - model_fn(v1)
    if abs(df["incremental_impact"].sum() - total) >= RECONCILIATION_TOL:
        raise ReconciliationError(
            f"Sequential bridge did not reconcile: "
            f"sum={df['incremental_impact'].sum()} vs target={total}"
        )
    for i in range(1, len(df)):
        if abs(df.loc[i, "start_fcf"] - df.loc[i - 1, "end_fcf"]) >= RECONCILIATION_TOL:
            raise ReconciliationError(f"Sequential bridge path discontinuity at step {i + 1}")

    return df


def all_orderings(
    v1, v2, changed: Iterable[str], seed: int = 42,
    model_fn: Callable[[object], float] = compute_fcf,
) -> pd.DataFrame:
    """Sequential bridge across orderings of the changed drivers.

    Exhaustive (n!) for n_changed <= SEQUENTIAL_FULL_ENUMERATION_MAX (6);
    otherwise a seeded random sample of 1000 orderings is used to build the
    diagnostic min-max whisker display (Blueprint §D) -- Shapley remains the
    number of record regardless of n.
    """
    changed = tuple(changed)
    n = len(changed)
    if n <= SEQUENTIAL_FULL_ENUMERATION_MAX:
        orderings: list[tuple[str, ...]] = list(permutations(changed))
    else:
        rng = random.Random(seed)
        orderings = []
        pool = list(changed)
        for _ in range(1000):
            rng.shuffle(pool)
            orderings.append(tuple(pool))

    frames = []
    for order in orderings:
        df = sequential_bridge(v1, v2, order, model_fn=model_fn)
        df = df.copy()
        df["ordering"] = " -> ".join(order)
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def ordering_impact_matrix(all_orderings_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot to a driver x ordering impact matrix. Rows: ordering,
    columns: driver, values: incremental impact; 'total' column appended."""
    pivot = all_orderings_df.pivot_table(
        index="ordering", columns="driver", values="incremental_impact", aggfunc="first"
    )
    pivot["total"] = pivot.sum(axis=1)
    return pivot


# --------------------------------------------------------------------- #
# Shapley — exact
# --------------------------------------------------------------------- #
def _powerset(iterable: Iterable[str]) -> Iterable[tuple[str, ...]]:
    items = list(iterable)
    return chain.from_iterable(combinations(items, r) for r in range(len(items) + 1))


def _apply_subset(v1: Drivers, v2: Drivers, subset: Sequence[str]) -> Drivers:
    updates = {name: getattr(v2, name) for name in subset}
    return replace(v1, **updates)


def coalition_values(
    v1, v2, changed: Sequence[str], model_fn: Callable[[object], float] = compute_fcf
) -> dict[tuple[str, ...], float]:
    """f(S) for every subset S of the changed drivers. f(empty)=V1 FCF,
    f(full)=V2 FCF."""
    values: dict[tuple[str, ...], float] = {}
    for subset in _powerset(changed):
        drivers = _apply_subset(v1, v2, subset)
        values[tuple(sorted(subset))] = model_fn(drivers)
    return values


def _shapley_exact(v1, v2, changed: Sequence[str], model_fn=compute_fcf) -> dict[str, float]:
    n = len(changed)
    values = coalition_values(v1, v2, changed, model_fn=model_fn)
    contributions: dict[str, float] = {name: 0.0 for name in changed}
    for i in changed:
        others = [d for d in changed if d != i]
        for subset in _powerset(others):
            s = len(subset)
            weight = factorial(s) * factorial(n - s - 1) / factorial(n)
            with_i = tuple(sorted(subset + (i,)))
            without_i = tuple(sorted(subset))
            marginal = values[with_i] - values[without_i]
            contributions[i] += weight * marginal
    return contributions


# --------------------------------------------------------------------- #
# Shapley — Monte Carlo (Castro, Gomez & Tejada, 2009)
# --------------------------------------------------------------------- #
def _shapley_mc_once(
    v1, v2, changed: Sequence[str], m: int, seed: int, model_fn=compute_fcf
) -> tuple[dict[str, float], dict[str, list[float]]]:
    """Run m permutation samples; return point estimates and the raw
    per-sample marginal contributions (for bootstrap CI)."""
    rng = random.Random(seed)
    samples: dict[str, list[float]] = {name: [] for name in changed}
    pool = list(changed)
    for _ in range(m):
        rng.shuffle(pool)
        current = v1
        prev_fcf = model_fn(current)
        for name in pool:
            current = replace(current, **{name: getattr(v2, name)})
            new_fcf = model_fn(current)
            samples[name].append(new_fcf - prev_fcf)
            prev_fcf = new_fcf
    estimates = {name: sum(vals) / m for name, vals in samples.items()}
    return estimates, samples


def _bootstrap_ci(samples: list[float], n_boot: int = 2000, seed: int = 42) -> tuple[float, float]:
    """Percentile bootstrap 95% CI on the mean of `samples`."""
    rng = random.Random(seed)
    n = len(samples)
    means = []
    for _ in range(n_boot):
        resample = [samples[rng.randrange(n)] for _ in range(n)]
        means.append(sum(resample) / n)
    means.sort()
    lo = means[int(0.025 * n_boot)]
    hi = means[int(0.975 * n_boot) - 1]
    return lo, hi


def _shapley_monte_carlo(
    v1,
    v2,
    changed: Sequence[str],
    seed: int,
    m0: int = DEFAULT_MC_SAMPLES,
    model_fn=compute_fcf,
) -> tuple[dict[str, float], dict[str, tuple[float, float]], int]:
    """Seeded MC Shapley with auto-retry: if the widest 95% CI half-width
    exceeds MC_CI_RELATIVE_THRESHOLD of |total variance|, double m up to
    MC_MAX_RETRIES times rather than silently reporting an under-converged
    estimate (Blueprint §G, Decision 4)."""
    total_variance = abs(model_fn(v2) - model_fn(v1))
    m = m0
    for attempt in range(MC_MAX_RETRIES + 1):
        estimates, samples = _shapley_mc_once(v1, v2, changed, m, seed, model_fn=model_fn)
        cis = {name: _bootstrap_ci(vals, seed=seed) for name, vals in samples.items()}
        max_half_width = max((hi - lo) / 2.0 for lo, hi in cis.values())
        threshold = MC_CI_RELATIVE_THRESHOLD * total_variance if total_variance > 0 else 1e-6
        if max_half_width <= threshold or attempt == MC_MAX_RETRIES:
            return estimates, cis, m
        m *= 2
    return estimates, cis, m  # pragma: no cover


# --------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------- #
def shapley_attribution(
    v1,
    v2,
    changed: Sequence[str],
    method: str = "auto",
    seed: int = 42,
    model_fn: Callable[[object], float] = compute_fcf,
) -> pd.DataFrame:
    """Shapley values for each driver.

    method: "exact" | "monte_carlo" | "auto" (exact if n<=8, else MC).
    Returns columns: driver, shapley_contribution, pct_of_variance,
    ci_low, ci_high, method, n_samples (ci/n_samples are NaN for exact).
    """
    changed = tuple(changed)
    n = len(changed)
    if method == "auto":
        method = "exact" if n <= EXACT_SHAPLEY_MAX_DRIVERS else "monte_carlo"

    total_variance = model_fn(v2) - model_fn(v1)

    if method == "exact":
        contributions = _shapley_exact(v1, v2, changed, model_fn=model_fn)
        cis = {name: (float("nan"), float("nan")) for name in changed}
        n_samples = None
    elif method == "monte_carlo":
        contributions, cis, n_samples = _shapley_monte_carlo(v1, v2, changed, seed=seed, model_fn=model_fn)
    else:
        raise ValueError(f"Unknown Shapley method: {method!r}")

    columns = ["driver", "shapley_contribution", "pct_of_variance", "ci_low", "ci_high", "method", "n_samples"]
    rows = []
    for name in changed:
        pct = 100.0 * contributions[name] / total_variance if total_variance != 0 else 0.0
        lo, hi = cis[name]
        rows.append(
            {
                "driver": name,
                "shapley_contribution": contributions[name],
                "pct_of_variance": pct,
                "ci_low": lo,
                "ci_high": hi,
                "method": method,
                "n_samples": n_samples,
            }
        )
    df = pd.DataFrame(rows, columns=columns)

    if method == "exact" and abs(df["shapley_contribution"].sum() - total_variance) >= RECONCILIATION_TOL:
        raise ReconciliationError(
            f"Shapley efficiency violated: {df['shapley_contribution'].sum()} vs {total_variance}"
        )
    return df


def interaction_size(v1, v2, changed: Sequence[str], model_fn=compute_fcf) -> float:
    """Net non-additivity: actual variance minus the sum of isolated
    (one-at-a-time) impacts (Blueprint §D correction A — this is the
    correctly-named quantity; it is NOT 'the interaction', which cancels)."""
    v1_fcf = model_fn(v1)
    isolated = 0.0
    for name in changed:
        d = replace(v1, **{name: getattr(v2, name)})
        isolated += model_fn(d) - v1_fcf
    total = model_fn(v2) - v1_fcf
    return total - isolated


__all__ = [
    "DEFAULT_MC_SAMPLES",
    "EXACT_SHAPLEY_MAX_DRIVERS",
    "SEQUENTIAL_FULL_ENUMERATION_MAX",
    "ReconciliationError",
    "all_orderings",
    "coalition_values",
    "interaction_size",
    "ordering_impact_matrix",
    "sequential_bridge",
    "shapley_attribution",
]
