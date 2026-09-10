"""
Phase 3 — HTML report tests.

Definition of done (Blueprint §K): a non-technical reviewer can read the
report and understand the V1->V2 story without opening Python. These tests
verify the structural and content properties that claim depends on.
"""
from pathlib import Path

import pytest

from bridgework import cli
from bridgework.html_report import _money, build_html_report

DATA_DIR = Path(__file__).parent.parent / "data" / "illustrative"


@pytest.fixture(scope="module")
def phase1_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("p1out")
    return cli.run_pipeline(
        str(DATA_DIR / "zoom_v1_drivers.yaml"),
        str(DATA_DIR / "zoom_v2_drivers.yaml"),
        output_dir=str(out),
        models_dir=str(tmp_path_factory.mktemp("p1mod")),
    ), out


@pytest.fixture(scope="module")
def full_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("p2out")
    return cli.run_pipeline(
        str(DATA_DIR / "zoom_v1_drivers.yaml"),
        str(DATA_DIR / "zoom_v2_drivers.yaml"),
        output_dir=str(out),
        models_dir=str(tmp_path_factory.mktemp("p2mod")),
        run_dia=True,
        run_tba=True,
    ), out


def test_money_puts_sign_outside_symbol():
    assert _money(38.958) == "+$38.96M"
    assert _money(-70.8249) == "-$70.82M"
    assert _money(0.0) == "+$0.00M"


def test_html_report_written_by_pipeline(phase1_run):
    _, out = phase1_run
    assert (out / "report.html").exists()


def test_html_is_self_contained(full_run):
    """No external asset dependencies — charts are embedded as base64, so
    the file survives being emailed or opened offline."""
    _, out = full_run
    html = (out / "report.html").read_text()
    assert "data:image/png;base64," in html
    assert 'src="dia_sobol.png"' not in html
    assert 'src="shapley_attribution.png"' not in html


def test_html_contains_the_thesis_three_answers(full_run):
    """The signature element: same driver, three different figures, with
    the order-independent one marked as the figure of record."""
    result, out = full_run
    html = (out / "report.html").read_text()
    assert "The problem this report solves" in html
    assert "the figure of record" in html
    spreads = (result.comparison["sequential_max"] - result.comparison["sequential_min"])
    focus = spreads.sort_values(ascending=False).index[0]
    assert focus in html


def test_html_states_key_numbers(full_run):
    result, out = full_run
    html = (out / "report.html").read_text()
    assert f"{result.v1_fcf:,.2f}" in html
    assert f"{result.v2_fcf:,.2f}" in html
    for driver in result.changed:
        assert driver in html


def test_html_surfaces_l1_over_net_non_additivity(full_run):
    """The report must lead the reader to the L1 figure, since the net
    figure understates ordering risk (Blueprint §4.4.A/B)."""
    _, out = full_run
    html = (out / "report.html").read_text()
    assert "Read the L1 figure, not the net figure" in html


def test_html_includes_limitations_section(full_run):
    _, out = full_run
    html = (out / "report.html").read_text()
    assert "What this does not tell you" in html
    assert "Nothing here is a forecast" in html


def test_html_includes_audit_trail(full_run):
    result, out = full_run
    html = (out / "report.html").read_text()
    assert result.manifest["input_hash"] in html
    assert "deterministic" in html.lower()


def test_html_omits_phase2_sections_when_not_run(phase1_run):
    """Phase-2 sections must not appear as empty shells when DIA/TBA
    didn't run."""
    _, out = phase1_run
    html = (out / "report.html").read_text()
    assert "Sensitivity &mdash; a different question" not in html
    # match the section heading specifically, not the limitations bullet
    # that legitimately mentions the same phrase
    assert '<h2 class="sec">Break points</h2>' not in html


def test_html_includes_phase2_sections_when_run(full_run):
    _, out = full_run
    html = (out / "report.html").read_text()
    assert "Sensitivity &mdash; a different question" in html
    assert '<h2 class="sec">Break points</h2>' in html


def test_html_surfaces_unchanged_but_risky_driver(full_run):
    """The strongest insight the tool produces: a driver that contributed
    nothing to the variance (it didn't move) but carries material output
    uncertainty. Shapley is silent on it by construction; the report must
    not be."""
    _, out = full_run
    html = (out / "report.html").read_text()
    assert "Did not change &mdash; but should be watched" in html
    assert "cogs_pct" in html


def test_html_is_deterministic_except_timestamp(full_run):
    """Two renders of the same result must be byte-identical — the report
    is a pure function of the pipeline result."""
    result, out = full_run
    a = build_html_report(result, out)
    b = build_html_report(result, out)
    assert a == b


def test_html_handles_zero_variance_without_thesis_block(tmp_path):
    """Zero-variance edge case: no ordering ambiguity exists, so the
    thesis block must be omitted rather than rendered empty."""
    result = cli.run_pipeline(
        str(DATA_DIR / "zoom_v1_drivers.yaml"),
        str(DATA_DIR / "zoom_v1_drivers.yaml"),
        output_dir=str(tmp_path / "out"),
        models_dir=str(tmp_path / "mod"),
    )
    html = (tmp_path / "out" / "report.html").read_text()
    assert result.total_variance == 0.0
    assert "The problem this report solves" not in html
    assert "<html" in html  # still a valid document


def test_html_accessibility_basics(full_run):
    _, out = full_run
    html = (out / "report.html").read_text()
    assert 'lang="en"' in html
    assert "viewport" in html
    assert "prefers-reduced-motion" in html
    assert 'alt="' in html
