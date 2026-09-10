"""
Phase 6 — DCF valuation attribution.

The reason this model earns its place: a DCF is severely non-linear where
the FCF model is nearly bilinear, because terminal value divides by
(WACC - g). That makes the ordering problem materially worse, which makes
the case for order-independent attribution materially stronger.
"""
from dataclasses import replace
from pathlib import Path

import pytest

from bridgework import cli
from bridgework.dcf import (
    FORECAST_YEARS,
    DCFDrivers,
    InvalidDCFError,
    compute_dcf_line_items,
    compute_share_price,
    terminal_value_share,
)
from bridgework.interactions import interaction_report
from bridgework.model_spec import DCF_MODEL, FCF_MODEL, get_model
from bridgework.variance_bridge import all_orderings, shapley_attribution

DATA = Path(__file__).parent.parent / "data" / "dcf_valuation"
V1 = DCFDrivers(
    fcf_base=1000.0, growth_explicit=0.08, wacc=0.075,
    terminal_growth=0.035, net_debt=4000.0, shares_outstanding=250.0,
)
V2 = replace(V1, growth_explicit=0.055, wacc=0.085, terminal_growth=0.028)
CHANGED = ("growth_explicit", "wacc", "terminal_growth")
TOL = 1e-9


# ---------------------------------------------------------------- #
# Model mechanics
# ---------------------------------------------------------------- #
def test_share_price_is_deterministic():
    assert compute_share_price(V1) == compute_share_price(V1)


def test_line_items_reconcile_to_share_price():
    items = compute_dcf_line_items(V1)
    assert items["Implied share price"] == pytest.approx(compute_share_price(V1), abs=TOL)
    assert items["Enterprise value"] == pytest.approx(
        items["PV of explicit period"] + items["PV of terminal value"], abs=1e-9
    )
    assert items["Equity value"] == pytest.approx(items["Enterprise value"] - V1.net_debt, abs=1e-9)


def test_explicit_period_length_matches_constant():
    items = compute_dcf_line_items(V1)
    assert f"FCF year {FORECAST_YEARS}" in items
    assert f"FCF year {FORECAST_YEARS + 1}" not in items


def test_higher_wacc_lowers_price():
    assert compute_share_price(replace(V1, wacc=0.09)) < compute_share_price(V1)


def test_higher_terminal_growth_raises_price():
    assert compute_share_price(replace(V1, terminal_growth=0.04)) > compute_share_price(V1)


def test_terminal_value_share_flags_perpetuity_heavy_valuation():
    """A tight WACC-g spread pushes most of the value into perpetuity --
    the standard practitioner sanity check."""
    share = terminal_value_share(V1)
    assert 0.75 < share < 0.95


# ---------------------------------------------------------------- #
# The coalition-validity guard
# ---------------------------------------------------------------- #
def test_wacc_below_terminal_growth_is_refused():
    with pytest.raises(InvalidDCFError, match="must exceed terminal growth"):
        compute_share_price(replace(V1, wacc=0.02, terminal_growth=0.04))


def test_wacc_equal_to_terminal_growth_is_refused():
    with pytest.raises(InvalidDCFError):
        compute_share_price(replace(V1, wacc=0.03, terminal_growth=0.03))


def test_zero_shares_refused():
    with pytest.raises(InvalidDCFError, match="shares_outstanding"):
        compute_share_price(replace(V1, shares_outstanding=0.0))


def test_guard_catches_the_coalition_case_not_just_the_endpoints():
    """The subtle failure this guard exists for: V1 and V2 are each
    individually valid, but a Shapley coalition mixing them is not.

    V1: WACC 6.0% > g 5.0%  -> valid
    V2: WACC 9.0% > g 7.0%  -> valid
    Coalition {WACC from V1, g from V2}: 6.0% < 7.0% -> UNDEFINED.

    Attribution must fail loudly here rather than silently returning an
    absurd terminal value from a negative denominator.
    """
    a = replace(V1, wacc=0.060, terminal_growth=0.050)
    b = replace(V1, wacc=0.090, terminal_growth=0.070)
    compute_share_price(a)  # individually valid
    compute_share_price(b)  # individually valid

    with pytest.raises(InvalidDCFError, match="must exceed terminal growth"):
        compute_share_price(replace(a, terminal_growth=b.terminal_growth))

    # And the attribution itself must surface it rather than swallow it.
    with pytest.raises(InvalidDCFError):
        shapley_attribution(a, b, ("wacc", "terminal_growth"), model_fn=compute_share_price)


def test_coalition_validity_precondition_is_stated_correctly():
    """The checkable rule is min(WACC) > max(terminal growth) across both
    versions. Confirm it correctly separates a safe pair from an unsafe
    one."""
    unsafe_a = replace(V1, wacc=0.060, terminal_growth=0.050)
    unsafe_b = replace(V1, wacc=0.090, terminal_growth=0.070)
    assert min(unsafe_a.wacc, unsafe_b.wacc) <= max(unsafe_a.terminal_growth, unsafe_b.terminal_growth)

    # The shipped fixture satisfies the rule and therefore attributes cleanly.
    assert min(V1.wacc, V2.wacc) > max(V1.terminal_growth, V2.terminal_growth)


