# Bridgework — Variance Bridge Report

## Executive Conclusion

Free Cash Flow decreased by $248.29M (V1 $95.40M → V2 -$152.88M) across 3 changed drivers: revenue_growth, cogs_pct, opex_pct. The largest single contributor is cogs_pct at -$173.09M (70% of variance), attributed via exact Shapley decomposition (order-independent, reconciles to the total variance to 1e-9 tolerance). L1 non-additivity is $4.78M (1.9% of |total variance|) — this is the sum of all pairwise (and higher-order) interaction terms and never cancels, unlike the smaller net non-additivity figure (-$4.78M). Structural integrity checks: V1 PASS, V2 PASS.

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
| V1 FCF | 95.4047 |
| V2 FCF | -152.8812 |
| **Total variance** | **-248.2859** |


## Shapley Attribution (primary, order-independent)

| driver         |   shapley_contribution |   pct_of_variance | method   |
|:---------------|-----------------------:|------------------:|:---------|
| revenue_growth |                 11.355 |            -4.573 | exact    |
| cogs_pct       |               -173.094 |            69.716 | exact    |
| opex_pct       |                -86.547 |            34.858 | exact    |


## Sequential vs Shapley (diagnostic)

| driver         |   sequential_canonical |   sequential_min |   sequential_max |   shapley |   seq_range |   seq_minus_shapley |
|:---------------|-----------------------:|-----------------:|-----------------:|----------:|------------:|--------------------:|
| revenue_growth |                 13.746 |            8.964 |           13.746 |    11.355 |       4.783 |               2.391 |
| cogs_pct       |               -174.688 |         -174.688 |         -171.5   |  -173.094 |       3.188 |              -1.594 |
| opex_pct       |                -87.344 |          -87.344 |          -85.75  |   -86.547 |       1.594 |              -0.797 |


## Non-Additivity Diagnostics

- Net non-additivity: $-4.7825M (can partially cancel — not the recommended headline risk metric)
- L1 non-additivity: $4.7825M (1.93% of |total variance| — recommended risk metric)


Pairwise interaction terms:


| driver_a       | driver_b   |   interaction |
|:---------------|:-----------|--------------:|
| revenue_growth | cogs_pct   |       -3.1884 |
| revenue_growth | opex_pct   |       -1.5942 |
| cogs_pct       | opex_pct   |        0      |


## Decision-Priority Table

| driver         |   shapley_contribution |   priority_score | method                                      |
|:---------------|-----------------------:|-----------------:|:--------------------------------------------|
| cogs_pct       |               -173.094 |            0.999 | weighted (w1=0.5, w2=0.3, w3=0.2) (Phase 2) |
| opex_pct       |                -86.547 |            0.478 | weighted (w1=0.5, w2=0.3, w3=0.2) (Phase 2) |
| revenue_growth |                 11.355 |            0.210 | weighted (w1=0.5, w2=0.3, w3=0.2) (Phase 2) |


## Driver Impact Analysis — Tornado (local, one-way)

| driver         |   fcf_low |   fcf_high |   impact_range |
|:---------------|----------:|-----------:|---------------:|
| cogs_pct       |  2,210.57 |  -2,543.28 |       4,753.85 |
| opex_pct       |    747.10 |    -617.67 |       1,364.78 |
| capex_pct      |    170.62 |      20.19 |         150.44 |
| tax_rate       |    124.29 |      66.52 |          57.77 |
| revenue_growth |     92.22 |      98.59 |           6.37 |
| nwc_pct        |     92.57 |      98.24 |           5.67 |


## Driver Impact Analysis — Sobol (global, variance-based)

Answers a different question than Shapley: variance contribution under an assumed input distribution (±20% uniform, Assumption #1), not the realized V1→V2 change. A driver can rank highly here even if it never changed.


| driver         |      S1 |   S1_conf |     ST |   ST_conf |   interaction_gap |
|:---------------|--------:|----------:|-------:|----------:|------------------:|
| cogs_pct       |  0.9085 |    0.1043 | 0.9098 |    0.0908 |            0.0013 |
| opex_pct       |  0.09   |    0.0362 | 0.0899 |    0.0101 |           -0.0001 |
| capex_pct      |  0.0009 |    0.0037 | 0.0009 |    0.0001 |           -0      |
| tax_rate       |  0.0005 |    0.0027 | 0.0008 |    0.0002 |            0.0002 |
| revenue_growth |  0      |    0.0003 | 0      |    0      |            0      |
| nwc_pct        | -0      |    0.0001 | 0      |    0      |            0      |


## Threshold & Break-Point Analysis (TBA)

- **revenue_growth**: FCF crosses 0 at revenue_growth = -0.1099 (monotone in [-0.95, 3.0])

- **cogs_pct**: FCF crosses 0 at cogs_pct = 0.7467 (monotone in [0.0, 1.5])

- **opex_pct**: FCF crosses 0 at opex_pct = 0.2347 (monotone in [0.0, 1.5])

- **tax_rate**: FCF crosses 0 at tax_rate = 0.3985 (monotone in [0.0, 1.5])

- **nwc_pct**: FCF crosses 0 at nwc_pct = 0.2007 (monotone in [0.0, 1.5])

- **capex_pct**: FCF crosses 0 at capex_pct = 0.0251 (monotone in [0.0, 1.5])


## Audit Trail

- **dependency_fingerprint**: 8357ac0c88e6 (pandas==3.0.2;numpy==2.4.4;scipy==1.17.1;SALib==1.5.2;openpyxl==3.1.5;matplotlib==3.10.8;PyYAML==6.0.3)

- **input_hash**: e0b407c920de39dc

- **code_version**: 9291b11

- **run_timestamp_utc**: 2026-08-28T15:31:29.340487+00:00

- **python_version**: 3.12.3

- **platform**: Linux-6.18.44-fc-v22-x86_64-with-glibc2.39


## Limitations

See `docs/limitations.md` for the full register. Key items: unlevered FCF does not reconcile to reported non-GAAP FCF; model is bilinear (no nonlinear-kink case tested in this run); Shapley on a discrete V1->V2 change is not Aumann-Shapley.
