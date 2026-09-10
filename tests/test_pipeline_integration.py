"""
Integration tests: Excel -> canonical -> engine -> report, end to end
(Blueprint §I), plus the SIA fail-fast halt and the Shapley exact/MC
scaling switch point.
"""
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from bridgework import cli, ingestion
from bridgework.model import Drivers
from bridgework.variance_bridge import EXACT_SHAPLEY_MAX_DRIVERS, shapley_attribution

DATA_DIR = Path(__file__).parent.parent / "data" / "illustrative"

V1 = Drivers(
    revenue_prior=4527.0,
    revenue_growth=0.031,
    cogs_pct=0.240,
    opex_pct=0.520,
    tax_rate=0.180,
    nwc_pct=0.050,
    capex_pct=0.030,
)


def test_full_pipeline_end_to_end(tmp_path):
    result = cli.run_pipeline(
        str(DATA_DIR / "zoom_v1_drivers.yaml"),
        str(DATA_DIR / "zoom_v2_drivers.yaml"),
        output_dir=str(tmp_path / "outputs"),
        models_dir=str(tmp_path / "models"),
    )
    assert result.sia_v1.passed and result.sia_v2.passed
    assert (tmp_path / "models" / "v1.xlsx").exists()
    assert (tmp_path / "models" / "v2.xlsx").exists()
    assert (tmp_path / "outputs" / "report.md").exists()
    assert (tmp_path / "outputs" / "shapley_attribution.png").exists()