def test_valid_version_pair_produces_no_invalid_coalitions():
    """The shipped fixture must satisfy min(WACC) > max(g) so every
    coalition is computable -- otherwise attribution could not run."""
    assert min(V1.wacc, V2.wacc) > max(V1.terminal_growth, V2.terminal_growth)
    shapley_attribution(V1, V2, CHANGED, model_fn=compute_share_price)  # must not raise


# ---------------------------------------------------------------- #
# Attribution behaviour — the actual thesis
# ---------------------------------------------------------------- #
def test_shapley_efficiency_holds_on_the_dcf():
    shap = shapley_attribution(V1, V2, CHANGED, method="exact", model_fn=compute_share_price)
    target = compute_share_price(V2) - compute_share_price(V1)
    assert shap["shapley_contribution"].sum() == pytest.approx(target, abs=TOL)


def test_dcf_is_more_non_additive_than_the_fcf_model():
    """The core claim justifying this module: valuation attribution is
    materially more order-dependent than FCF attribution. The Zoom FCF
    fixture measures ~9.9%; this must clearly exceed it."""
    rep = interaction_report(V1, V2, CHANGED, model_fn=compute_share_price)
    assert rep["l1_pct_of_variance"] > 15.0, (
        f"expected materially higher non-additivity than the FCF model's 9.9%, "
        f"got {rep['l1_pct_of_variance']:.1f}%"
    )


def test_wacc_terminal_growth_is_the_dominant_interaction():
    """The (WACC - g) denominator should make that pair the largest
    interaction term -- the structural reason DCFs misattribute."""
    rep = interaction_report(V1, V2, CHANGED, model_fn=compute_share_price)
    pairs = rep["pairwise"].set_index(["driver_a", "driver_b"])["interaction"].abs()
    top = pairs.idxmax()
    assert set(top) == {"wacc", "terminal_growth"}
    assert pairs.max() > 0.5 * pairs.sum()  # over half of all pairwise interaction


def test_ordering_ambiguity_is_material_on_the_dcf():
    ao = all_orderings(V1, V2, CHANGED, model_fn=compute_share_price)
    spread = ao.groupby("driver")["incremental_impact"].agg(lambda s: s.max() - s.min())
    total = abs(compute_share_price(V2) - compute_share_price(V1))
    assert spread.max() / total > 0.10, "ordering spread should be >10% of the total move"


# ---------------------------------------------------------------- #
# Registry + pipeline
# ---------------------------------------------------------------- #
def test_model_registry_resolves_both_models():
    assert get_model("fcf") is FCF_MODEL
    assert get_model("dcf") is DCF_MODEL
    assert get_model(None) is FCF_MODEL  # back-compatible default


def test_unknown_model_rejected():
    with pytest.raises(ValueError, match="Unknown model"):
        get_model("lbo")


def test_yaml_file_declares_its_own_model(tmp_path):
    """A driver file carrying 'model: dcf' must select the DCF model
    without needing the --model flag."""
    result = cli.run_pipeline(
        str(DATA / "target_v1_drivers.yaml"), str(DATA / "target_v2_drivers.yaml"),
        output_dir=str(tmp_path / "out"), models_dir=str(tmp_path / "mod"),
    )
    assert result.spec.key == "dcf"


def test_dcf_pipeline_end_to_end(tmp_path):
    result = cli.run_pipeline(
        str(DATA / "target_v1_drivers.yaml"), str(DATA / "target_v2_drivers.yaml"),
        output_dir=str(tmp_path / "out"), models_dir=str(tmp_path / "mod"),
        run_dia=True, run_tba=True,
    )
    assert result.sia_v1.passed and result.sia_v2.passed
    assert result.shapley["shapley_contribution"].sum() == pytest.approx(result.total_variance, abs=TOL)
    assert (tmp_path / "out" / "report.html").exists()
    assert (tmp_path / "out" / "dia_sobol.csv").exists()


def test_dcf_report_speaks_valuation_not_cash_flow(tmp_path):
    """Report copy must adapt to the model -- a valuation report saying
    'Free Cash Flow' would be wrong and would read as a template leak."""
    cli.run_pipeline(
        str(DATA / "target_v1_drivers.yaml"), str(DATA / "target_v2_drivers.yaml"),
        output_dir=str(tmp_path / "out"), models_dir=str(tmp_path / "mod"),
    )
    html = (tmp_path / "out" / "report.html").read_text()
    assert "Implied share price" in html or "implied share price" in html
    assert "/share" in html
    assert "Free Cash Flow increased" not in html


