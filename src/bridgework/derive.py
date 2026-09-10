"""
Driver derivation — Phase 7.

Solves a usability problem, not an extraction problem. The barrier to using
Bridgework is not that filings are hard to parse; it is that an analyst
holding perfectly ordinary line items has to work out what
`nwc_pct = 0.05` should be. This module does that arithmetic and writes the
driver files, showing its working.

WHAT THIS DOES NOT DO, deliberately. It does not read 10-Ks, annual
reports, PDFs or XBRL. Extraction from filings is a different and much
larger problem (it is the entire product of several funded companies), and
solving it badly would mean either an LLM making judgement calls inside the
calculation path — destroying the determinism and auditability this project
rests on — or brittle heuristics that fail silently. Both red-team reviews
identified confident output on unvalidated input as the project's core
weakness; automated extraction would industrialise exactly that.

So the division of labour is explicit: **the analyst decides what the
numbers mean; this module does the arithmetic.** Deciding which lines are
operating expense, whether stock compensation belongs in them, and which
segment to model are judgements a person must make and own. Once made,
turning them into ratios is mechanical, and mechanical is what this does.

Every derived driver is reported with the formula and the inputs that
produced it, so the result is auditable rather than magic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import yaml

from .model import CANONICAL_ROLES, Drivers


class DerivationError(ValueError):
    """A line-item set cannot produce a valid driver set. Raised with the
    full list of problems, never just the first."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("Cannot derive drivers:\n" + "\n".join(f"  - {p}" for p in problems))


@dataclass(frozen=True)
class LineItems:
    """One period of ordinary financial line items, in currency units
    (use $M consistently). These are figures an analyst already has --
    from a model, a filing, a management pack, anywhere.

    `prior_revenue` is the immediately preceding period's revenue, needed
    to express growth. `net_working_capital` is the balance, not the
    movement; the movement is derived.
    """

    revenue: float
    prior_revenue: float
    cost_of_goods_sold: float
    operating_expenses: float
    tax_expense: float
    pretax_income: float
    net_working_capital: float
    capital_expenditure: float

    def validate(self) -> list[str]:
        problems: list[str] = []
        if self.revenue <= 0:
            problems.append(f"revenue must be > 0, got {self.revenue}")
        if self.prior_revenue <= 0:
            problems.append(f"prior_revenue must be > 0, got {self.prior_revenue}")
        for name in ("revenue", "prior_revenue", "cost_of_goods_sold", "operating_expenses",
                     "tax_expense", "pretax_income", "net_working_capital", "capital_expenditure"):
            v = getattr(self, name)
            if not math.isfinite(v):
                problems.append(f"{name} is not a finite number: {v}")
        return problems


@dataclass(frozen=True)
class Derivation:
    """A derived driver set plus the arithmetic that produced it."""

    drivers: Drivers
    workings: dict[str, str]
    warnings: list[str]

    def explain(self) -> str:
        lines = ["Derived drivers (each shown with the arithmetic that produced it):"]
        for role in CANONICAL_ROLES:
            lines.append(f"  {role:<16} = {getattr(self.drivers, role):>14,.6f}   {self.workings[role]}")
        if self.warnings:
            lines.append("")
            lines.append("Warnings (these are judgement calls, not errors):")
            lines.extend(f"  ! {w}" for w in self.warnings)
        return "\n".join(lines)


def derive_drivers(items: LineItems) -> Derivation:
    """Turn one period of line items into the seven canonical drivers.

    Pure arithmetic. Every ratio is a division an analyst would do by hand;
    nothing here decides what belongs in a line item.
    """
    problems = items.validate()
    if problems:
        raise DerivationError(problems)

    rev, prior = items.revenue, items.prior_revenue
    warnings: list[str] = []

    revenue_growth = rev / prior - 1.0
    cogs_pct = items.cost_of_goods_sold / rev
    opex_pct = items.operating_expenses / rev
    nwc_pct = items.net_working_capital / rev
    capex_pct = items.capital_expenditure / rev

    if items.pretax_income == 0:
        tax_rate = 0.0
        warnings.append("pretax income is zero; effective tax rate set to 0 — supply it directly if that is wrong")
    else:
        tax_rate = items.tax_expense / items.pretax_income
        if items.pretax_income < 0:
            warnings.append(
                f"pretax income is negative ({items.pretax_income:,.1f}), so the effective rate "
                f"({tax_rate:.1%}) reflects a loss position and may not describe forward taxation"
            )

    # Plausibility warnings -- surfaced, never silently corrected. A ratio
    # outside these bands is usually a units mismatch (mixing $M and $000s)
    # or a sign convention problem, and the analyst should look rather than
    # have the tool guess.
    if not -0.5 <= revenue_growth <= 3.0:
        warnings.append(f"revenue growth of {revenue_growth:.1%} is unusual — check the prior-period figure")
    if not 0.0 <= cogs_pct <= 1.0:
        warnings.append(f"COGS is {cogs_pct:.1%} of revenue — check units and sign convention")
    if not 0.0 <= opex_pct <= 1.5:
        warnings.append(f"operating expense is {opex_pct:.1%} of revenue — check units and sign convention")
    if not -0.5 <= tax_rate <= 1.0:
        warnings.append(f"effective tax rate of {tax_rate:.1%} is outside the usual range")
    if not 0.0 <= capex_pct <= 0.5:
        warnings.append(f"capex is {capex_pct:.1%} of revenue — check units")
    gross_margin = 1.0 - cogs_pct
    if gross_margin - opex_pct < -0.5:
        warnings.append(
            f"implied operating margin is {gross_margin - opex_pct:.1%} — heavily loss-making; "
            f"confirm this is intended before attributing variance"
        )

    drivers = Drivers(
        revenue_prior=prior,
        revenue_growth=revenue_growth,
        cogs_pct=cogs_pct,
        opex_pct=opex_pct,
        tax_rate=tax_rate,
        nwc_pct=nwc_pct,
        capex_pct=capex_pct,
    )

    workings = {
        "revenue_prior": f"prior-period revenue, taken directly = {prior:,.1f}",
        "revenue_growth": f"{rev:,.1f} / {prior:,.1f} - 1",
        "cogs_pct": f"{items.cost_of_goods_sold:,.1f} / {rev:,.1f}",
        "opex_pct": f"{items.operating_expenses:,.1f} / {rev:,.1f}",
        "tax_rate": f"{items.tax_expense:,.1f} / {items.pretax_income:,.1f}",
        "nwc_pct": f"{items.net_working_capital:,.1f} / {rev:,.1f}",
        "capex_pct": f"{items.capital_expenditure:,.1f} / {rev:,.1f}",
    }
    return Derivation(drivers=drivers, workings=workings, warnings=warnings)


