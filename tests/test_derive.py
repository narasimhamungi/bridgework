"""
Phase 7 — driver derivation.

Scope check that matters as much as the behaviour: this module does
arithmetic on line items an analyst supplies. It does not read filings, and
these tests assert that boundary stays where it is.
"""
from pathlib import Path

import pytest
import yaml

from bridgework import cli
from bridgework.derive import (
    DerivationError,
    LineItems,
    derive_drivers,
    load_line_items,
    write_driver_file,
    write_template,
)
from bridgework.ingestion import load_from_yaml
from bridgework.model import CANONICAL_ROLES

BASE = LineItems(
    revenue=4667.0,
    prior_revenue=4527.0,
    cost_of_goods_sold=1120.0,
    operating_expenses=2427.0,
    tax_expense=189.0,
    pretax_income=1050.0,
    net_working_capital=233.0,
    capital_expenditure=140.0,
)


# ---------------------------------------------------------------- #
# Arithmetic
# ---------------------------------------------------------------- #
def test_every_canonical_role_is_derived():
    d = derive_drivers(BASE)
    for role in CANONICAL_ROLES:
        assert isinstance(getattr(d.drivers, role), float)


def test_ratios_are_the_obvious_divisions():
    d = derive_drivers(BASE).drivers
    assert d.revenue_growth == pytest.approx(4667.0 / 4527.0 - 1, abs=1e-12)
    assert d.cogs_pct == pytest.approx(1120.0 / 4667.0, abs=1e-12)
    assert d.opex_pct == pytest.approx(2427.0 / 4667.0, abs=1e-12)
    assert d.tax_rate == pytest.approx(189.0 / 1050.0, abs=1e-12)
    assert d.nwc_pct == pytest.approx(233.0 / 4667.0, abs=1e-12)
    assert d.capex_pct == pytest.approx(140.0 / 4667.0, abs=1e-12)
    assert d.revenue_prior == pytest.approx(4527.0, abs=1e-12)


def test_workings_are_recorded_for_every_driver():
    """The derivation must be auditable, not magic."""
    d = derive_drivers(BASE)
    for role in CANONICAL_ROLES:
        assert role in d.workings
        assert d.workings[role].strip()


def test_derivation_is_deterministic():
    a, b = derive_drivers(BASE), derive_drivers(BASE)
    assert a.drivers == b.drivers


# ---------------------------------------------------------------- #
# Refusal and warning behaviour
# ---------------------------------------------------------------- #
def test_zero_revenue_refused():
    with pytest.raises(DerivationError, match="revenue must be > 0"):
        derive_drivers(LineItems(**{**BASE.__dict__, "revenue": 0.0}))


def test_non_finite_input_refused():
    with pytest.raises(DerivationError, match="not a finite number"):
        derive_drivers(LineItems(**{**BASE.__dict__, "capital_expenditure": float("nan")}))


def test_all_problems_reported_together_not_just_the_first():
    with pytest.raises(DerivationError) as exc:
        derive_drivers(LineItems(**{**BASE.__dict__, "revenue": 0.0, "prior_revenue": -5.0}))
    assert len(exc.value.problems) >= 2


def test_units_mismatch_produces_a_warning_not_a_silent_result():
    """The most likely real-world mistake: mixing $M and $000s. The tool
    must flag it rather than quietly deriving a −99.9% growth rate."""
    d = derive_drivers(LineItems(**{**BASE.__dict__, "prior_revenue": 4527000.0}))
    assert any("revenue growth" in w for w in d.warnings)


def test_negative_pretax_income_warns_about_the_tax_rate():
    d = derive_drivers(LineItems(**{**BASE.__dict__, "pretax_income": -500.0, "tax_expense": 20.0}))
    assert any("negative" in w for w in d.warnings)


def test_zero_pretax_income_does_not_divide_by_zero():
    d = derive_drivers(LineItems(**{**BASE.__dict__, "pretax_income": 0.0}))
    assert d.drivers.tax_rate == 0.0
    assert any("zero" in w for w in d.warnings)


def test_warnings_do_not_block_derivation():
    """Plausibility warnings are advisory. The analyst may have an unusual
    but correct model; the tool flags and proceeds rather than refusing."""
    d = derive_drivers(LineItems(**{**BASE.__dict__, "capital_expenditure": 3000.0}))
    assert d.warnings
    assert d.drivers.capex_pct > 0.5


