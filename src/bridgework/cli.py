"""
Single CLI entry point (Blueprint §E): `bridgework compare v1.yaml v2.yaml`

Pipeline: ingest -> generate Excel byproduct -> SIA gate (fail-fast) ->
sequential bridge (diagnostic) -> Shapley (primary) -> interactions ->
[optional: DIA, TBA] -> audit manifest -> write CSVs + plots + report.

Phase-2 stages (--dia, --tba, or --full) are opt-in: they answer a
different question from the variance bridge (Blueprint §C) and keeping
them off by default leaves the Phase-1 golden dataset byte-identical.

No I/O, no wall-clock, no network in the calculation path itself (model.py,
variance_bridge.py, interactions.py, dia.py, tba.py remain pure) -- I/O
lives only here and in ingestion.py/report.py/plots.py/audit.py, which is
the intended boundary (Blueprint §E).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from . import ingestion
from .derive import derive_drivers, load_line_items, write_driver_file, write_template
from .dia import sobol_indices, tornado
from .html_report import build_html_report
from .interactions import interaction_report
from .model_spec import diff_changed, get_model
from .plots import (
    plot_interactions,
    plot_ordering_sensitivity,
    plot_shapley_with_whisker,
    plot_sobol,
    plot_tornado,
    plot_waterfall,
)
from .report import (
    PipelineResult,
    build_report_markdown,
    change_register,
    executive_summary,
    model_snapshot,
    sequential_vs_shapley,
)
from .sia import run_structural_checks
from .tba import DEFAULT_SEARCH_RANGES, find_threshold
from .variance_bridge import all_orderings, ordering_impact_matrix, sequential_bridge, shapley_attribution


class PipelineHaltedError(Exception):
    """Raised when SIA fails and the pipeline halts before attribution
    runs (fail-fast, Blueprint §D SIA gate)."""


def _resolve_model(model_arg: str | None, v1_path: str):
    """Resolve which model to run. Precedence: an explicit --model flag
    wins; otherwise the driver file declares it (YAML 'model:' key or
    Meta!B3 in a workbook); otherwise the FCF default."""
    if model_arg is not None:
        return get_model(model_arg)

    suffix = Path(v1_path).suffix.lower()
    key = None
    if suffix in (".yaml", ".yml"):
        import yaml as _yaml
        with open(v1_path) as fh:
            key = (_yaml.safe_load(fh) or {}).get("model")
    elif suffix == ".xlsx":
        from openpyxl import load_workbook
        wb = load_workbook(v1_path, data_only=False)
        if "Meta" in wb.sheetnames:
            key = wb["Meta"]["B3"].value
    return get_model(str(key)) if key else get_model(None)


def _load_drivers(path: str, spec=None):
    """Dispatch on extension: .yaml/.yml -> canonical input; .xlsx ->
    constrained round-trip ingestion (Decision 3). Any other extension is
    a schema violation, not a silent guess."""
    suffix = Path(path).suffix.lower()
    if suffix in (".yaml", ".yml"):
        return ingestion.load_from_yaml(path, spec=spec)
    if suffix == ".xlsx":
        return ingestion.load_from_excel(path, spec=spec)
    raise ingestion.BridgeworkSchemaError(
        [f"unsupported input extension {suffix!r} for {path!r} — expected .yaml/.yml or .xlsx"]
    )


def run_pipeline(
    v1_path: str,
    v2_path: str,
    output_dir: str = "outputs",
    models_dir: str = "models",
    method: str = "auto",
    seed: int = 42,
    run_dia: bool = False,
    run_tba: bool = False,
    model: str | None = None,
) -> PipelineResult:
    """Phase 1 pipeline (SIA -> sequential -> Shapley -> interactions) plus
    optional Phase-2 stages. DIA/TBA default OFF: they answer a different,
    additional question (Blueprint §C) and are compute-heavier (DIA) or
    require a documented default search range (TBA, Assumption #3) --
    opt-in keeps the Phase-1 golden dataset byte-identical regardless."""
    outputs = Path(output_dir)
    models = Path(models_dir)
    outputs.mkdir(parents=True, exist_ok=True)
    models.mkdir(parents=True, exist_ok=True)

    # 1) Ingest — YAML (canonical input) or a Bridgework-generated
    # workbook a user has edited (constrained round-trip, Decision 3).
    spec = _resolve_model(model, v1_path)
    v1 = _load_drivers(v1_path, spec=spec)
    v2 = _load_drivers(v2_path, spec=spec)
    changed = diff_changed(v1, v2, spec)
    model_fn = spec.compute

    # Pre-flight: Shapley evaluates coalitions, i.e. MIXTURES of V1 and V2.
    # A mixture can be invalid when both endpoints are fine. Check that here
    # so the user gets a clear message before any workbook is written,
    # rather than a mid-pipeline exception (adversarial review finding).
    if {"wacc", "terminal_growth"} <= set(spec.roles):
        min_wacc = min(v1.wacc, v2.wacc)
        max_g = max(v1.terminal_growth, v2.terminal_growth)
        if min_wacc <= max_g:
            raise PipelineHaltedError(
                "Cannot attribute: the two versions are individually valid but some "
                "Shapley coalitions are not.\n"
                f"  min(WACC) across versions      = {min_wacc:.4f}\n"
                f"  max(terminal growth) across    = {max_g:.4f}\n"
                "Attribution evaluates every mixture of V1 and V2 driver values, so a "
                "coalition here would pair a discount rate at or below its perpetuity "
                "growth rate, making the terminal value undefined.\n"
                "Required precondition: min(WACC) > max(terminal growth) across both versions."
            )

    # 2) Generate Excel byproduct (Blueprint §B: byproduct, not source of truth)
    v1_xlsx, v2_xlsx = models / "v1.xlsx", models / "v2.xlsx"
    ingestion.write_excel(v1, v1_xlsx, "V1 (Baseline)", spec=spec)
    ingestion.write_excel(v2, v2_xlsx, "V2 (Revised)", spec=spec)

    # 3) SIA gate — the ONE fail-fast structural gate in the pipeline;
    # no attribution runs on a structurally unverified model.
    sia_v1 = run_structural_checks(v1_xlsx, spec=spec)
    sia_v2 = run_structural_checks(v2_xlsx, spec=spec)
    if not (sia_v1.passed and sia_v2.passed):
        raise PipelineHaltedError(
            "SIA failed — halting before variance attribution.\n"
            f"V1:\n{sia_v1.summary()}\nV2:\n{sia_v2.summary()}"
        )

    v1_fcf, v2_fcf = model_fn(v1), model_fn(v2)
    total_variance = v2_fcf - v1_fcf

    # 4) Sequential bridge (diagnostic)
    bridge = sequential_bridge(v1, v2, changed, model_fn=model_fn)
    all_ord = all_orderings(v1, v2, changed, seed=seed, model_fn=model_fn)
    matrix = ordering_impact_matrix(all_ord)

    # 5) Shapley (primary)
    shap = shapley_attribution(v1, v2, changed, method=method, seed=seed, model_fn=model_fn)

    # 6) Interactions
    interactions = interaction_report(v1, v2, changed, model_fn=model_fn)

    # 7) Audit manifest
    from .audit import run_manifest

    manifest = run_manifest(v1, v2, changed)

    comparison = sequential_vs_shapley(bridge, matrix, shap, changed)

    # 8) Phase-2 optional stages: DIA (global/local sensitivity) and TBA
    # (threshold analysis). Both are computed against V1 as the base case.
    dia_tornado = dia_sobol = tba_results = None
    if run_dia:
        _anchors = {"revenue_prior", "fcf_base", "net_debt", "shares_outstanding"}
        dia_drivers = tuple(r for r in spec.roles if r not in _anchors)
        dia_tornado = tornado(v1, dia_drivers, model_fn=model_fn)
        dia_sobol = sobol_indices(v1, dia_drivers, seed=seed, model_fn=model_fn)
    if run_tba:
        tba_results = {}
        for name in spec.roles:
            rng = DEFAULT_SEARCH_RANGES.get(name)
            if rng is None:
                continue
            tba_results[name] = find_threshold(v1, name, rng, target_fn=model_fn)

    result = PipelineResult(
        v1=v1,
        v2=v2,
        changed=changed,
        v1_fcf=v1_fcf,
        v2_fcf=v2_fcf,
        total_variance=total_variance,
        sia_v1=sia_v1,
        sia_v2=sia_v2,
        bridge_canonical=bridge,
        ordering_matrix=matrix,
        shapley=shap,
        comparison=comparison,
        interactions=interactions,
        manifest=manifest,
        spec=spec,
        dia_tornado=dia_tornado,
        dia_sobol=dia_sobol,
        tba_results=tba_results,
    )

    _write_outputs(result, outputs)
    return result


def _write_outputs(result: PipelineResult, outputs: Path) -> None:
    reg = change_register(result.v1, result.v2, result.changed, spec=result.spec)
    reg.to_csv(outputs / "change_register.csv", index=False)

    snap = model_snapshot(result.v1, result.v2, spec=result.spec)
    snap.to_csv(outputs / "model_snapshot.csv")

    result.bridge_canonical.to_csv(outputs / "variance_bridge.csv", index=False)

    all_ord_rows = []
    for ordering in result.ordering_matrix.index:
        for driver in [c for c in result.ordering_matrix.columns if c != "total"]:
            all_ord_rows.append(
                {"ordering": ordering, "driver": driver, "incremental_impact": result.ordering_matrix.loc[ordering, driver]}
            )
    pd.DataFrame(all_ord_rows).to_csv(outputs / "variance_bridge_all_orderings.csv", index=False)
    result.ordering_matrix.to_csv(outputs / "ordering_sensitivity_matrix.csv")

    result.shapley.to_csv(outputs / "shapley_attribution.csv", index=False)
    result.comparison.to_csv(outputs / "sequential_vs_shapley.csv")
    # Export the Möbius interaction terms, which are what L1 aggregates.
    # The pairwise Grabisch-Roubens indices are a different (interpretable,
    # reader-facing) quantity and are exported separately; summing THOSE
    # would not reconcile to the reported L1, which is exactly the tie-out
    # failure adversarial review caught.
    _mob = result.interactions.get("mobius", {})
    pd.DataFrame(
        [{"subset": " x ".join(T), "order": len(T), "mobius_interaction": val}
         for T, val in sorted(_mob.items(), key=lambda kv: (len(kv[0]), kv[0]))]
    ).to_csv(outputs / "interaction_terms.csv", index=False)
    result.interactions["pairwise"].to_csv(outputs / "pairwise_interactions.csv", index=False)

    plot_waterfall(
        result.bridge_canonical,
        result.v1_fcf,
        result.v2_fcf,
        outputs / "variance_bridge.png",
        f"V1 -> V2 Sequential Variance Bridge (order: {' -> '.join(result.changed)})",
    )
    plot_shapley_with_whisker(
        result.shapley,
        result.ordering_matrix,
        result.total_variance,
        result.interactions["l1_non_additivity"],
        outputs / "shapley_attribution.png",
    )
    plot_ordering_sensitivity(result.ordering_matrix, outputs / "ordering_sensitivity.png")
    plot_interactions(result.interactions["pairwise"], outputs / "pairwise_interactions.png")

    # Phase-2 artefacts, written only when the corresponding stage ran.
    if result.dia_tornado is not None:
        result.dia_tornado.to_csv(outputs / "dia_tornado.csv", index=False)
        plot_tornado(result.dia_tornado, outputs / "dia_tornado.png")
    if result.dia_sobol is not None:
        result.dia_sobol.to_csv(outputs / "dia_sobol.csv", index=False)
        plot_sobol(result.dia_sobol, outputs / "dia_sobol.png")
    if result.tba_results is not None:
        tba_rows = [
            {
                "driver": name,
                "defined": tr.defined,
                "threshold": tr.threshold,
                "search_low": tr.search_low,
                "search_high": tr.search_high,
                "n_sign_changes": tr.n_sign_changes,
                "reason": tr.reason,
            }
            for name, tr in result.tba_results.items()
        ]
        pd.DataFrame(tba_rows).to_csv(outputs / "tba_thresholds.csv", index=False)

    (outputs / "report.md").write_text(build_report_markdown(result))
    (outputs / "report.html").write_text(build_html_report(result, outputs))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="bridgework", description="Bridgework variance-bridge CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    compare = sub.add_parser("compare", help="Compare two driver files and produce the full variance-bridge report")
    compare.add_argument("v1", help="Path to V1 (baseline) YAML driver file")
    compare.add_argument("v2", help="Path to V2 (revised) YAML driver file")
    compare.add_argument("--method", choices=["auto", "exact", "monte_carlo"], default="auto")
    compare.add_argument("--seed", type=int, default=42)
    compare.add_argument(
        "--model", choices=["fcf", "dcf"], default=None,
        help="Which model to attribute: 'fcf' (operating free cash flow, default) "
             "or 'dcf' (valuation — implied share price). A driver file may also "
             "declare its own model via a top-level 'model:' key.",
    )
    compare.add_argument("--outdir", default="outputs")
    compare.add_argument("--models-dir", default="models")
    compare.add_argument(
        "--dia",
        action="store_true",
        help="Run Driver Impact Analysis (tornado + Sobol global sensitivity) against V1 as base case",
    )
    compare.add_argument(
        "--tba",
        action="store_true",
        help="Run Threshold & Break-Point Analysis (FCF=0 crossing per driver, with monotonicity guard)",
    )
    compare.add_argument(
        "--full",
        action="store_true",
        help="Run every stage: equivalent to --dia --tba",
    )

    derive = sub.add_parser(
        "derive",
        help="Turn ordinary line items into Bridgework driver files (arithmetic only — does not read filings)",
    )
    derive.add_argument("v1_lines", nargs="?", help="V1 line-items YAML")
    derive.add_argument("v2_lines", nargs="?", help="V2 line-items YAML")
    derive.add_argument("--outdir", default=".", help="Where to write the driver files")
    derive.add_argument("--template", metavar="PATH", help="Write a blank line-items template and exit")

    args = parser.parse_args(argv)

    if args.command == "derive":
        from .derive import DerivationError

        if args.template:
            write_template(args.template)
            print(f"Blank line-items template written to {args.template}")
            print("Fill it in for each version, then run: bridgework derive v1.yaml v2.yaml")
            return 0
        if not (args.v1_lines and args.v2_lines):
            print("error: provide two line-items files, or use --template to create one", file=sys.stderr)
            return 1
        try:
            outdir = Path(args.outdir)
            outdir.mkdir(parents=True, exist_ok=True)
            written = []
            for src, stem in ((args.v1_lines, "v1_drivers.yaml"), (args.v2_lines, "v2_drivers.yaml")):
                items, label = load_line_items(src)
                d = derive_drivers(items)
                dest = outdir / stem
                write_driver_file(d, dest, label)
                written.append(dest)
                print(f"\n{label}  ->  {dest}")
                print(d.explain())
        except DerivationError as exc:
            print(str(exc), file=sys.stderr)
            return 4
        print(f"\nNow run:  bridgework compare {written[0]} {written[1]} --full")
        return 0


    if args.command == "compare":
        try:
            result = run_pipeline(
                args.v1,
                args.v2,
                output_dir=args.outdir,
                models_dir=args.models_dir,
                method=args.method,
                seed=args.seed,
                run_dia=args.dia or args.full,
                run_tba=args.tba or args.full,
                model=args.model,
            )
        except PipelineHaltedError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        except ingestion.BridgeworkSchemaError as exc:
            print(str(exc), file=sys.stderr)
            return 3

        print(executive_summary(result))
        print(f"\nOutputs written to {args.outdir}/, models to {args.models_dir}/")
        return 0

    return 1  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