def test_dcf_excel_round_trip(tmp_path):
    """The DCF workbook must satisfy the same Excel contract as the FCF
    one -- generated, validated, and re-ingestible."""
    from bridgework.ingestion import load_from_excel

    cli.run_pipeline(
        str(DATA / "target_v1_drivers.yaml"), str(DATA / "target_v2_drivers.yaml"),
        output_dir=str(tmp_path / "out"), models_dir=str(tmp_path / "mod"),
    )
    reloaded = load_from_excel(tmp_path / "mod" / "v1.xlsx")
    assert isinstance(reloaded, DCFDrivers)
    assert reloaded.wacc == pytest.approx(V1.wacc, abs=1e-9)
    assert compute_share_price(reloaded) == pytest.approx(compute_share_price(V1), abs=1e-6)


def test_sia_flags_wacc_below_terminal_growth_in_workbook(tmp_path):
    """SIA's model-aware sign check must catch the undefined-DCF case at
    the structural gate, before attribution runs."""
    import openpyxl

    from bridgework.ingestion import write_excel
    from bridgework.sia import run_structural_checks

    p = tmp_path / "bad.xlsx"
    write_excel(V1, p, "bad", spec=DCF_MODEL)
    wb = openpyxl.load_workbook(p)
    wb["Drivers"]["B6"] = 0.02   # wacc
    wb["Drivers"]["B7"] = 0.05   # terminal_growth
    wb.save(p)
    report = run_structural_checks(p, spec=DCF_MODEL)
    check5 = next(r for r in report.results if r.check_id == 5)
    assert not check5.passed
    assert "terminal growth" in check5.message


def test_report_units_switch_with_the_model(tmp_path):
    """A per-share model must never print '$M' and vice versa. This is the
    kind of template leak that destroys credibility with a finance reader,
    so it is locked in rather than left to review."""
    cli.run_pipeline(
        str(DATA / "target_v1_drivers.yaml"), str(DATA / "target_v2_drivers.yaml"),
        output_dir=str(tmp_path / "dcf"), models_dir=str(tmp_path / "dcfm"),
    )
    dcf_html = (tmp_path / "dcf" / "report.html").read_text()
    assert "/share</span> spread" in dcf_html
    assert "M</span> spread" not in dcf_html

    illustrative = Path(__file__).parent.parent / "data" / "illustrative"
    cli.run_pipeline(
        str(illustrative / "zoom_v1_drivers.yaml"), str(illustrative / "zoom_v2_drivers.yaml"),
        output_dir=str(tmp_path / "fcf"), models_dir=str(tmp_path / "fcfm"),
    )
    fcf_html = (tmp_path / "fcf" / "report.html").read_text()
    assert "M</span> spread" in fcf_html
    assert "/share" not in fcf_html


def test_interaction_csv_reconciles_to_reported_l1(tmp_path):
    """A reader summing interaction_terms.csv must arrive at the same L1
    figure the report states. Omitting the higher-order term silently
    breaks that tie-out."""
    import pandas as pd

    result = cli.run_pipeline(
        str(DATA / "target_v1_drivers.yaml"), str(DATA / "target_v2_drivers.yaml"),
        output_dir=str(tmp_path / "out"), models_dir=str(tmp_path / "mod"),
    )
    csv = pd.read_csv(tmp_path / "out" / "interaction_terms.csv")
    assert csv["mobius_interaction"].abs().sum() == pytest.approx(
        result.interactions["l1_non_additivity"], abs=1e-9
    )


def test_invalid_coalition_is_caught_preflight_not_midpipeline(tmp_path):
    """Adversarial review finding: the coalition guard fired mid-run, after
    workbooks had already been written, as a raw exception. The precondition
    is checkable up front and should produce a clean, actionable message."""
    import yaml

    from bridgework.cli import PipelineHaltedError

    def write(path, wacc, g):
        path.write_text(yaml.dump({
            "schema_version": "1.0.0", "model": "dcf", "label": "x",
            "drivers": {"fcf_base": 1000.0, "growth_explicit": 0.05, "wacc": wacc,
                        "terminal_growth": g, "net_debt": 4000.0, "shares_outstanding": 250.0},
        }))

    a, b = tmp_path / "a.yaml", tmp_path / "b.yaml"
    write(a, 0.060, 0.050)   # individually valid
    write(b, 0.090, 0.070)   # individually valid; mixture is not
    compute_share_price(load_from_yaml_for_test(a))
    compute_share_price(load_from_yaml_for_test(b))

    with pytest.raises(PipelineHaltedError, match="min\\(WACC\\) > max\\(terminal growth\\)"):
        cli.run_pipeline(str(a), str(b), output_dir=str(tmp_path / "o"), models_dir=str(tmp_path / "m"))

    assert not (tmp_path / "m").exists() or not list((tmp_path / "m").glob("*.xlsx")), \
        "pre-flight must halt before any workbook is written"


def load_from_yaml_for_test(p):
    from bridgework.ingestion import load_from_yaml
    from bridgework.model_spec import get_model
    return load_from_yaml(p, spec=get_model("dcf"))
