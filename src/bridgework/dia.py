"""
Driver Impact Analysis (DIA) — Blueprint §D, §G, Phase 2.

Answers a DIFFERENT analyst question from Shapley (Blueprint §C, challenge
2): Shapley attributes a specific, realized V1->V2 change (retrospective/
forensic -- "what already happened"). DIA/Sobol attributes output variance
under an ASSUMED input distribution around a base case (prospective/risk-
scoping -- "what should I worry about going forward, even if it hasn't
moved yet"). Both survive in this codebase because they answer materially
different, both decision-relevant, questions.

Two methods:
  - Tornado (local, one-way): perturb each driver +-x% around a base case,
    holding all others fixed, rank by |delta FCF|. Cheap, always available.
  - Sobol (global, variance-based): first-order S1 (variance explained by
    driver i alone) and total-order ST (variance explained by driver i
    including all its interactions), via SALib (Herman & Usher, 2017;
    Iwanaga, Usher & Herman, 2022), implementing Sobol (2001) /
    Saltelli et al. (2010).

Input-distribution policy (Assumption #1, Blueprint §D, flagged in
docs/limitations.md as not yet evidence-calibrated): independent uniform
+-20% around each driver's base value. This is a documented, overridable
default, not a claim that +-20% is the "correct" uncertainty for every
driver in every model.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

import numpy as np
import pandas as pd
from SALib.analyze import morris as morris_analyze_mod
from SALib.analyze import sobol as sobol_analyze_mod
from SALib.sample import sobol as sobol_sample_mod
from SALib.sample.morris import sample as morris_sample_mod

from .model import compute_fcf

DEFAULT_PERTURBATION = 0.20  # +-20% (Assumption #1)
DEFAULT_SOBOL_BASE_N = 512  # base sample size -> N = n*(2k+2) total evaluations
DEFAULT_MORRIS_TRAJECTORIES = 20


# --------------------------------------------------------------------- #
# Tornado (local, one-way)
# --------------------------------------------------------------------- #
def tornado(base, drivers: Sequence[str], pct: float = DEFAULT_PERTURBATION, model_fn=compute_fcf) -> pd.DataFrame:
    """One-way +-pct perturbation per driver around `base`, holding all
    others fixed. Returns columns: driver, low_value, high_value,
    fcf_low, fcf_high, fcf_base, impact_range (ranked descending)."""
    base_fcf = model_fn(base)
    rows = []
    for name in drivers:
        v = getattr(base, name)
        low_v, high_v = v * (1 - pct), v * (1 + pct)
        fcf_low = model_fn(replace(base, **{name: low_v}))
        fcf_high = model_fn(replace(base, **{name: high_v}))
        rows.append(
            {
                "driver": name,
                "low_value": low_v,
                "high_value": high_v,
                "fcf_low": fcf_low,
                "fcf_high": fcf_high,
                "fcf_base": base_fcf,
                "impact_range": abs(fcf_high - fcf_low),
            }
        )
    df = pd.DataFrame(rows).sort_values("impact_range", ascending=False).reset_index(drop=True)
    return df


# --------------------------------------------------------------------- #
# Sobol (global, variance-based)
# --------------------------------------------------------------------- #
def _salib_problem(base, drivers: Sequence[str], pct: float) -> dict[str, object]:
    bounds = []
    for name in drivers:
        v = getattr(base, name)
        lo, hi = v * (1 - pct), v * (1 + pct)
        if lo > hi:
            lo, hi = hi, lo
        bounds.append([lo, hi])
    return {"num_vars": len(drivers), "names": list(drivers), "bounds": bounds}


def sobol_indices(
    base,
    drivers: Sequence[str],
    pct: float = DEFAULT_PERTURBATION,
    base_n: int = DEFAULT_SOBOL_BASE_N,
    seed: int = 42,
    model_fn=compute_fcf,
) -> pd.DataFrame:
    """First-order (S1) and total-order (ST) Sobol indices via SALib's
    Saltelli sampler, N = base_n*(2k+2) total model evaluations.

    Returns columns: driver, S1, S1_conf, ST, ST_conf, interaction_gap
    (= ST - S1; a large gap flags interaction-concentrated risk that
    Shapley alone, on the realized V1->V2 change, would not surface --
    Blueprint §C, §H)."""
    problem = _salib_problem(base, drivers, pct)
    param_values = sobol_sample_mod.sample(problem, base_n, calc_second_order=False, seed=seed)

    Y = np.array(
        [model_fn(replace(base, **dict(zip(drivers, row, strict=False)))) for row in param_values]
    )
    Si = sobol_analyze_mod.analyze(problem, Y, calc_second_order=False, seed=seed, print_to_console=False)

    rows = []
    for i, name in enumerate(drivers):
        rows.append(
            {
                "driver": name,
                "S1": Si["S1"][i],
                "S1_conf": Si["S1_conf"][i],
                "ST": Si["ST"][i],
                "ST_conf": Si["ST_conf"][i],
                "interaction_gap": Si["ST"][i] - Si["S1"][i],
            }
        )
    df = pd.DataFrame(rows).sort_values("ST", ascending=False).reset_index(drop=True)
    return df


def morris_screening(
    base,
    drivers: Sequence[str],
    pct: float = DEFAULT_PERTURBATION,
    trajectories: int = DEFAULT_MORRIS_TRAJECTORIES,
    seed: int = 42,
    model_fn=compute_fcf,
) -> pd.DataFrame:
    """Cheap Morris elementary-effects screen -- O(r(k+1)) evaluations vs
    Sobol's O(N(2k+2)); useful as a pre-screen before a full Sobol run on
    a larger driver set. Returns mu_star (mean absolute elementary
    effect, overall importance) and sigma (effect std dev, a nonlinearity/
    interaction signal)."""
    problem = _salib_problem(base, drivers, pct)
    param_values = morris_sample_mod(problem, trajectories, seed=seed)
    Y = np.array(
        [model_fn(replace(base, **dict(zip(drivers, row, strict=False)))) for row in param_values]
    )
    Si = morris_analyze_mod.analyze(problem, param_values, Y, seed=seed, print_to_console=False)
    rows = [
        {"driver": name, "mu_star": Si["mu_star"][i], "sigma": Si["sigma"][i]}
        for i, name in enumerate(drivers)
    ]
    return pd.DataFrame(rows).sort_values("mu_star", ascending=False).reset_index(drop=True)


__all__ = [
    "DEFAULT_MORRIS_TRAJECTORIES",
    "DEFAULT_PERTURBATION",
    "DEFAULT_SOBOL_BASE_N",
    "morris_screening",
    "sobol_indices",
    "tornado",
]
