# Bridgework — Variance Bridge Report

## Executive Conclusion

Free Cash Flow decreased by $1,679.78M (V1 $7,085.42M → V2 $5,405.64M) across 3 changed drivers: revenue_growth, cogs_pct, capex_pct. The largest single contributor is cogs_pct at -$926.79M (55% of variance), attributed via exact Shapley decomposition (order-independent, reconciles to the total variance to 1e-9 tolerance). L1 non-additivity is $84.57M (5.0% of |total variance|) — this is the sum of all pairwise (and higher-order) interaction terms and never cancels, unlike the smaller net non-additivity figure (-$84.57M). Structural integrity checks: V1 PASS, V2 PASS.

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
| V1 FCF | 7,085.4201 |
| V2 FCF | 5,405.6395 |
| **Total variance** | **-1,679.7806** |


## Shapley Attribution (primary, order-independent)

| driver         |   shapley_contribution |   pct_of_variance | method   |
|:---------------|-----------------------:|------------------:|:---------|
| revenue_growth |                 44.242 |            -2.634 | exact    |
| cogs_pct       |               -926.787 |            55.173 | exact    |
| capex_pct      |               -797.236 |            47.461 | exact    |


## Sequential vs Shapley (diagnostic)

| driver         |   sequential_canonical |   sequential_min |   sequential_max |   shapley |   seq_range |   seq_minus_shapley |
|:---------------|-----------------------:|-----------------:|-----------------:|----------:|------------:|--------------------:|
| revenue_growth |                 86.53  |            1.955 |           86.53  |    44.242 |      84.574 |              42.287 |
| cogs_pct       |               -949.519 |         -949.519 |         -904.055 |  -926.787 |      45.465 |             -22.732 |
| capex_pct      |               -816.791 |         -816.791 |         -777.681 |  -797.236 |      39.109 |             -19.555 |


## Non-Additivity Diagnostics

- Net non-additivity: $-84.5741M (can partially cancel — not the recommended headline risk metric)
- L1 non-additivity: $84.5741M (5.03% of |total variance| — recommended risk metric)


Pairwise interaction terms:


| driver_a       | driver_b   |   interaction |
|:---------------|:-----------|--------------:|
| revenue_growth | cogs_pct   |      -45.4647 |
| revenue_growth | capex_pct  |      -39.1094 |
| cogs_pct       | capex_pct  |        0      |


## Decision-Priority Table

| driver         |   shapley_contribution |   priority_score | method                                      |
|:---------------|-----------------------:|-----------------:|:--------------------------------------------|
| cogs_pct       |               -926.787 |            0.975 | weighted (w1=0.5, w2=0.3, w3=0.2) (Phase 2) |
| capex_pct      |               -797.236 |            0.614 | weighted (w1=0.5, w2=0.3, w3=0.2) (Phase 2) |
| revenue_growth |                 44.242 |            0.024 | weighted (w1=0.5, w2=0.3, w3=0.2) (Phase 2) |


## Driver Impact Analysis — Tornado (local, one-way)

| driver         |   fcf_low |   fcf_high |   impact_range |
|:---------------|----------:|-----------:|---------------:|
| cogs_pct       | 13,313.35 |     857.49 |      12,455.86 |
| opex_pct       |  8,873.44 |   5,297.40 |       3,576.04 |
| capex_pct      |  7,733.49 |   6,437.35 |       1,296.14 |
| tax_rate       |  7,674.51 |   6,496.33 |       1,178.19 |
| nwc_pct        |  7,049.37 |   7,121.47 |          72.10 |
| revenue_growth |  7,097.38 |   7,073.46 |          23.93 |


## Driver Impact Analysis — Sobol (global, variance-based)

Answers a different question than Shapley: variance contribution under an assumed input distribution (±20% uniform, Assumption #1), not the realized V1→V2 change. A driver can rank highly here even if it never changed.


| driver         |     S1 |   S1_conf |     ST |   ST_conf |   interaction_gap |
|:---------------|-------:|----------:|-------:|----------:|------------------:|
| cogs_pct       | 0.9059 |    0.1033 | 0.9055 |    0.0891 |           -0.0004 |
| opex_pct       | 0.0751 |    0.0333 | 0.0747 |    0.0084 |           -0.0004 |
| capex_pct      | 0.0098 |    0.0118 | 0.0098 |    0.001  |           -0      |
| tax_rate       | 0.008  |    0.0116 | 0.0089 |    0.0013 |            0.0009 |
| nwc_pct        | 0      |    0.0006 | 0      |    0      |            0      |
| revenue_growth | 0      |    0.0005 | 0      |    0      |            0      |


## Threshold & Break-Point Analysis (TBA)

- **revenue_growth**: threshold undefined — target never crossed within search range [-0.95, 3.0]: 0 sign changes across 11-point grid scan. The function may be perfectly monotone here; the crossing simply lies outside this range. Widen search_range to locate it.

- **cogs_pct**: FCF crosses 0 at cogs_pct = 0.7611 (monotone in [0.0, 1.5])

- **opex_pct**: FCF crosses 0 at opex_pct = 0.3191 (monotone in [0.0, 1.5])

- **tax_rate**: FCF crosses 0 at tax_rate = 0.7662 (monotone in [0.0, 1.5])

- **nwc_pct**: threshold undefined — target never crossed within search range [0.0, 1.5]: 0 sign changes across 11-point grid scan. The function may be perfectly monotone here; the crossing simply lies outside this range. Widen search_range to locate it.

- **capex_pct**: FCF crosses 0 at capex_pct = 0.1593 (monotone in [0.0, 1.5])


## Audit Trail

- **dependency_fingerprint**: 8357ac0c88e6 (pandas==3.0.2;numpy==2.4.4;scipy==1.17.1;SALib==1.5.2;openpyxl==3.1.5;matplotlib==3.10.8;PyYAML==6.0.3)

- **input_hash**: 7cc371077b760a80

- **code_version**: 9291b11

- **run_timestamp_utc**: 2026-08-28T15:31:26.615630+00:00

- **python_version**: 3.12.3

- **platform**: Linux-6.18.44-fc-v22-x86_64-with-glibc2.39


## Limitations

See `docs/limitations.md` for the full register. Key items: unlevered FCF does not reconcile to reported non-GAAP FCF; model is bilinear (no nonlinear-kink case tested in this run); Shapley on a discrete V1->V2 change is not Aumann-Shapley.
