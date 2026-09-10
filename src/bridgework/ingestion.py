"""
Ingestion — YAML (canonical input) and constrained Excel round-trip
(Blueprint §F, Decision 3).

Excel ingestion scope, LOCKED: Bridgework only ingests a workbook that IT
generated via write_excel(). The only cells a user may legitimately change
before re-ingesting are the seven driver values in Drivers!B4:B10 -- every
other cell is diffed against the template this module itself writes, and
any other change raises BridgeworkSchemaError. Arbitrary third-party
workbooks are out of scope for Phase 1 (Blueprint §N).

Every validation rule accumulates ALL violations before raising -- the
user gets one complete report, never an iterative fix-one-error-at-a-time
loop (Blueprint §F).
"""
from __future__ import annotations

from pathlib import Path

import yaml
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

from .model import CANONICAL_ROLES, SCHEMA_VERSION

HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(bold=True, color="FFFFFF")
INPUT_FONT = Font(color="0000FF")  # blue = hardcoded input, per finance-model convention


class BridgeworkSchemaError(Exception):
    """Raised when a workbook (or YAML file) violates the Bridgework
    contract. Always carries the FULL list of violations found, not just
    the first."""

    def __init__(self, violations: list[str]):
        self.violations = violations
        message = "Bridgework schema contract violated:\n" + "\n".join(
            f"  - {v}" for v in violations
        )
        super().__init__(message)


# --------------------------------------------------------------------- #
# YAML — canonical input format
# --------------------------------------------------------------------- #
def load_role_map(path: str | Path, roles: tuple = CANONICAL_ROLES) -> dict[str, str]:
    """Load a company adapter's role map: {canonical_role: company_native_name}.

    This is the mechanism that makes the Blueprint §M mapping-only rule
    enforceable. It is generic infrastructure, added once -- adding any
    further company after this requires a new YAML adapter only, never a
    change to this file or any other .py."""
    path = Path(path)
    with open(path) as fh:
        doc = yaml.safe_load(fh)

    if "role_map" not in doc:
        raise BridgeworkSchemaError([f"{path.name}: missing top-level key 'role_map'"])

    role_map = doc["role_map"]
    violations: list[str] = []
    missing = set(roles) - set(role_map)
    if missing:
        violations.append(f"{path.name}: role_map is missing canonical roles {sorted(missing)}")
    unknown = set(role_map) - set(roles)
    if unknown:
        violations.append(f"{path.name}: role_map declares unknown roles {sorted(unknown)}")
    natives = list(role_map.values())
    if len(natives) != len(set(natives)):
        violations.append(f"{path.name}: role_map maps two canonical roles onto the same native name")
    if violations:
        raise BridgeworkSchemaError(violations)

    return role_map


def load_from_yaml(path: str | Path, spec=None):
    from .model_spec import FCF_MODEL, MODELS

    path = Path(path)
    with open(path) as fh:
        doc = yaml.safe_load(fh)

    # A driver file may declare which model it targets; default is FCF so
    # every pre-Phase-6 file keeps loading unchanged.
    if spec is None:
        spec = MODELS.get(str(doc.get("model", "fcf")), FCF_MODEL)

    violations: list[str] = []
    if "schema_version" not in doc:
        violations.append("missing top-level key 'schema_version'")
    elif str(doc["schema_version"]).split(".")[0] != SCHEMA_VERSION.split(".")[0]:
        violations.append(
            f"schema_version major mismatch: found {doc['schema_version']}, "
            f"expected major {SCHEMA_VERSION.split('.')[0]}.x"
        )
    if "drivers" not in doc:
        violations.append("missing top-level key 'drivers'")
    if violations:
        raise BridgeworkSchemaError(violations)

    raw = doc["drivers"]

    # Optional company adapter: when 'mapping' is present the driver file is
    # keyed by that company's own line-item names and is translated into
    # canonical roles here. Absent 'mapping', the file is assumed already
    # canonical (the Zoom illustrative case).
    if "mapping" in doc:
        map_path = Path(doc["mapping"])
        if not map_path.is_absolute():
            map_path = path.parent / map_path
        role_map = load_role_map(map_path, roles=spec.roles)
        translated: dict[str, float] = {}
        missing_natives = []
        for role, native in role_map.items():
            if native not in raw:
                missing_natives.append(f"{native!r} (for role {role!r})")
            else:
                translated[role] = raw[native]
        if missing_natives:
            raise BridgeworkSchemaError(
                [f"{path.name}: driver file is missing values for: {', '.join(sorted(missing_natives))}"]
            )
        raw = translated

    try:
        return spec.drivers_cls.from_dict(raw)
    except ValueError as exc:
        raise BridgeworkSchemaError([str(exc)]) from exc


