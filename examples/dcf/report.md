# Bridgework — Variance Bridge Report

## Executive Conclusion

Implied share price decreased by $45.11/share (V1 $110.21/share → V2 $65.10/share) across 3 changed drivers: growth_explicit, wacc, terminal_growth. The largest single contributor is wacc at -$21.41/share (47% of variance), attributed via exact Shapley decomposition (order-independent, reconciles to the total variance to 1e-9 tolerance). L1 non-additivity is $11.25/share (24.9% of |total variance|) — this is the sum of all pairwise (and higher-order) interaction terms and never cancels, unlike the smaller net non-additivity figure (+$9.93/share). Structural integrity checks: V1 PASS, V2 PASS.

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
| V1 FCF | 110.2103 |
| V2 FCF | 65.1044 |
| **Total variance** | **-45.1058** |


## Shapley Attribution (primary, order-independent)

| driver          |   shapley_contribution |   pct_of_variance | method   |
|:----------------|-----------------------:|------------------:|:---------|
| growth_explicit |                -10.985 |            24.354 | exact    |
| wacc            |                -21.405 |            47.455 | exact    |
| terminal_growth |                -12.716 |            28.191 | exact    |


## Sequential vs Shapley (diagnostic)

| driver          |   sequential_canonical |   sequential_min |   sequential_max |   shapley |   seq_range |   seq_minus_shapley |
|:----------------|-----------------------:|-----------------:|-----------------:|----------:|------------:|--------------------:|
| growth_explicit |                -13.076 |          -13.076 |           -9.114 |   -10.985 |       3.961 |              -2.091 |
| wacc            |                -22.765 |          -25.575 |          -17.455 |   -21.405 |       8.121 |              -1.36  |
| terminal_growth |                 -9.265 |          -16.386 |           -9.265 |   -12.716 |       7.121 |               3.451 |


## Non-Additivity Diagnostics

- Net non-additivity: $+9.9315M (can partially cancel — not the recommended headline risk metric)
- L1 non-additivity: $11.2510M (24.94% of |total variance| — recommended risk metric)


Pairwise interaction terms:


| driver_a        | driver_b        |   interaction |
|:----------------|:----------------|--------------:|
| growth_explicit | wacc            |        2.4804 |
| growth_explicit | terminal_growth |        1.4809 |
| wacc            | terminal_growth |        5.6403 |


## Decision-Priority Table

| driver          |   shapley_contribution |   priority_score | method                                      |
|:----------------|-----------------------:|-----------------:|:--------------------------------------------|
| wacc            |                -21.405 |            0.959 | weighted (w1=0.5, w2=0.3, w3=0.2) (Phase 2) |
| growth_explicit |                -10.985 |            0.407 | weighted (w1=0.5, w2=0.3, w3=0.2) (Phase 2) |
| terminal_growth |                -12.716 |            0.364 | weighted (w1=0.5, w2=0.3, w3=0.2) (Phase 2) |


## Driver Impact Analysis — Tornado (local, one-way)

| driver          |   fcf_low |   fcf_high |   impact_range |
|:----------------|----------:|-----------:|---------------:|
| wacc            |    186.98 |      75.34 |         111.65 |
| terminal_growth |     93.82 |     133.55 |          39.72 |
| growth_explicit |    101.71 |     119.22 |          17.51 |


## Driver Impact Analysis — Sobol (global, variance-based)

Answers a different question than Shapley: variance contribution under an assumed input distribution (±20% uniform, Assumption #1), not the realized V1→V2 change. A driver can rank highly here even if it never changed.


| driver          |     S1 |   S1_conf |     ST |   ST_conf |   interaction_gap |
|:----------------|-------:|----------:|-------:|----------:|------------------:|
| wacc            | 0.7902 |    0.099  | 0.8393 |    0.0957 |            0.0491 |
| terminal_growth | 0.1475 |    0.0593 | 0.1875 |    0.0273 |            0.04   |
| growth_explicit | 0.0244 |    0.0159 | 0.0245 |    0.0031 |            0.0001 |


## Threshold & Break-Point Analysis (TBA)

- **growth_explicit**: FCF crosses 0 at growth_explicit = -0.3271 (monotone in [-0.5, 1.0])

- **wacc**: FCF crosses 0 at wacc = 0.3324 (monotone in [0.045, 0.4])

- **terminal_growth**: threshold undefined — target never crossed within search range [-0.2, 0.04]: 0 sign changes across 11-point grid scan. The function may be perfectly monotone here; the crossing simply lies outside this range. Widen search_range to locate it.

- **net_debt**: FCF crosses 0 at net_debt = 31552.5695 (monotone in [0.0, 500000.0])


## Audit Trail

- **dependency_fingerprint**: 8357ac0c88e6 (pandas==3.0.2;numpy==2.4.4;scipy==1.17.1;SALib==1.5.2;openpyxl==3.1.5;matplotlib==3.10.8;PyYAML==6.0.3)

- **input_hash**: 1ee5413651937c89

- **code_version**: 9291b11

- **run_timestamp_utc**: 2026-08-28T15:31:31.908402+00:00

- **python_version**: 3.12.3

- **platform**: Linux-6.18.44-fc-v22-x86_64-with-glibc2.39


## Limitations

See `docs/limitations.md` for the full register. Key items: unlevered FCF does not reconcile to reported non-GAAP FCF; model is bilinear (no nonlinear-kink case tested in this run); Shapley on a discrete V1->V2 change is not Aumann-Shapley.
