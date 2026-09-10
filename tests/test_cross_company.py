"""
Phase 4 — cross-company validation (Blueprint §M).

The rule under test: adding a company must require a new YAML adapter
only, never a change to src/bridgework/*.py.

Honest framing: the *mapping mechanism itself* (ingestion.load_role_map
plus the 'mapping' key handling in load_from_yaml) was a one-time change
to ingestion.py. Caterpillar exercises it across a genuine business-model
gap; Northwind was added afterwards with zero source changes, which is the
actual proof the rule holds going forward.
"""
from pathlib import Path

import pytest

from bridgework import cli
from bridgework.ingestion import BridgeworkSchemaError, load_from_yaml, load_role_map
from bridgework.model import CANONICAL_ROLES, compute_fcf

DATA = Path(__file__).parent.parent / "data"
COMPANIES = {
    "zoom": (DATA / "illustrative" / "zoom_v1_drivers.yaml", DATA / "illustrative" / "zoom_v2_drivers.yaml"),
    "caterpillar": (DATA / "caterpillar" / "cat_v1_drivers.yaml", DATA / "caterpillar" / "cat_v2_drivers.yaml"),
    "northwind": (DATA / "synthetic_retail" / "nw_v1_drivers.yaml", DATA / "synthetic_retail" / "nw_v2_drivers.yaml"),
}


# ---------------------------------------------------------------- #
# Role map mechanics
# ---------------------------------------------------------------- #
def test_role_map_covers_every_canonical_role():
    for name in ("caterpillar", "synthetic_retail"):
        rm = load_role_map(DATA / name / "mapping.yaml")
        assert set(rm) == set(CANONICAL_ROLES), f"{name} role_map does not cover the canonical roles"


def test_role_map_uses_genuinely_different_vocabulary():
    """If the adapter just restated the canonical names, this test would
    prove nothing about generalisation."""
    cat = load_role_map(DATA / "caterpillar" / "mapping.yaml")
    nw = load_role_map(DATA / "synthetic_retail" / "mapping.yaml")
    for role in CANONICAL_ROLES:
        assert cat[role] != role, f"CAT adapter did not rename {role}"
        assert nw[role] != role, f"Northwind adapter did not rename {role}"
    # And the two companies must differ from each other, not share one vocabulary
    assert cat != nw


def test_role_map_missing_role_rejected(tmp_path):
    p = tmp_path / "bad_mapping.yaml"
    p.write_text("schema_version: '1.0.0'\nrole_map:\n  revenue_prior: foo\n")
    with pytest.raises(BridgeworkSchemaError, match="missing canonical roles"):
        load_role_map(p)


def test_role_map_unknown_role_rejected(tmp_path):
    lines = ["schema_version: '1.0.0'", "role_map:"]
    lines += [f"  {r}: native_{r}" for r in CANONICAL_ROLES]
    lines.append("  invented_role: native_invented")
    p = tmp_path / "bad_mapping.yaml"
    p.write_text("\n".join(lines) + "\n")
    with pytest.raises(BridgeworkSchemaError, match="unknown roles"):
        load_role_map(p)


def test_role_map_duplicate_native_name_rejected(tmp_path):
    lines = ["schema_version: '1.0.0'", "role_map:"]
    lines += [f"  {r}: collide" for r in CANONICAL_ROLES]
    p = tmp_path / "bad_mapping.yaml"
    p.write_text("\n".join(lines) + "\n")
    with pytest.raises(BridgeworkSchemaError, match="same native name"):
        load_role_map(p)


def test_driver_file_missing_a_mapped_value_rejected(tmp_path):
    (tmp_path / "m.yaml").write_text(
        "schema_version: '1.0.0'\nrole_map:\n"
        + "\n".join(f"  {r}: n_{r}" for r in CANONICAL_ROLES) + "\n"
    )
    (tmp_path / "d.yaml").write_text(
        "schema_version: '1.0.0'\nmapping: m.yaml\ndrivers:\n  n_revenue_prior: 100.0\n"
    )
    with pytest.raises(BridgeworkSchemaError, match="missing values for"):
        load_from_yaml(tmp_path / "d.yaml")


