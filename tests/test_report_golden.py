"""
Golden dataset regression (Blueprint §I): the Zoom V1/V2 fixture must
reproduce byte-exact CSV outputs on every run. Any regression here is a
hard CI failure, not a warning.
"""
from pathlib import Path

import pytest

from bridgework import cli

GOLDEN_DIR = Path(__file__).parent / "golden"
DATA_DIR = Path(__file__).parent.parent / "data" / "illustrative"

CSV_FILES = [
    "change_register.csv",
    "model_snapshot.csv",
    "ordering_sensitivity_matrix.csv",
    "pairwise_interactions.csv",
    "interaction_terms.csv",
    "sequential_vs_shapley.csv",
    "shapley_attribution.csv",
    "variance_bridge.csv",
    "variance_bridge_all_orderings.csv",
]


@pytest.fixture(scope="module")
def fresh_run(tmp_path_factory):
    outdir = tmp_path_factory.mktemp("outputs")
    modeldir = tmp_path_factory.mktemp("models")
    result = cli.run_pipeline(
        str(DATA_DIR / "zoom_v1_drivers.yaml"),
        str(DATA_DIR / "zoom_v2_drivers.yaml"),
        output_dir=str(outdir),
        models_dir=str(modeldir),
    )
    return outdir, result


@pytest.mark.parametrize("filename", CSV_FILES)
def test_golden_csv_byte_exact(fresh_run, filename):
    outdir, _ = fresh_run
    fresh = (outdir / filename).read_text()
    golden = (GOLDEN_DIR / filename).read_text()
    assert fresh == golden, f"{filename} regressed against golden dataset"


def test_golden_locked_headline_numbers(fresh_run):
    """Independent sanity check against the Blueprint §4.2 LOCKED numbers,
    not just internal consistency with the golden files."""
    _, result = fresh_run
    assert result.v1_fcf == pytest.approx(771.4949616, abs=1e-6)
    assert result.v2_fcf == pytest.approx(810.4529655, abs=1e-6)
    assert result.total_variance == pytest.approx(38.958, abs=1e-3)
