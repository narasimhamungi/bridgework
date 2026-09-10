# Bridgework — Model Assumptions & Data Sources

**All driver values are ILLUSTRATIVE.** The primary output (unlevered Free
Cash Flow) is not expected to reconcile to Zoom's reported non-GAAP FCF,
because the reported figure includes stock-based compensation add-backs,
interest income on Zoom's cash balance, gains on strategic investments and
other non-recurring items this compact model deliberately excludes.

## Correction applied (Blueprint Decision 1)

Earlier project documentation cited "FY2025 GAAP operating income $1,123.6M,
Zoom 8-K Feb 24 2025" as the anchor implying `opex_pct`'s "~24% GAAP
op margin." **This citation was wrong.** Independently verified against
Zoom's own filings:

- Zoom's Feb 24, 2025 release (fiscal year ended Jan 31, 2025) reports
  **GAAP operating margin of 17.4%** for FY2025.
- The $1,123.6M figure is confirmed by Zoom's Feb 25, 2026 release to be
  the **FY2026** GAAP income from operations, not FY2025. That same release
  states FY2025 GAAP income from operations was **$813.3M**.

**Corrected public anchor: FY2025 GAAP operating income = $813.3M;
FY2025 GAAP operating margin ≈ 17.4%.**

This model's `opex_pct = 52.0%` is **not** derived to match this corrected
margin. It never needs to be: this is a controlled, illustrative attribution
experiment, not a reproduction of Zoom's actual FY25 income statement. The
value was chosen (as it always was) to produce an interesting, opposing-sign
three-driver attribution case. The correction here is to the *citation*,
which previously implied a false derivation — it is retired.

## Public data anchors (context only, not derivation inputs)

| Item | Value | Source |
|---|---|---|
| FY2024 revenue (year end Jan 31 2024) | $4,527.0M | Zoom FY24 10-K (zm-20240131) |
| FY2025 revenue (year end Jan 31 2025) | ~$4,666M | Zoom FY25 10-K (zm-20250131) |
| **FY2025 GAAP operating income (corrected)** | **$813.3M** | Zoom FY26 Q4/FY earnings release (Feb 25, 2026), comparative FY25 figure |
| **FY2025 GAAP operating margin (corrected)** | **~17.4%** | Zoom FY25 earnings release (Feb 24, 2025) |
| FY2025 CapEx (property & equipment) | ~$137M | Macrotrends ZM cash flow |
| FY2025 reported FCF (non-GAAP) | $1,808.7M | Zoom FY25 8-K |

## V1 driver set (illustrative, not margin-matched)

| Driver | V1 value | Rationale |
|---|---|---|
| revenue_prior | $4,527M | FY2024 revenue anchor |
| revenue_growth | 3.1% | Illustrative FY24→FY25 growth |
| cogs_pct | 24.0% | Illustrative, ~76% gross margin |
| opex_pct | 52.0% | **Illustrative** — chosen for attribution interest, not margin-matched |
| tax_rate | 18.0% | Illustrative effective rate |
| nwc_pct | 5.0% | Illustrative NWC intensity |
| capex_pct | 3.0% | ~$137M capex on ~$4.66B revenue |

## V2 driver changes (exactly three)

| Driver | V1 | V2 | Change | Economic story |
|---|---|---|---|---|
| revenue_growth | 3.1% | 5.5% | +240bps | AI (Zoom AI Companion, Contact Center) + enterprise re-acceleration |
| opex_pct | 52.0% | 49.5% | −250bps | Operating leverage, post-COVID cost discipline holds |
| capex_pct | 3.0% | 4.5% | +150bps | AI infrastructure build-out (GPU / data-centre) |

All other drivers held constant — the cleanest experimental design for
isolating the attribution question.

## Why these three drivers

They span three economic categories (top-line, cost-side, investment-side)
and push in opposing directions — growth and opex leverage both add FCF,
capex subtracts. This is deliberately the "interesting" attribution case:
when drivers compete, ordering starts to matter and Shapley proves its
worth.

## What this model does not capture

Stock-based compensation; interest income on Zoom's cash balance; deferred
revenue mechanics; segment mix; FX effects. Taxes are a flat rate on EBIT,
not pre-tax income. These are deliberate Phase-0/Phase-1 simplifications.

## Known structural limitation

This model is bilinear — its non-additivity comes almost entirely from
revenue-growth × margin/cost interactions. It has never been tested against
a genuine nonlinearity (e.g. the `max(EBIT, 0)` tax floor actually binding).
Synthetic edge case #5 in the Blueprint (§M) exists specifically to close
this gap.