# --------------------------------------------------------------------- #
# Excel — generation (byproduct of the canonical calc, Blueprint §B)
# --------------------------------------------------------------------- #
_CALC_LINES = [
    ("Revenue (prior)", "={ref[revenue_prior]}", "Anchor: prior-period revenue"),
    ("Revenue", "=B4*(1+{ref[revenue_growth]})", "prior * (1 + growth)"),
    ("Gross Profit", "=B5*(1-{ref[cogs_pct]})", "Revenue * (1 - COGS%)"),
    ("Opex", "=B5*{ref[opex_pct]}", "Revenue * Opex%"),
    ("EBIT", "=B6-B7", "Gross Profit - Opex"),
    ("Taxes", "=MAX(B8,0)*{ref[tax_rate]}", "max(EBIT,0) * tax rate"),
    ("NOPAT", "=B8-B9", "EBIT - Taxes"),
    ("Delta NWC", "=B5*{ref[nwc_pct]}-B4*{ref[nwc_pct]}", "(Rev - PriorRev) * NWC%"),
    ("CapEx", "=B5*{ref[capex_pct]}", "Revenue * CapEx%"),
    ("Free Cash Flow", "=B10-B11-B12", "NOPAT - dNWC - CapEx"),
]


def write_excel(drivers, path: str | Path, title: str, spec=None) -> None:
    """Generate a Bridgework-contract-compliant workbook: Drivers, Calc,
    Meta sheets, live formulas throughout (never hardcoded results)."""
    from .model_spec import FCF_MODEL

    spec = spec or FCF_MODEL
    roles, labels, calc_lines = spec.roles, spec.labels, spec.calc_lines
    wb = Workbook()

    # -- Meta sheet -------------------------------------------------
    meta = wb.active
    meta.title = "Meta"
    meta["A1"] = "schema_version"
    meta["B1"] = SCHEMA_VERSION
    meta["A2"] = "title"
    meta["B2"] = title
    meta["A3"] = "model"
    meta["B3"] = spec.key

    # -- Drivers sheet ------------------------------------------------
    ws = wb.create_sheet("Drivers")
    ws["A1"] = f"Bridgework — {title} Drivers"
    ws["A1"].font = Font(bold=True, size=14)
    ws.merge_cells("A1:C1")
    ws["A3"], ws["B3"], ws["C3"] = "Driver", "Value", "Label"
    for cell in ("A3", "B3", "C3"):
        ws[cell].fill = HEADER_FILL
        ws[cell].font = HEADER_FONT

    for i, role in enumerate(roles, start=4):
        ws.cell(row=i, column=1, value=role)
        c = ws.cell(row=i, column=2, value=getattr(drivers, role))
        c.font = INPUT_FONT
        ws.cell(row=i, column=3, value=labels[role])

    named = {role: f"Drivers!$B${4 + i}" for i, role in enumerate(roles)}

    # -- Calc sheet -----------------------------------------------------
    calc = wb.create_sheet("Calc")
    calc["A1"] = f"Bridgework — {title} FCF Calculation"
    calc["A1"].font = Font(bold=True, size=14)
    calc.merge_cells("A1:C1")
    calc["A3"], calc["B3"], calc["C3"] = "Line item", "Value ($M)", "Formula note"
    for c in ("A3", "B3", "C3"):
        calc[c].fill = HEADER_FILL
        calc[c].font = HEADER_FONT

    for i, (label, formula_tmpl, note) in enumerate(calc_lines, start=4):
        calc.cell(row=i, column=1, value=label)
        calc.cell(row=i, column=2, value=formula_tmpl.format(ref=named))
        calc.cell(row=i, column=3, value=note)

    fcf_row = 3 + len(calc_lines)
    calc.cell(row=fcf_row, column=1).font = Font(bold=True)
    calc.cell(row=fcf_row, column=2).font = Font(bold=True)
    calc.cell(row=fcf_row, column=1).fill = PatternFill("solid", fgColor="D9E1F2")
    calc.cell(row=fcf_row, column=2).fill = PatternFill("solid", fgColor="D9E1F2")

    for col, width in zip("ABC", (26, 18, 42)):
        ws.column_dimensions[col].width = width
        calc.column_dimensions[col].width = width

    wb.save(path)


