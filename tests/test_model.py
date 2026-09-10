from dataclasses import replace

import pytest

from bridgework.model import CANONICAL_ROLES, Drivers, compute_fcf, compute_line_items, diff_changed_drivers

V1 = Drivers(
    revenue_prior=4527.0,
    revenue_growth=0.031,
    cogs_pct=0.240,
    opex_pct=0.520,
    tax_rate=0.180,
    nwc_pct=0.050,
    capex_pct=0.030,
)
V2 = replace(V1, revenue_growth=0.055, opex_pct=0.495, capex_pct=0.045)


def test_fcf_matches_locked_phase0_value():
    assert compute_fcf(V1) == pytest.approx(771.4949616, abs=1e-6)
    assert compute_fcf(V2) == pytest.approx(810.4529655, abs=1e-6)


def test_drivers_is_frozen():
    from dataclasses import FrozenInstanceError

    with pytest.raises(FrozenInstanceError):
        V1.revenue_growth = 0.5  # type: ignore[misc]


def test_from_dict_round_trip():
    d = Drivers.from_dict(V1.to_dict())
    assert d == V1


def test_from_dict_missing_role_raises():
    incomplete = V1.to_dict()
    del incomplete["capex_pct"]
    with pytest.raises(ValueError, match="Missing canonical driver roles"):
        Drivers.from_dict(incomplete)


def test_from_dict_unknown_role_raises():
    extra = V1.to_dict()
    extra["made_up_driver"] = 1.0
    with pytest.raises(ValueError, match="Unknown driver roles"):
        Drivers.from_dict(extra)


def test_diff_changed_drivers():
    assert diff_changed_drivers(V1, V2) == ("revenue_growth", "opex_pct", "capex_pct")


def test_diff_changed_drivers_zero_change():
    assert diff_changed_drivers(V1, V1) == ()


def test_compute_line_items_reconciles_to_fcf():
    items = compute_line_items(V1)
    assert items["Free Cash Flow"] == pytest.approx(compute_fcf(V1), abs=1e-9)


def test_canonical_roles_order_stable():
    assert CANONICAL_ROLES == (
        "revenue_prior",
        "revenue_growth",
        "cogs_pct",
        "opex_pct",
        "tax_rate",
        "nwc_pct",
        "capex_pct",
    )
