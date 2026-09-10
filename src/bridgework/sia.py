"""
Structural Integrity Analysis (SIA) — Blueprint §D, §H.

8 deterministic, mechanical checks against Bridgework's OWN controlled
schema. This is explicitly NOT a general-purpose spreadsheet auditor
(Blueprint §H honest positioning): automated tools catch roughly 27% of
seeded errors even when purpose-built (Anderson 2004, cited in Aurigemma &
Panko 2010). SIA here is narrower still -- schema/contract conformance --
and a failure halts the pipeline before any variance attribution runs
(fail-fast, hard constraint: no attribution on a structurally unverified
model).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook

from .model import CANONICAL_ROLES, SCHEMA_VERSION

REQUIRED_SHEETS = ("Drivers", "Calc", "Meta")

# Formula whitelist (Blueprint §F). Matches ANY of these tokens; a formula
# using something outside this set trips the unsupported-construct check.
_ALLOWED_FUNCS = {"MAX", "MIN", "IF", "SUM", "ABS", "ROUND"}
_BANNED_PATTERN = re.compile(
    r"\b(INDIRECT|OFFSET|NOW|TODAY|RAND|RANDBETWEEN|CELL|INFO)\b", re.IGNORECASE
)
_FUNC_PATTERN = re.compile(r"\b([A-Z]{2,})\(")


@dataclass
class CheckResult:
    check_id: int
    name: str
    passed: bool
    message: str


@dataclass
class SIAReport:
    results: list[CheckResult]

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    def summary(self) -> str:
        lines = [f"SIA: {'PASS' if self.passed else 'FAIL'} ({sum(r.passed for r in self.results)}/{len(self.results)} checks)"]
        for r in self.results:
            mark = "OK " if r.passed else "FAIL"
            lines.append(f"  [{mark}] #{r.check_id} {r.name}: {r.message}")
        return "\n".join(lines)


def run_structural_checks(workbook_path: str | Path, spec=None) -> SIAReport:
    """Run all 8 structural checks against a Bridgework-generated
    workbook. Returns an SIAReport; never raises for a normal failure (a
    failing check is data, not an exception) -- callers decide whether to
    halt the pipeline on report.passed == False."""
    from .model_spec import FCF_MODEL, MODELS

    path = Path(workbook_path)
    results: list[CheckResult] = []

    try:
        wb_formulas = load_workbook(path, data_only=False)
    except Exception as exc:  # pragma: no cover - defensive
        return SIAReport(
            [CheckResult(0, "workbook_load", False, f"Could not open workbook: {exc}")]
        )

    # Resolve the model this workbook targets so row ranges and the
    # expected driver vocabulary match it (Meta!B3, default fcf).
    if spec is None:
        try:
            key = wb_formulas["Meta"]["B3"].value or "fcf"
        except Exception:
            key = "fcf"
        spec = MODELS.get(str(key), FCF_MODEL)
    n_drivers = len(spec.roles)
    calc_first, calc_last = 4, 3 + len(spec.calc_lines)

    # --- Check 1: schema-version match ---------------------------------
    try:
        meta = wb_formulas["Meta"]
        version = str(meta["B1"].value)
        major = version.split(".")[0]
        expected_major = SCHEMA_VERSION.split(".")[0]
        ok = major == expected_major
        msg = f"found {version}, expected major {expected_major}.x"
    except (KeyError, AttributeError, ValueError, TypeError) as exc:
        ok, msg = False, f"Meta!B1 unreadable: {exc}"
    results.append(CheckResult(1, "schema_version_match", ok, msg))

    # --- Check 2: required sheets present -------------------------------
    missing_sheets = [s for s in REQUIRED_SHEETS if s not in wb_formulas.sheetnames]
    ok = not missing_sheets
    results.append(
        CheckResult(2, "required_sheets_present", ok, "all present" if ok else f"missing: {missing_sheets}")
    )
    if not ok:
        # Cannot meaningfully run the remaining sheet-dependent checks.
        return SIAReport(results)

    # --- Check 3: no hardcoded literals in Calc formula cells -----------
    calc = wb_formulas["Calc"]
    hardcoded = []
    for row in calc.iter_rows(min_row=calc_first, max_row=calc_last, min_col=2, max_col=2):
        cell = row[0]
        val = cell.value
        if val is None:
            continue
        if not (isinstance(val, str) and val.startswith("=")):
            hardcoded.append(cell.coordinate)
    ok = not hardcoded
    results.append(
        CheckResult(3, "no_hardcoded_calc_literals", ok, "all formula-driven" if ok else f"hardcoded cells: {hardcoded}")
    )

    # --- Check 4: cross-sheet reference integrity -----------------------
    drivers_ws = wb_formulas["Drivers"]
    driver_names = [drivers_ws.cell(row=4 + i, column=1).value for i in range(n_drivers)]
    broken_refs = []
    referenced = set()
    for row in calc.iter_rows(min_row=calc_first, max_row=calc_last, min_col=2, max_col=2):
        formula = row[0].value
        if isinstance(formula, str):
            for m in re.finditer(r"Drivers!\$?([A-Z]+)\$?(\d+)", formula):
                r = int(m.group(2))
                idx = r - 4  # Drivers!B4 -> driver_names[0]
                if 0 <= idx < len(driver_names):
                    referenced.add(driver_names[idx])
                else:
                    broken_refs.append(m.group(0))
    ok = not broken_refs
    results.append(
        CheckResult(4, "cross_sheet_reference_integrity", ok, "all references resolve" if ok else f"broken: {broken_refs}")
    )

    # --- Check 5: sign-convention check ---------------------------------
    driver_vals = {name: drivers_ws.cell(row=4 + i, column=2).value for i, name in enumerate(driver_names)}
    sign_issues = []
    _POSITIVE_REQUIRED = {"revenue_prior", "fcf_base", "shares_outstanding"}
    _RATE_ROLES = {
        "cogs_pct", "opex_pct", "tax_rate", "nwc_pct", "capex_pct",
        "growth_explicit", "wacc", "terminal_growth",
    }
    for role in spec.roles:
        v = driver_vals.get(role)
        if role in _POSITIVE_REQUIRED and (v is None or v <= 0):
            sign_issues.append(f"{role} must be > 0, got {v}")
        elif role in _RATE_ROLES and (v is None or not (-1.0 <= v <= 2.0)):
            sign_issues.append(f"{role}={v} outside plausible rate range [-1.0, 2.0]")
    # Model-specific structural precondition: a Gordon Growth terminal
    # value is undefined unless WACC exceeds terminal growth.
    if {"wacc", "terminal_growth"} <= set(spec.roles):
        w, g = driver_vals.get("wacc"), driver_vals.get("terminal_growth")
        if w is not None and g is not None and w <= g:
            sign_issues.append(f"WACC ({w}) must exceed terminal growth ({g}) — terminal value undefined")
    ok = not sign_issues
    results.append(
        CheckResult(5, "sign_convention_check", ok, "plausible" if ok else "; ".join(sign_issues))
    )

    # --- Check 6: row-order tie-out vs canonical schema -----------------
    ok = tuple(driver_names) == tuple(spec.roles)
    results.append(
        CheckResult(
            6,
            "row_order_tie_out",
            ok,
            "matches canonical order" if ok else f"found {driver_names}, expected {CANONICAL_ROLES}",
        )
    )

    # --- Check 7: unsupported-construct scan ----------------------------
    unsupported = []
    for row in calc.iter_rows(min_row=calc_first, max_row=calc_last, min_col=2, max_col=2):
        formula = row[0].value
        if not isinstance(formula, str):
            continue
        if _BANNED_PATTERN.search(formula):
            unsupported.append((row[0].coordinate, formula))
        for func in _FUNC_PATTERN.findall(formula):
            if func not in _ALLOWED_FUNCS:
                unsupported.append((row[0].coordinate, f"unwhitelisted function {func}"))
    ok = not unsupported
    results.append(
        CheckResult(7, "unsupported_construct_scan", ok, "clean" if ok else f"found: {unsupported}")
    )

    # --- Check 8: orphaned driver check --------------------------------
    # The Blueprint listed this and the code did not implement it -- a
    # contract/enforcement drift found in adversarial review. Every declared
    # driver must be referenced by at least one Calc formula, or it is dead
    # input that a reader would wrongly assume is live.
    orphans = [name for name in driver_names if name not in referenced]
    ok = not orphans
    results.append(
        CheckResult(
            8,
            "orphaned_driver_check",
            ok,
            "every driver is referenced in Calc" if ok else f"declared but never used: {orphans}",
        )
    )

    return SIAReport(results)


__all__ = ["REQUIRED_SHEETS", "CheckResult", "SIAReport", "run_structural_checks"]