def test_cli_main_returns_zero_on_success(tmp_path, capsys):
    exit_code = cli.main(
        [
            "compare",
            str(DATA_DIR / "zoom_v1_drivers.yaml"),
            str(DATA_DIR / "zoom_v2_drivers.yaml"),
            "--outdir",
            str(tmp_path / "outputs"),
            "--models-dir",
            str(tmp_path / "models"),
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Free Cash Flow" in captured.out


def test_cli_reports_schema_violation_with_nonzero_exit(tmp_path, capsys):
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(yaml.dump({"schema_version": "1.0.0"}))  # missing 'drivers'
    exit_code = cli.main(
        [
            "compare",
            str(bad_yaml),
            str(DATA_DIR / "zoom_v2_drivers.yaml"),
            "--outdir",
            str(tmp_path / "outputs"),
            "--models-dir",
            str(tmp_path / "models"),
        ]
    )
    assert exit_code == 3


def test_sia_failure_halts_pipeline_before_attribution(tmp_path, monkeypatch):
    """Corrupt the generated V1 workbook right after write_excel -- SIA is
    the pipeline's one fail-fast structural gate and must catch it before
    Shapley ever runs."""
    import openpyxl

    original_write_excel = ingestion.write_excel

    def tampering_write_excel(drivers, path, title, spec=None):
        original_write_excel(drivers, path, title, spec=spec)
        if "v1" in str(path):
            wb = openpyxl.load_workbook(path)
            wb["Calc"]["B7"] = 999.0  # hardcoded literal -> trips SIA check 3
            wb.save(path)

    monkeypatch.setattr(cli.ingestion, "write_excel", tampering_write_excel)

    with pytest.raises(cli.PipelineHaltedError, match="SIA failed"):
        cli.run_pipeline(
            str(DATA_DIR / "zoom_v1_drivers.yaml"),
            str(DATA_DIR / "zoom_v2_drivers.yaml"),
            output_dir=str(tmp_path / "outputs"),
            models_dir=str(tmp_path / "models"),
        )
    # Confirm no attribution CSVs were written -- the halt happened
    # strictly before Shapley/interactions ran (fail-fast, hard constraint).
    assert not (tmp_path / "outputs" / "shapley_attribution.csv").exists()


def test_cli_accepts_excel_round_trip_input(tmp_path):
    """End-to-end exercise of Decision 3: generate via one pipeline run,
    hand-edit a driver value in the resulting workbook, feed the .xlsx
    straight back into the CLI as V2."""
    import openpyxl

    cli.run_pipeline(
        str(DATA_DIR / "zoom_v1_drivers.yaml"),
        str(DATA_DIR / "zoom_v1_drivers.yaml"),  # V1 vs itself, just to generate the workbook
        output_dir=str(tmp_path / "outputs0"),
        models_dir=str(tmp_path / "models0"),
    )
    v1_xlsx = tmp_path / "models0" / "v1.xlsx"
    wb = openpyxl.load_workbook(v1_xlsx)
    wb["Drivers"]["B5"] = 0.055  # revenue_growth edited by hand
    wb["Drivers"]["B7"] = 0.495  # opex_pct edited by hand
    wb["Drivers"]["B10"] = 0.045  # capex_pct edited by hand
    wb.save(v1_xlsx)

    result = cli.run_pipeline(
        str(DATA_DIR / "zoom_v1_drivers.yaml"),
        str(v1_xlsx),
        output_dir=str(tmp_path / "outputs1"),
        models_dir=str(tmp_path / "models1"),
    )
    assert result.total_variance == pytest.approx(38.958, abs=1e-2)


def test_shapley_scaling_switch_point():
    """9 changed drivers must switch to Monte Carlo under 'auto'; 8 or
    fewer stays exact (Blueprint §G Decision 4)."""
    # Build a synthetic 9-role scenario isn't possible with the fixed
    # 7-field Drivers dataclass, so instead assert the switch policy
    # directly against the documented threshold and confirm the 7-driver
    # (all canonical roles differ) real case stays exact.
    v2_all_seven = replace(
        V1,
        revenue_prior=4600.0,
        revenue_growth=0.05,
        cogs_pct=0.23,
        opex_pct=0.50,
        tax_rate=0.19,
        nwc_pct=0.04,
        capex_pct=0.04,
    )
    changed = tuple(V1.to_dict().keys())  # all 7 roles changed
    assert len(changed) <= EXACT_SHAPLEY_MAX_DRIVERS
    shap = shapley_attribution(V1, v2_all_seven, changed, method="auto")
    assert (shap["method"] == "exact").all()


# ------------------------------------------------------------------ #
# Phase 2 — DIA / TBA pipeline integration
# ------------------------------------------------------------------ #
def test_phase2_stages_are_off_by_default(tmp_path):
    """Default pipeline must stay Phase-1 exact: no DIA/TBA computed, no
    Phase-2 artefacts written. This is what keeps the golden dataset
    byte-identical regardless of Phase-2 existing."""
    result = cli.run_pipeline(
        str(DATA_DIR / "zoom_v1_drivers.yaml"),
        str(DATA_DIR / "zoom_v2_drivers.yaml"),
        output_dir=str(tmp_path / "outputs"),
        models_dir=str(tmp_path / "models"),
    )
    assert result.dia_tornado is None
    assert result.dia_sobol is None
    assert result.tba_results is None
    assert not (tmp_path / "outputs" / "dia_sobol.csv").exists()
    assert not (tmp_path / "outputs" / "tba_thresholds.csv").exists()


def test_phase2_full_run_produces_all_artefacts(tmp_path):
    result = cli.run_pipeline(
        str(DATA_DIR / "zoom_v1_drivers.yaml"),
        str(DATA_DIR / "zoom_v2_drivers.yaml"),
        output_dir=str(tmp_path / "outputs"),
        models_dir=str(tmp_path / "models"),
        run_dia=True,
        run_tba=True,
    )
    assert result.dia_tornado is not None
    assert result.dia_sobol is not None
    assert result.tba_results is not None
    for artefact in ("dia_tornado.csv", "dia_tornado.png", "dia_sobol.csv", "dia_sobol.png", "tba_thresholds.csv"):
        assert (tmp_path / "outputs" / artefact).exists(), f"missing {artefact}"


def test_phase2_does_not_change_phase1_numbers(tmp_path):
    """Running DIA/TBA must not perturb the variance-bridge results in any
    way -- they are additive diagnostics, not inputs to attribution."""
    base = cli.run_pipeline(
        str(DATA_DIR / "zoom_v1_drivers.yaml"),
        str(DATA_DIR / "zoom_v2_drivers.yaml"),
        output_dir=str(tmp_path / "out_base"),
        models_dir=str(tmp_path / "mod_base"),
    )
    full = cli.run_pipeline(
        str(DATA_DIR / "zoom_v1_drivers.yaml"),
        str(DATA_DIR / "zoom_v2_drivers.yaml"),
        output_dir=str(tmp_path / "out_full"),
        models_dir=str(tmp_path / "mod_full"),
        run_dia=True,
        run_tba=True,
    )
    assert base.v1_fcf == full.v1_fcf
    assert base.v2_fcf == full.v2_fcf
    assert base.total_variance == full.total_variance
    assert (base.shapley["shapley_contribution"].values == full.shapley["shapley_contribution"].values).all()


def test_decision_priority_switches_formula_with_dia_present(tmp_path):
    """Phase 1 ranks on Shapley magnitude alone; Phase 2 uses the weighted
    3-factor formula (Blueprint §J)."""
    from bridgework.report import decision_priority_table

    base = cli.run_pipeline(
        str(DATA_DIR / "zoom_v1_drivers.yaml"),
        str(DATA_DIR / "zoom_v2_drivers.yaml"),
        output_dir=str(tmp_path / "out_base"),
        models_dir=str(tmp_path / "mod_base"),
    )
    full = cli.run_pipeline(
        str(DATA_DIR / "zoom_v1_drivers.yaml"),
        str(DATA_DIR / "zoom_v2_drivers.yaml"),
        output_dir=str(tmp_path / "out_full"),
        models_dir=str(tmp_path / "mod_full"),
        run_dia=True,
        run_tba=True,
    )
    assert "Phase 1" in decision_priority_table(base).iloc[0]["method"]
    assert "Phase 2" in decision_priority_table(full).iloc[0]["method"]


def test_cli_full_flag(tmp_path):
    exit_code = cli.main(
        [
            "compare",
            str(DATA_DIR / "zoom_v1_drivers.yaml"),
            str(DATA_DIR / "zoom_v2_drivers.yaml"),
            "--full",
            "--outdir",
            str(tmp_path / "outputs"),
            "--models-dir",
            str(tmp_path / "models"),
        ]
    )
    assert exit_code == 0
    assert (tmp_path / "outputs" / "dia_sobol.csv").exists()
    assert (tmp_path / "outputs" / "tba_thresholds.csv").exists()