# ---------------------------------------------------------------- #
# The rule itself
# ---------------------------------------------------------------- #
@pytest.mark.parametrize("company", list(COMPANIES))
def test_every_company_loads_through_the_same_engine(company):
    v1_path, v2_path = COMPANIES[company]
    v1 = load_from_yaml(v1_path)
    load_from_yaml(v2_path)  # must also parse cleanly through the same adapter
    assert compute_fcf(v1) == compute_fcf(v1)  # deterministic
    for role in CANONICAL_ROLES:
        assert isinstance(getattr(v1, role), float)


@pytest.mark.parametrize("company", list(COMPANIES))
def test_full_pipeline_runs_for_every_company(tmp_path, company):
    v1_path, v2_path = COMPANIES[company]
    result = cli.run_pipeline(
        str(v1_path), str(v2_path),
        output_dir=str(tmp_path / company),
        models_dir=str(tmp_path / f"{company}_models"),
        run_dia=True, run_tba=True,
    )
    assert result.sia_v1.passed and result.sia_v2.passed
    # Shapley Efficiency must hold for every company, not just Zoom
    assert result.shapley["shapley_contribution"].sum() == pytest.approx(result.total_variance, abs=1e-9)
    assert (tmp_path / company / "report.html").exists()


def test_companies_span_genuinely_different_economics():
    """The validation is only meaningful if the three companies have
    materially different financial shapes."""
    shapes = {}
    for company, (v1_path, _) in COMPANIES.items():
        v1 = load_from_yaml(v1_path)
        shapes[company] = {
            "gross_margin": 1 - v1.cogs_pct,
            "capex_intensity": v1.capex_pct,
            "nwc": v1.nwc_pct,
        }
    # Software: high gross margin, low capex. Industrial: mid margin, high capex.
    # Retail: thin margin, negative working capital.
    assert shapes["zoom"]["gross_margin"] > 0.70
    assert shapes["caterpillar"]["gross_margin"] < 0.45
    assert shapes["northwind"]["gross_margin"] < 0.30
    assert shapes["caterpillar"]["capex_intensity"] > shapes["zoom"]["capex_intensity"]
    assert shapes["northwind"]["nwc"] < 0, "retail case should carry negative working capital"


def test_negative_fcf_case_is_handled_end_to_end(tmp_path):
    """Northwind crosses FCF through zero between versions -- exercises
    sign handling across attribution, reporting and charts, which neither
    the Zoom nor Caterpillar fixture does."""
    v1_path, v2_path = COMPANIES["northwind"]
    result = cli.run_pipeline(
        str(v1_path), str(v2_path),
        output_dir=str(tmp_path / "nw"),
        models_dir=str(tmp_path / "nw_models"),
        run_dia=True, run_tba=True,
    )
    assert result.v1_fcf > 0 > result.v2_fcf, "fixture should straddle FCF = 0"
    assert result.shapley["shapley_contribution"].sum() == pytest.approx(result.total_variance, abs=1e-9)
    html = (tmp_path / "nw" / "report.html").read_text()
    assert "-$" in html  # negative currency renders with the sign outside the symbol


def test_adapter_translation_is_faithful():
    """A mapped driver file must produce exactly the Drivers object its
    native values imply -- no silent reordering or role confusion."""
    v1 = load_from_yaml(COMPANIES["caterpillar"][0])
    assert v1.revenue_prior == pytest.approx(67060.0)
    assert v1.cogs_pct == pytest.approx(0.620)
    assert v1.capex_pct == pytest.approx(0.050)


def test_canonical_files_still_load_without_a_mapping():
    """Backwards compatibility: the Zoom files carry no 'mapping' key and
    must keep working unchanged."""
    v1 = load_from_yaml(COMPANIES["zoom"][0])
    assert v1.revenue_prior == pytest.approx(4527.0)
