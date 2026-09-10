# Bridgework — Variance Bridge Report

## Executive Conclusion

Free Cash Flow increased by $38.96M (V1 $771.49M → V2 $810.45M) across 3 changed drivers: revenue_growth, opex_pct, capex_pct. The largest single contributor is opex_pct at +$96.79M (248% of variance), attributed via exact Shapley decomposition (order-independent, reconciles to the total variance to 1e-9 tolerance). L1 non-additivity is $3.86M (9.9% of |total variance|) — this is the sum of all pairwise (and higher-order) interaction terms and never cancels, unlike the smaller net non-additivity figure (+$0.60M). Structural integrity checks: V1 PASS, V2 PASS.

## Structural Integrity Findings (SIA)

```
SIA: PASS (8/8 checks)
  [OK ] #1 schema_version_match: found 1.0.0, expected major 1.x
  [OK ] #2 required_sheets_present: all present
  [OK ] #3 no_hardcoded_calc_literals: all formula-driven
  [OK ] #4 cross_sheet_reference_integrity: all references resolve
  [OK ] #5 sign_convention_check: plausible
  [OK ] #6 row_order_tie_out: matches canonical order
  [OK ] #7 unsupported_construct_scan: clean
  [OK ] #8 orphaned_driver_check: every driver is referenced in Calc
```

```
SIA: PASS (8/8 checks)
  [OK ] #1 schema_version_match: found 1.0.0, expected major 1.x
  [OK ] #2 required_sheets_present: all present
  [OK ] #3 no_hardcoded_calc_literals: all formula-driven
  [OK ] #4 cross_sheet_reference_integrity: all references resolve
  [OK ] #5 sign_convention_check: plausible
  [OK ] #6 row_order_tie_out: matches canonical order
  [OK ] #7 unsupported_construct_scan: clean
  [OK ] #8 orphaned_driver_check: every driver is referenced in Calc
```

## Primary Output Change

| | Value ($M) |
|---|---:|
| V1 FCF | 771.4950 |
| V2 FCF | 810.4530 |
| **Total variance** | **+38.9580** |


## Shapley Attribution (primary, order-independent)

| driver         |   shapley_contribution |   pct_of_variance | method   |
|:---------------|-----------------------:|------------------:|:---------|
| revenue_growth |                 12.989 |            33.341 | exact    |
| opex_pct       |                 96.794 |           248.457 | exact    |
| capex_pct      |                -70.825 |          -181.798 | exact    |


## Sequential vs Shapley (diagnostic)

| driver         |   sequential_canonical |   sequential_min |   sequential_max |   shapley |   seq_range |   seq_minus_shapley |
|:---------------|-----------------------:|-----------------:|-----------------:|----------:|------------:|--------------------:|
| revenue_growth |                 12.69  |            11.06 |           14.917 |    12.989 |       3.857 |              -0.299 |
| opex_pct       |                 97.908 |            95.68 |           97.908 |    96.794 |       2.227 |               1.114 |
| capex_pct      |                -71.64  |           -71.64 |          -70.01  |   -70.825 |       1.63  |              -0.815 |


## Non-Additivity Diagnostics

- Net non-additivity: $+0.5976M (can partially cancel — not the recommended headline risk metric)
- L1 non-additivity: $3.8570M (9.90% of |total variance| — recommended risk metric)


Pairwise interaction terms:


| driver_a       | driver_b   |   interaction |
|:---------------|:-----------|--------------:|
| revenue_growth | opex_pct   |        2.2273 |
| revenue_growth | capex_pct  |       -1.6297 |
| opex_pct       | capex_pct  |        0      |


## Decision-Priority Table

| driver         |   shapley_contribution |   priority_score | method                                      |
|:---------------|-----------------------:|-----------------:|:--------------------------------------------|
| opex_pct       |                 96.794 |            0.966 | weighted (w1=0.5, w2=0.3, w3=0.2) (Phase 2) |
| capex_pct      |                -70.825 |            0.539 | weighted (w1=0.5, w2=0.3, w3=0.2) (Phase 2) |
| revenue_growth |                 12.989 |            0.067 | weighted (w1=0.5, w2=0.3, w3=0.2) (Phase 2) |


## Driver Impact Analysis — Tornado (local, one-way)

| driver         |   fcf_low |   fcf_high |   impact_range |
|:---------------|----------:|-----------:|---------------:|
| opex_pct       |  1,169.53 |     373.46 |         796.06 |
| cogs_pct       |    955.20 |     587.79 |         367.41 |
| tax_rate       |    811.82 |     731.17 |          80.65 |
| capex_pct      |    799.50 |     743.49 |          56.01 |
| revenue_growth |    768.22 |     774.77 |           6.56 |
| nwc_pct        |    772.90 |     770.09 |           2.81 |


## Driver Impact Analysis — Sobol (global, variance-based)

Answers a different question than Shapley: variance contribution under an assumed input distribution (±20% uniform, Assumption #1), not the realized V1→V2 change. A driver can rank highly here even if it never changed.


| driver         |      S1 |   S1_conf |     ST |   ST_conf |   interaction_gap |
|:---------------|--------:|----------:|-------:|----------:|------------------:|
| opex_pct       |  0.814  |    0.0919 | 0.8139 |    0.0718 |           -0.0001 |
| cogs_pct       |  0.1738 |    0.0477 | 0.1732 |    0.02   |           -0.0006 |
| tax_rate       |  0.0085 |    0.0128 | 0.009  |    0.0012 |            0.0004 |
| capex_pct      |  0.004  |    0.0075 | 0.004  |    0.0005 |           -0      |
| revenue_growth | -0      |    0.0009 | 0.0001 |    0      |            0.0001 |
| nwc_pct        |  0      |    0.0004 | 0      |    0      |            0      |


## Threshold & Break-Point Analysis (TBA)

- **revenue_growth**: threshold undefined — target never crossed within search range [-0.95, 3.0]: 0 sign changes across 11-point grid scan. The function may be perfectly monotone here; the crossing simply lies outside this range. Widen search_range to locate it.

- **cogs_pct**: FCF crosses 0 at cogs_pct = 0.4416 (monotone in [0.0, 1.5])

- **opex_pct**: FCF crosses 0 at opex_pct = 0.7216 (monotone in [0.0, 1.5])

- **tax_rate**: FCF crosses 0 at tax_rate = 0.8687 (monotone in [0.0, 1.5])

- **nwc_pct**: threshold undefined — target never crossed within search range [0.0, 1.5]: 0 sign changes across 11-point grid scan. The function may be perfectly monotone here; the crossing simply lies outside this range. Widen search_range to locate it.

- **capex_pct**: FCF crosses 0 at capex_pct = 0.1953 (monotone in [0.0, 1.5])


## Audit Trail

- **dependency_fingerprint**: 8357ac0c88e6 (pandas==3.0.2;numpy==2.4.4;scipy==1.17.1;SALib==1.5.2;openpyxl==3.1.5;matplotlib==3.10.8;PyYAML==6.0.3)

- **input_hash**: 86b3952181645cc2

- **code_version**: 9291b11

- **run_timestamp_utc**: 2026-08-28T15:31:24.027145+00:00

- **python_version**: 3.12.3

- **platform**: Linux-6.18.44-fc-v22-x86_64-with-glibc2.39


## Limitations

See `docs/limitations.md` for the full register. Key items: unlevered FCF does not reconcile to reported non-GAAP FCF; model is bilinear (no nonlinear-kink case tested in this run); Shapley on a discrete V1->V2 change is not Aumann-Shapley.
