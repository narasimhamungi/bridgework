# DCF Valuation Dataset — Assumptions

**Fully illustrative. Not a real company. No figure here should be cited.**

This dataset exists to demonstrate the attribution problem in a valuation
context, which is where it bites hardest. Unlike the Zoom and Caterpillar
datasets, there are no public anchors to verify because there is no
underlying company — the numbers are chosen to be plausible for a mid-cap
industrial and to sit in the range where DCF non-linearity is severe.

## Why this fixture is shaped the way it is

Terminal value is `FCF₅ × (1 + g) / (WACC − g)`. WACC and terminal growth
therefore interact through a *difference in a denominator*, which is
violently non-linear when the spread is tight. At V1's 7.5% WACC against
3.5% terminal growth, the spread is 400bps and the terminal value carries
**~84% of enterprise value** — above the ~75% level at which practitioners
normally flag that a valuation is mostly a perpetuity assumption rather
than a forecast.

That is deliberate. It is a realistic and common situation, and it is
exactly where a sequential variance bridge misleads most.

## Measured consequence

| | Zoom FCF model | This DCF model |
|---|---:|---:|
| L1 non-additivity | 9.9% of change | **22.7% of change** |
| Largest interacting pair | revenue × opex | **WACC × terminal growth** |
| Widest sequential ordering range | $3.86M on a $38.96M move | **$8.12/share on a $45.11 move** |

The WACC × terminal-growth interaction alone accounts for over half of
total non-additivity. An analyst walking drivers in a different order
could credit WACC with a figure $8/share different — on a stock priced
around $110.

## Model constants (not drivers)

Forecast horizon is fixed at **5 years**. It is an integer and would not
behave sensibly under Shapley coalition enumeration or continuous
sensitivity perturbation, so it is a documented model constant rather than
an attributable driver.

## Structural guard

The model refuses to compute when `WACC ≤ terminal growth`. This matters
more than it first appears: Shapley evaluates every *coalition*, so a
coalition can pair V1's WACC with V2's terminal growth and produce an
undefined model even when V1 and V2 are each individually valid. The rule
to check before comparing two versions is `min(WACC) > max(terminal
growth)` across both.

## Limitations

Unlevered FCF is taken as a given input, not built from revenue and
margins — this dataset attributes *valuation* movement, not the operating
performance underneath it. No mid-year convention, no explicit debt
schedule, no cross-check against trading comps or precedent transactions.