# --------------------------------------------------------------------- #
# Template + file I/O
# --------------------------------------------------------------------- #
_TEMPLATE_FIELDS = [
    ("revenue", "Revenue for the period"),
    ("prior_revenue", "Revenue for the immediately preceding period"),
    ("cost_of_goods_sold", "Cost of revenue / cost of sales"),
    ("operating_expenses", "Operating expenses (R&D + S&M + G&A, or your definition)"),
    ("tax_expense", "Income tax expense"),
    ("pretax_income", "Income before income taxes"),
    ("net_working_capital", "Net working capital BALANCE (not the movement)"),
    ("capital_expenditure", "Purchases of property and equipment"),
]


def write_template(path: str | Path) -> None:
    """Write a blank line-items file for the analyst to fill in."""
    lines = [
        "# Bridgework line items — fill in one file per version, then run:",
        "#   bridgework derive v1_lines.yaml v2_lines.yaml",
        "#",
        "# Use consistent currency units throughout (millions is conventional).",
        "# These are figures you already have. Bridgework does not read filings:",
        "# deciding what belongs in each line is your judgement, not the tool's.",
        "",
        'label: "V1 (Baseline)"',
        "line_items:",
    ]
    for name, desc in _TEMPLATE_FIELDS:
        lines.append(f"  {name}: 0.0   # {desc}")
    Path(path).write_text("\n".join(lines) + "\n")


def load_line_items(path: str | Path) -> tuple[LineItems, str]:
    """Read a line-items file. Returns (items, label)."""
    path = Path(path)
    with open(path) as fh:
        doc = yaml.safe_load(fh) or {}
    if "line_items" not in doc:
        raise DerivationError([f"{path.name}: missing top-level key 'line_items'"])
    raw = doc["line_items"]
    expected = {name for name, _ in _TEMPLATE_FIELDS}
    missing = sorted(expected - set(raw))
    unknown = sorted(set(raw) - expected)
    problems = []
    if missing:
        problems.append(f"{path.name}: missing line items {missing}")
    if unknown:
        problems.append(f"{path.name}: unknown line items {unknown}")
    if problems:
        raise DerivationError(problems)
    items = LineItems(**{k: float(raw[k]) for k in expected})
    return items, str(doc.get("label", path.stem))


def write_driver_file(derivation: Derivation, path: str | Path, label: str) -> None:
    """Write a Bridgework driver file, with the derivation recorded inline
    so the result stays auditable rather than appearing from nowhere."""
    d = derivation.drivers
    lines = [
        f"# Derived from line items by `bridgework derive`. Label: {label}",
        "# Each driver's arithmetic is recorded beside it. Review before use —",
        "# the derivation is mechanical, but what belongs in each line item",
        "# was your judgement.",
    ]
    if derivation.warnings:
        lines.append("#")
        lines += [f"# WARNING: {w}" for w in derivation.warnings]
    lines += ['schema_version: "1.0.0"', f'label: "{label}"', "drivers:"]
    for role in CANONICAL_ROLES:
        lines.append(f"  {role}: {getattr(d, role)!r}   # {derivation.workings[role]}")
    Path(path).write_text("\n".join(lines) + "\n")


__all__ = [
    "Derivation",
    "DerivationError",
    "LineItems",
    "derive_drivers",
    "load_line_items",
    "write_driver_file",
    "write_template",
]
