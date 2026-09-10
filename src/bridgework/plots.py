"""
Visualisation — Blueprint §J. IBCS / ISO 24896:2026-aligned: signed values,
single unit of measure, no truncated axes, no 3D/pie/decorative gradients,
matplotlib Agg backend only (headless-safe, reproducible).
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_POS = "#1D6B45"   # ledger green — matches html_report --positive
_NEG = "#9B2C2C"   # oxblood — matches html_report --negative
_NEUTRAL = "#2C5F7C"  # audit blue — matches html_report --verified


def plot_waterfall(
    bridge_df: pd.DataFrame, v1_fcf: float, v2_fcf: float, out_path: Path, title: str
) -> None:
    """V1 -> drivers -> V2 waterfall (diagnostic ordering view)."""
    labels = ["V1 FCF"] + list(bridge_df["driver"]) + ["V2 FCF"]
    impacts = [v1_fcf] + list(bridge_df["incremental_impact"]) + [v2_fcf]
    running = v1_fcf
    positions = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(10, 6))
    for i, (lab, val) in enumerate(zip(labels, impacts)):
        if i in (0, len(labels) - 1):
            ax.bar(i, val, color=_NEUTRAL)
            ax.text(i, val, f"${val:,.0f}M", ha="center", va="bottom", fontsize=9)
        else:
            color = _POS if val >= 0 else _NEG
            ax.bar(i, val, bottom=running, color=color)
            ax.text(i, running + val, f"{'+' if val >= 0 else ''}{val:,.1f}", ha="center", va="bottom", fontsize=9)
            running += val
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("Free Cash Flow ($M)")
    ax.set_title(title)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_shapley_with_whisker(
    shap_df: pd.DataFrame,
    ordering_matrix: pd.DataFrame,
    total_variance: float,
    l1_non_additivity: float,
    out_path: Path,
) -> None:
    """PRIMARY headline chart (Blueprint §J visualisation contract):
    Shapley bars as the primary series, with the sequential min-max range
    overlaid as a whisker per driver, and non-additivity annotated as
    visible text (never hidden in a tooltip)."""
    drivers = list(shap_df["driver"])
    values = list(shap_df["shapley_contribution"])
    colors = [_POS if v >= 0 else _NEG for v in values]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    y = np.arange(len(drivers))
    ax.barh(y, values, color=colors, zorder=2)

    driver_cols = [c for c in ordering_matrix.columns if c != "total"]
    for i, drv in enumerate(drivers):
        if drv in driver_cols:
            lo, hi = ordering_matrix[drv].min(), ordering_matrix[drv].max()
            ax.plot([lo, hi], [i, i], color="black", linewidth=1.5, zorder=3)
            ax.plot([lo, lo], [i - 0.12, i + 0.12], color="black", linewidth=1.5, zorder=3)
            ax.plot([hi, hi], [i - 0.12, i + 0.12], color="black", linewidth=1.5, zorder=3)

    for i, v in enumerate(values):
        ax.text(v, i, f" {v:+,.1f}", va="center", fontsize=10, zorder=4)

    ax.set_yticks(y)
    ax.set_yticklabels(drivers)
    ax.axvline(0, color="black", linewidth=0.7)
    l1_pct = (100 * l1_non_additivity / abs(total_variance)) if total_variance != 0 else 0.0
    ax.set_xlabel("Shapley contribution ($M FCF) — whisker = sequential min-max range")
    ax.set_title(
        f"Variance Bridge — Shapley Attribution (primary) — Total variance = ${total_variance:+,.1f}M\n"
        f"L1 non-additivity = ${l1_non_additivity:,.2f}M ({l1_pct:.1f}% of |total variance|)"
    )
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_ordering_sensitivity(matrix: pd.DataFrame, out_path: Path) -> None:
    """Diagnostic only, never the headline (Blueprint §J)."""
    driver_cols = [c for c in matrix.columns if c != "total"]
    x = np.arange(len(matrix.index))
    width = 0.8 / max(len(driver_cols), 1)
    fig, ax = plt.subplots(figsize=(11, 6))
    for i, drv in enumerate(driver_cols):
        ax.bar(x + i * width, matrix[drv], width, label=drv)
    ax.set_xticks(x + width * (len(driver_cols) - 1) / 2)
    ax.set_xticklabels(matrix.index, rotation=20, ha="right", fontsize=8)
    ax.set_ylabel("Sequential incremental impact ($M FCF)")
    ax.set_title("Sequential Attribution Depends on Ordering (diagnostic)")
    ax.axhline(0, color="black", linewidth=0.6)
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    if driver_cols:
        ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_interactions(pairwise_df: pd.DataFrame, out_path: Path) -> None:
    """Pairwise interaction terms — supports the L1 non-additivity claim
    with the underlying, individually-signed pairs."""
    labels = [f"{r.driver_a} x {r.driver_b}" for r in pairwise_df.itertuples()]
    values = list(pairwise_df["interaction"])
    colors = [_POS if v >= 0 else _NEG for v in values]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    y = np.arange(len(labels))
    ax.barh(y, values, color=colors)
    for i, v in enumerate(values):
        ax.text(v, i, f" {v:+,.2f}", va="center", fontsize=9)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.axvline(0, color="black", linewidth=0.7)
    ax.set_xlabel("Pairwise interaction ($M FCF)")
    ax.set_title("Pairwise Interaction Terms (Grabisch-Roubens)")
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_sobol(sobol_df: pd.DataFrame, out_path: Path) -> None:
    """Sobol first-order (S1) vs total-order (ST) bars per driver, side by
    side, so the interaction gap (ST - S1) is visually apparent (Blueprint
    §J visualisation contract)."""
    drivers = list(sobol_df["driver"])
    x = np.arange(len(drivers))
    width = 0.35
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.bar(x - width / 2, sobol_df["S1"], width, yerr=sobol_df["S1_conf"], label="S1 (first-order)", color=_NEUTRAL, capsize=3)
    ax.bar(x + width / 2, sobol_df["ST"], width, yerr=sobol_df["ST_conf"], label="ST (total-order)", color="#7CA7CC", capsize=3)
    ax.set_xticks(x)
    ax.set_xticklabels(drivers, rotation=20, ha="right")
    ax.set_ylabel("Sobol index (fraction of output variance)")
    ax.set_title("Driver Impact Analysis — Sobol Sensitivity (interaction gap = ST − S1)")
    ax.grid(axis="y", linestyle=":", alpha=0.5)
    ax.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    plt.close(fig)


def plot_tornado(tornado_df: pd.DataFrame, out_path: Path) -> None:
    """Local one-way sensitivity, ranked by impact range."""
    df = tornado_df.iloc[::-1]  # largest at top when plotted horizontally
    y = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for i, row in enumerate(df.itertuples()):
        ax.plot([row.fcf_low, row.fcf_high], [i, i], color=_NEUTRAL, linewidth=6, solid_capstyle="butt")
    ax.axvline(tornado_df.iloc[0]["fcf_base"], color="black", linewidth=1, linestyle="--", label="Base FCF")
    ax.set_yticks(y)
    ax.set_yticklabels(df["driver"])
    ax.set_xlabel("Free Cash Flow ($M)")
    ax.set_title("Driver Impact Analysis — Tornado (±20% one-way perturbation)")
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    ax.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    plt.close(fig)


__all__ = [
    "plot_interactions",
    "plot_ordering_sensitivity",
    "plot_shapley_with_whisker",
    "plot_sobol",
    "plot_tornado",
    "plot_waterfall",
]
