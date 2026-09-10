# Caterpillar Inc. — Assumptions & Sources

Second-company validation case (Blueprint §M). The purpose of this dataset
is to test whether Bridgework's canonical schema generalises from a
software business (Zoom) to a heavy-industrial manufacturer **without any
change to the engine**. Adding Caterpillar required exactly one new file
type — `mapping.yaml` — and zero `.py` changes.

## Why Caterpillar

Chosen over Volvo deliberately (Blueprint Decision 5): Caterpillar and Zoom
both report in USD under US-GAAP. That isolates the variable under test —
does the *schema* generalise across business models — without
simultaneously introducing FX translation and IFRS reconciliation noise
that would contaminate the result with issues unrelated to the schema.

The vocabulary gap is real and is the point: CAT reports "sales and
revenues" not "revenue", "cost of sales" not "COGS", and splits SG&A and
R&D into separate lines that map onto one canonical `opex_pct` role.

## Reported figures (verified)

| Item | Value | Source |
|---|---:|---|
| FY2023 sales & revenues | $67,060M | CAT FY2024 10-K / Q4 FY24 release (Jan 30, 2025) |
| FY2024 sales & revenues | $64,809M | same — a 3% decrease |
| FY2024 operating profit | $13,072M | FY2024 10-K |
| FY2024 operating margin | 20.2% | FY2024 10-K (vs 19.3% in FY2023) |
| FY2024 adjusted operating margin | 20.7% | Q4 FY24 release |
| FY2024 cost of sales | ~$40.2B (~62% of revenue) | FY2024 reporting |
| FY2024 enterprise operating cash flow | $12.0B | Q4 FY24 release |

`sales_and_revenues_growth` of −3.36% is derived directly:
64,809 / 67,060 − 1.

`sga_and_rd_pct` of 17.8% is a **balancing figure**, not a reported line:
it is what reconciles a 62.0% cost-of-sales ratio to the reported 20.2%
operating margin (100% − 62.0% − 17.8% = 20.2%). It is internally
consistent with the reported margin by construction.

## Illustrative figures (NOT reported — do not cite)

`effective_tax_rate` (22.5%), `working_capital_intensity` (8.0%) and
`capex_pct_of_sales` (5.0%) are plausible-but-illustrative values chosen
to produce a well-behaved model. They were not derived from CAT filings
and should not be quoted as Caterpillar figures.

## V2 scenario

Illustrative forward case, **not a forecast**. Three drivers move in
opposing directions so the attribution problem is non-trivial: volume
recovery lifts the top line (+1.5% vs −3.4%), input-cost and tariff
pressure raises cost of sales (+180bps), and a capacity/autonomy capex
step-up subtracts from free cash flow (+120bps).

## Limitations specific to this dataset

As with the Zoom case, the computed unlevered FCF will not reconcile to
Caterpillar's reported enterprise operating cash flow: Financial Products
segment income, pension/OPEB remeasurement, restructuring, and
working-capital timing are all outside this compact model by design.
Caterpillar also carries a large captive finance arm (Cat Financial) whose
economics this 7-driver industrial model does not represent at all.