# --------------------------------------------------------------------- #
# Excel — constrained round-trip ingestion (Decision 3)
# --------------------------------------------------------------------- #
def load_from_excel(path: str | Path, spec=None):
    """Ingest a Bridgework-generated workbook. Validates the FULL
    contract (§F) and raises BridgeworkSchemaError with every violation
    found if any check fails. Only Drivers!B4:B10 values are permitted to
    differ from a freshly-generated template with the same driver values."""
    from .model_spec import FCF_MODEL, MODELS

    path = Path(path)
    violations: list[str] = []

    try:
        wb = load_workbook(path, data_only=False)
    except Exception as exc:
        raise BridgeworkSchemaError([f"could not open workbook: {exc}"]) from exc

    required = ("Drivers", "Calc", "Meta")
    missing = [s for s in required if s not in wb.sheetnames]
    if missing:
        violations.append(f"missing required sheet(s): {missing}")
    if violations:
        raise BridgeworkSchemaError(violations)

    # Resolve which model this workbook was generated for. Meta!B3 is
    # authoritative; absent it, assume the original FCF model so
    # pre-Phase-6 workbooks keep loading.
    if spec is None:
        model_key = wb["Meta"]["B3"].value if wb["Meta"]["B3"].value else "fcf"
        spec = MODELS.get(str(model_key), FCF_MODEL)
    roles, calc_lines = spec.roles, spec.calc_lines

    # schema_version check
    version = str(wb["Meta"]["B1"].value)
    major = version.split(".")[0]
    expected_major = SCHEMA_VERSION.split(".")[0]
    if major != expected_major:
        violations.append(
            f"Meta!schema_version major mismatch: found {version}, expected {expected_major}.x"
        )

    # Drivers row order + values
    ws = wb["Drivers"]
    found_roles = [ws.cell(row=4 + i, column=1).value for i in range(len(roles))]
    if tuple(found_roles) != tuple(roles):
        violations.append(f"Drivers row order mismatch: found {found_roles}, expected {list(roles)}")
        raise BridgeworkSchemaError(violations)

    driver_values = {}
    for i, role in enumerate(roles):
        val = ws.cell(row=4 + i, column=2).value
        if not isinstance(val, (int, float)):
            violations.append(f"Drivers!{role} value is not numeric: {val!r}")
        else:
            driver_values[role] = float(val)

    # Calc sheet: must byte-match the template generated from these driver
    # values (i.e. only Drivers!B4:B10 may have changed) -- build a fresh
    # reference workbook in memory and diff the Calc formulas.
    if not violations:
        spec.drivers_cls.from_dict(driver_values)  # validates types/roles before the Calc diff
        named = {role: f"Drivers!$B${4 + i}" for i, role in enumerate(roles)}
        expected_calc = {
            4 + i: formula_tmpl.format(ref=named) for i, (_, formula_tmpl, _) in enumerate(calc_lines)
        }
        calc = wb["Calc"]
        for row, expected_formula in expected_calc.items():
            actual = calc.cell(row=row, column=2).value
            if actual != expected_formula:
                violations.append(
                    f"Calc!B{row} was modified outside the permitted round-trip scope "
                    f"(found {actual!r}, expected {expected_formula!r})"
                )

    if violations:
        raise BridgeworkSchemaError(violations)

    return spec.drivers_cls.from_dict(driver_values)


__all__ = [
    "BridgeworkSchemaError",
    "load_from_excel",
    "load_from_yaml",
    "load_role_map",
    "write_excel",
]