# ---------------------------------------------------------------- #
# Files and round trip
# ---------------------------------------------------------------- #
def test_template_round_trips_through_the_loader(tmp_path):
    p = tmp_path / "t.yaml"
    write_template(p)
    items, label = load_line_items(p)
    assert isinstance(items, LineItems)
    assert label


def test_missing_line_item_rejected(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.dump({"line_items": {"revenue": 100.0}}))
    with pytest.raises(DerivationError, match="missing line items"):
        load_line_items(p)


def test_unknown_line_item_rejected(tmp_path):
    d = {k: 1.0 for k in BASE.__dict__}
    d["ebitda"] = 5.0
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.dump({"line_items": d}))
    with pytest.raises(DerivationError, match="unknown line items"):
        load_line_items(p)


def test_written_driver_file_is_loadable_by_the_engine(tmp_path):
    """The whole point: derived output must feed straight into `compare`."""
    d = derive_drivers(BASE)
    p = tmp_path / "v1.yaml"
    write_driver_file(d, p, "test")
    reloaded = load_from_yaml(p)
    assert reloaded == d.drivers


def test_warnings_are_carried_into_the_written_file(tmp_path):
    d = derive_drivers(LineItems(**{**BASE.__dict__, "prior_revenue": 4527000.0}))
    p = tmp_path / "v1.yaml"
    write_driver_file(d, p, "test")
    assert "WARNING" in p.read_text()


# ---------------------------------------------------------------- #
# End to end through the CLI
# ---------------------------------------------------------------- #
def _write_lines(path: Path, **overrides):
    items = {**BASE.__dict__, **overrides}
    path.write_text(yaml.dump({"label": path.stem, "line_items": items}))


def test_cli_derive_then_compare(tmp_path):
    a, b = tmp_path / "l1.yaml", tmp_path / "l2.yaml"
    _write_lines(a)
    _write_lines(b, revenue=4900.0, operating_expenses=2425.0, capital_expenditure=220.0)

    assert cli.main(["derive", str(a), str(b), "--outdir", str(tmp_path / "drv")]) == 0
    v1 = tmp_path / "drv" / "v1_drivers.yaml"
    v2 = tmp_path / "drv" / "v2_drivers.yaml"
    assert v1.exists() and v2.exists()

    assert cli.main([
        "compare", str(v1), str(v2), "--outdir", str(tmp_path / "out"),
        "--models-dir", str(tmp_path / "mod"),
    ]) == 0
    assert (tmp_path / "out" / "report.html").exists()


def test_cli_derive_template(tmp_path):
    p = tmp_path / "template.yaml"
    assert cli.main(["derive", "--template", str(p)]) == 0
    assert p.exists()
    load_line_items(p)


def test_cli_derive_reports_bad_input_with_nonzero_exit(tmp_path):
    a, b = tmp_path / "l1.yaml", tmp_path / "l2.yaml"
    a.write_text(yaml.dump({"line_items": {"revenue": 1.0}}))
    _write_lines(b)
    assert cli.main(["derive", str(a), str(b), "--outdir", str(tmp_path / "d")]) == 4


# ---------------------------------------------------------------- #
# Scope boundary
# ---------------------------------------------------------------- #
def test_module_does_not_claim_to_read_filings():
    """Guards the documented boundary. Extraction from filings requires
    judgement (what counts as opex?) that cannot be made deterministically,
    and doing it with an LLM would break the determinism and auditability
    the project rests on. If someone later adds parsing here, this test
    should make them argue for it explicitly."""
    import bridgework.derive as mod

    # Scan code only — the module docstring legitimately *names* these
    # things in order to say it does not do them.
    src = Path(mod.__file__).read_text()
    body = src.split('"""', 2)[2].lower() if src.count('"""') >= 2 else src.lower()
    for forbidden in ("pdfplumber", "pypdf", "beautifulsoup", "xbrl", "sec.gov", "edgar"):
        assert forbidden not in body, f"derive.py must not parse filings; found {forbidden!r}"
    assert "does not read 10-ks" in mod.__doc__.lower()
