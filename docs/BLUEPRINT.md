# Bridgework — Master Research & Architecture Blueprint v1.0

*Produced against the Bridgework Master Execution Prompt (masterplan.pdf, §0–14). Structured per §6 (A→O). Phase 0 numbers cited, not restated. Every non-trivial decision uses the §7 DECISION format and a LOCKED/PROVISIONAL/OPEN/REJECTED tag.*

---

## A. Executive Definition

**Problem.** When a financial model's primary output changes between two versions, the standard analyst response — a one-driver-at-a-time waterfall — silently depends on the order the analyst chose to walk the drivers. On the validated Phase 0 Zoom experiment, that choice alone moves `revenue_growth`'s credited impact from +$11.06M to +$14.92M (a $3.86M swing on a $12.99M true value) with zero change to the underlying economics. The analyst ships a methodology artefact labeled as an economic finding, and nothing in a conventional Excel bridge flags that this happened.

**Primary persona: FP&A / corporate-finance analyst.** Of the three candidate personas (IB/M&A modeller, equity-research analyst, FP&A lead), FP&A is primary because version-over-version variance explanation — Actual vs. Budget, Forecast v(n) vs. v(n−1) — is FP&A's *recurring, monthly* core task, not an episodic one. Equity research explains deltas quarterly around earnings; M&A/diligence explains deltas once per deal. FP&A is the only persona whose Monday-morning job *is* this problem. Equity research and diligence are documented secondary users (§C).

**Use case.** An FP&A lead has this month's revised forecast (V2) against last month's (V1). Instead of hand-building a bridge in Excel that depends on which order they type the drivers, they run `bridgework compare v1.yaml v2.yaml` and receive: (1) a Shapley-attributed variance table that sums exactly to the total and does not depend on ordering, (2) a sequential min–max whisker per driver showing how much an arbitrary walk could have distorted the story, (3) a non-additivity flag when the drivers interact more than a documented threshold, (4) a ≤200-word deterministic executive summary ready to paste into a commentary deck.

**Value proposition.** Removes a hidden, undisclosed methodology choice from variance commentary. Replaces an order-dependent guess with an axiomatically defensible, order-independent number, and *surfaces* the interaction risk instead of hiding it inside a single ordering choice.

**Differentiation.**
| Existing tool | What it does | What it does not do |
|---|---|---|
| Excel (manual bridge) | Any ordering, any driver set | No axiomatic attribution; ordering artefact is invisible to the reader |
| Copilot for Frontier Finance / Shortcut AI | Build/fix models faster | No attribution methodology; still ships whatever bridge the user typed |
| Daloopa | Extracts filing data | No attribution, no diagnostics |
| Zebra BI / IBCS tooling | Renders a variance bridge beautifully | Visualizes whatever number it's fed; does not fix the ordering-dependence problem upstream |

Bridgework's differentiation is the pairing of (a) an axiomatically defensible, order-independent attribution engine and (b) an explicit, first-class non-additivity/model-risk diagnostic — wrapped in a controlled, reproducible, auditable calculation core. Nothing in the existing landscape ships both.

**Scope statement.**
- **In (Phase 1):** compact controlled-schema FCF model; strictly whitelisted Excel round-trip (generate → edit driver values only → re-ingest); SIA mechanical checks; exact + Monte-Carlo Shapley; sequential diagnostic; two-way interaction / non-additivity reporting; ≥30 tests; deterministic CSV/PNG outputs.
- **Out (rejected or deferred — §B):** universal Excel parser; LLM in the calculation path; sequential-only headline output; 3-statement model construction; filing-data extraction; financial-services/utilities sectors; ML/statistical long-horizon forecasting; TBA (deferred to Phase 2, conditional); dashboards/Streamlit/Power BI.

---

## B. Current State

**Phase 0 (complete, independently re-verified this session — pytest 10/10 re-run, CSVs cross-checked, Excel formulas confirmed live not hardcoded).** Locked numbers per masterplan §4.2: V1 FCF $771.4949616M, V2 FCF $810.4529655M, total variance +$38.958M. Shapley: `revenue_growth` +$12.989M (33%), `opex_pct` +$96.794M (248%), `capex_pct` −$70.825M (−182%). Sequential ranges: `revenue_growth` $11.060–$14.917M, `opex_pct` $95.680–$97.908M, `capex_pct` −$71.640 to −$70.010M. All cited verbatim from Phase 0, not recomputed.

**§4.4 corrections — status of each, applied here:**
- **A (terminology)** — Applied throughout this Blueprint: "interaction effect" is retired; "net non-additivity" (+$0.60M) and "L1 non-additivity" ($3.86M) used precisely (§D).
- **B (two-way interaction table)** — Independently recomputed this session directly from Phase 0's `coalition_values`: I(rev,opex)=+$2.2273M, I(rev,capex)=−$1.6297M, I(opex,capex)=$0.00M, three-way=$0.00M. Net non-additivity = 2.2273 − 1.6297 + 0 = **+$0.5976M** ✓ matches the reported +$0.60M. L1 = |2.2273|+|1.6297|+|0| = **$3.857M** ✓ matches the reported ~$3.86M. Both figures are confirmed correct, not merely repeated.
- **C (FY25 citation error)** — **Independently re-verified against Zoom's SEC filings this session.** The Phase 0 `assumptions.md` cites "FY2025 GAAP operating income $1,123.6M, Zoom 8-K Feb 24 2025" — this is wrong on two counts. First, Zoom's own Feb 24, 2025 release (covering FY ended Jan 31, 2025) reports **FY2025 GAAP operating margin of 17.4%**, not ~24%. Second, $1,123.6M is confirmed (via Zoom's Feb 25, 2026 release, which states income from operations was "$1,123.6 million, compared to GAAP income from operations of $813.3 million for fiscal year 2025") to be the **FY2026** figure. **Correct FY2025 GAAP operating income = $813.3M; correct FY2025 GAAP operating margin ≈ 17.4%.** This is a material correction: Phase 0's `opex_pct=52.0%` was calibrated to imply "~24% GAAP op margin," which itself was never Zoom's real FY25 figure.
  - **DECISION 1** — OPTIONS: (a) silently leave Phase 0 numbers as-is and only fix the citation text; (b) re-derive V1 to target the correct 17.4% margin and treat this as a new golden dataset, breaking comparability with masterplan §4.2's LOCKED numbers.
  - **RECOMMENDATION:** (a), with the correction fully disclosed. **WHY:** §4.2 explicitly locks the Phase-0 numbers as fixed regression-test fixtures ("must appear unchanged in the Blueprint"); Phase 0 was always labeled **illustrative**, not a reproduction of Zoom's actuals, so its internal consistency (a 7-driver toy model reconciling to itself) does not depend on the citation being correct. **TRADE-OFF:** the phrase "implies ~24% GAAP op margin" in the old `assumptions.md` is retired as misleading. **IMPLEMENTATION CONSEQUENCE:** `data/illustrative/assumptions.md` is rewritten (§L) to state the corrected FY25 figures ($813.3M, 17.4%) as the *real* public anchor, explicitly flag that `opex_pct=52.0%` is an **illustrative, not margin-matched**, input chosen to produce an interesting attribution case (as Phase 0 always intended), and stop implying a false derivation. **STATUS: LOCKED.**
- **D (30% swing framing)** — Applied: framed throughout as scenario-specific (§D, §N), never as a universal property.
- **E (bilinear caveat)** — Applied: §D's interaction methodology explicitly generalizes beyond the bilinear case (the plain and full Grabisch–Roubens pairwise formulas are shown to coincide *only because* this model's three-way term is exactly zero — not a general property; see §D).

**Classification register (extends masterplan §4.5):**

| Status | Item |
|---|---|
| **LOCKED** | Shapley (exact, 2ⁿ enumeration) as primary attribution; sequential bridge as diagnostic only; deterministic-first/LLM-second; controlled schema; Excel as byproduct-plus-constrained-round-trip (Decision 4 below); frozen `Drivers` dataclass; FAST/ICAEW/IBCS-ISO24896 as standard frame; all 10 Phase-0 tests retained; L1 + net non-additivity both reported; FCF as primary output; §4.2 numbers; corrected FY25 citation (Decision 1) |
| **PROVISIONAL** | SIA scope (Decision 5); DIA stack = SALib (Decision, §C); Caterpillar as second-company pick (Decision 8); L1 non-additivity *materiality threshold* (numeric cutoff not yet evidence-based) |
| **OPEN → RESOLVED HERE** | Excel contract (§F, fully specified); Shapley MC threshold/sample count (§G, resolved: n>8 exact-coalition cutoff, m=10,000 default); TBA phase placement (resolved: Phase 2, conditional); reporting format (resolved: HTML primary + CSV/PNG bundle, §J); canonical schema requirement (resolved: yes, required for cross-company reuse, §D) |
| **REJECTED** | Universal Excel parser; LLM-driven calculation; sequential-only headline; "Criticality Map" brand; Streamlit/Power BI in v1; building 3-statement models; filing extraction; financial-services/utilities in v1; ML forecasting; full second-company build as a Phase-1 gate (demoted to Phase-4 stretch, §M) |

**Known Phase-0 limitations carried forward:** bilinear structure only (no tax-kink or nonlinear behavior tested); 3 drivers only; unlevered FCF does not reconcile to Zoom's reported non-GAAP FCF (SBC, interest income, strategic gains excluded by design).

---

## C. Research Foundation

Every citation below is attached to a specific decision; none are decorative.

| Finding | Source | Decision it drives |
|---|---|---|
| Shapley value is the unique allocation satisfying Efficiency, Symmetry, Dummy, Additivity | Shapley, L.S. (1953), "A Value for n-Person Games," *Contributions to the Theory of Games II* | Retains Shapley as primary attribution (§D, mandatory challenge 1) |
| Aumann–Shapley values are defined for games with a continuum of players / continuously divisible participation | Aumann, R.J. & Shapley, L.S. (1974), *Values of Non-Atomic Games*, Princeton UP | Confirms Aumann–Shapley is the wrong tool here — our drivers are discrete on/off (V1-value vs V2-value), not continuously divisible (§D, challenge 1) |
| Sobol indices decompose *output variance* under an assumed *input distribution*; distinct question from a discrete two-point attribution | Sobol, I.M. (2001), "Global sensitivity indices for nonlinear mathematical models and their Monte Carlo estimates," *Math. & Computers in Simulation* 55(1-3):271-280 | Justifies keeping DIA as a *complementary*, not redundant, module (challenge 2) |
| Total-order Sobol estimator design | Saltelli et al. (2010), *Computer Physics Communications* 181(2):259-270 | DIA implementation (§G, Phase 2) |
| SALib implements Sobol/Morris/FAST in Python; sample requirement N=n(2k+2) | Herman & Usher (2017), *JOSS* 2(9):97; Iwanaga, Usher & Herman (2022), *Socio-Environmental Systems Modelling* 4:18155 | DIA library choice (§G) |
| Automated spreadsheet auditing tools caught only 27% of seeded errors in controlled tests | Anderson (2004), cited in Aurigemma & Panko, "The Detection of Human Spreadsheet Errors by Humans versus Inspection (Auditing) Software" (2010); synthesized in Panko, R.R. (2008), "Spreadsheet Errors: What We Know. What We Think We Can Do" | Caps SIA's claims (§H); SIA is a fail-fast integrity gate, not a comprehensive audit (challenge 4) |
| Individual code/spreadsheet inspection catches 50–63% of seeded errors; group inspection 70–83% | Panko, R.R. (1999), "Applying Code Inspection to Spreadsheet Testing," *JMIS* 16(2) | Supports framing SIA as a supplement to, not replacement for, human review |
| Exact Shapley requires 2ⁿ coalition evaluations; a polynomial Monte-Carlo estimator via permutation sampling converges at O(1/√m) by CLT | Castro, J., Gómez, D. & Tejada, J. (2009), "Polynomial calculation of the Shapley value based on sampling," *Computers & Operations Research* 36(5):1726-1730; refined with stratified sampling in Castro, Gómez, Molina & Tejada (2017), same journal, 82:180-188 | Shapley exact/MC switch policy and sample-count default (§G) |
| Shapley interaction index for pairs/subsets, axiomatized via linearity, dummy, symmetry | Grabisch, M. & Roubens, M. (1999), "An axiomatic approach to the concept of interaction among players in cooperative games," *International Journal of Game Theory* 28(4):547-565 | Interaction-index formalism choice (§D, challenge 11) |
| FAST Standard was the first modelling standard recognized as compliant with ICAEW's principles | ICAEW (2014), *Twenty Principles for Good Spreadsheet Practice*; ICAEW, *Financial Modelling Code*; FAST-Standard.org | Excel contract design (§F) directly encodes named ICAEW principles |
| IBCS's SUCCESS notation is now formalized as an ISO standard | ISO 24896:2026, *Notation for Business Reporting* (published June 2026, based on IBCS 2.0) | Visualisation contract (§J) — updated to cite the current ISO standard rather than the superseded IBCS 1.x-only framing |
| Banking model-risk governance: effective challenge, independent validation, documented limitations | SR 11-7 (Federal Reserve, April 4, 2011); OCC Bulletin 2011-12; SR 26-2 (revised guidance) | Model-risk framework structure (§H) — Bridgework borrows the *vocabulary and discipline* (documented limitations, effective challenge), not a claim of regulatory compliance (hard constraint 7) |

**Competing approaches considered and rejected:** Aumann–Shapley (wrong game structure, above); Möbius-only reporting without the plain-formula translation (too abstract for the target reader — retained only in the methodology appendix, §D); black-box ML-based "importance scores" (violates determinism-first principle, no axiomatic guarantee, rejected outright).

---

## D. Financial Methodology

**Model structure.** Unchanged core mechanics from Phase 0 (cited, not restated): `Revenue → Gross Profit → EBIT → Taxes (floored at EBIT≥0) → NOPAT → ΔNWC → CapEx → FCF`. For Phase 1, drivers are recategorized into a canonical taxonomy so future industry adapters map into fixed *roles* rather than the engine hardcoding driver names:

```yaml
# schema/canonical_schema.yaml (excerpt)
line_items:
  - role: revenue_driver     # e.g. revenue_growth
  - role: margin_driver      # e.g. cogs_pct
  - role: opex_driver        # e.g. opex_pct
  - role: tax_driver         # e.g. tax_rate
  - role: working_capital_driver   # e.g. nwc_pct
  - role: capex_driver       # e.g. capex_pct
primary_output: free_cash_flow
```

A company/industry adapter (`mapping_<company>.yaml`) binds its own named drivers to these roles; `model.py`'s `compute_fcf` operates only on roles, never on company-specific names. This is what makes the Caterpillar mapping-only rule (§M) enforceable.

**Variance methodology.**
- Total variance: `V2_FCF − V1_FCF`, exact by construction (§4.2).
- **Sequential bridge:** unchanged Phase-0 algorithm. Full `n!` enumeration for `n_changed ≤ 6` (720 orderings, sub-second); for `n_changed > 6`, the diagnostic display uses `k=1000` randomly sampled orderings (seeded) to build the min–max whisker, since exhaustive enumeration is no longer the reporting requirement — Shapley remains the number of record regardless.
- **Shapley:** unchanged exact-enumeration algorithm for `n_changed ≤ 8` (§G for the MC switch above 8). Efficiency axiom (`Σφᵢ = f(N) − f(∅)`) is enforced at `1e-9` tolerance, matching Phase 0's test 4.

**Interaction methodology.** Two reporting layers, both retained (challenge 11):
1. **Primary (reader-facing):** the plain pairwise term `I(i,j) = f({i,j}) − f({i}) − f({j}) + f(∅)`. Directly interpretable: "the extra dollars of FCF impact when driver *i* and driver *j* move together, beyond what each does alone." No game-theory background required.
2. **Methodology appendix (rigor-facing):** the general Grabisch–Roubens Shapley interaction index for `n>2` players, which for a pair `{i,j}` in an `n`-player game averages the plain term over every subset `S ⊆ N∖{i,j}` with combinatorial weight `|S|!(n−|S|−2)!/(n−1)!`.

**Independently verified this session:** for the Phase 0 3-driver case, both formulas coincide exactly (`I(rev,opex)=+2.2273`, `I(rev,capex)=−1.6297`, `I(opex,capex)=0.0000`) — but only because the model's true 3-way term is exactly zero. This is **not** a general property (§4.4.E caveat); at `n>3`, or wherever a genuine 3-way term exists, the two formulas diverge. **DECISION 2** — the engine (`interactions.py`) must implement the general weighted formula unconditionally, never the plain-pair shortcut, so correctness generalizes past this specific fixture. **STATUS: LOCKED.**

- **Net non-additivity** = actual variance − Σ(isolated one-at-a-time impacts) = Σ over all interaction terms (2-way + 3-way…), signed, can partially cancel. Verified: `+2.2273 − 1.6297 + 0 = +0.5976 ≈ +$0.60M`.
- **L1 non-additivity** = Σ|interaction terms|, never cancels. Verified: `|2.2273|+|1.6297|+|0| = 3.857 ≈ $3.86M`. This is the correct model-risk diagnostic (challenge 12): a model with L1 = 0 has *provably zero* ordering dependence in its sequential bridge, regardless of sign cancellation in the net figure.

**Sensitivity methodology (Phase 2, DIA):** local (tornado: one-way ±x% perturbation per driver, ranked by |ΔFCF|) and global (Sobol first-order `Sᵢ` and total-order `Sₜᵢ` via SALib, requiring an explicit input-distribution policy — default: independent uniform ±20% around each driver's V1 value, documented as Assumption #1, flagged for later validation per §11).

**Threshold methodology (TBA, Phase 2, conditional — challenge 3).** Definition: the input value of a single driver at which a defined predicate flips (e.g., `FCF < 0`). Method: `scipy.optimize.brentq` bisection. **Monotonicity precondition, mandatory:** before invoking Brent's method, the engine scans a coarse grid (11 points) across the driver's plausible range and counts sign changes in `predicate(driver_value)`. If the count ≠ 1, TBA refuses with an explicit "threshold undefined — non-monotone in search range" result rather than returning a spurious root (hard constraint: no silent fallback). This precondition exists because the tax-floor kink (`max(EBIT,0)`) makes some driver/predicate combinations genuinely non-monotone — a real risk this Blueprint does not paper over (§4.4.E).

**Structural diagnostics (SIA) — full list, each with pass/fail criterion:**

| # | Diagnostic | Pass criterion | Catches |
|---|---|---|---|
| 1 | Schema-version match | `Meta!schema_version` major version == engine's expected major version | Stale/incompatible workbooks |
| 2 | No hardcoded literals in Calc cells | Every `Calc` formula cell contains a formula string (starts with `=`) referencing `Drivers!`, never a bare numeric literal | Silent hand-edits that break the formula-driven contract |
| 3 | Orphaned driver check | Every row in `Drivers` is referenced by ≥1 formula in `Calc` | Unused/dead inputs |
| 4 | Cross-sheet reference integrity | Every `Drivers!` reference in `Calc` resolves to a real, populated cell | Broken links |
| 5 | Sign-convention check | Percent-type drivers (`*_pct`) ∈ [documented plausible range]; `revenue_prior > 0` | Obvious sign/unit errors |
| 6 | Row-order tie-out | `Drivers` sheet row order exactly matches `canonical_schema.yaml` | Silent remapping of driver meaning |
| 7 | Unsupported-construct scan | No formula matches the banned-function regex (§F) | VBA/INDIRECT/OFFSET/volatile smuggled in |
| 8 | Balance placeholder | No-op in Phase 1 (FCF-only, no balance sheet); reserved slot for when 3-statement scope is added | Forward-compatibility |

SIA failure halts the pipeline before variance attribution runs (fail-fast, hard constraint 1).

---

## E. Complete System Architecture

**Data flow:** `YAML driver files (canonical input) ⇄ Excel workbook (constrained round-trip, §Decision 4) → ingestion.py (validates against schema/excel_contract.md) → model.py (canonical calc) → sia.py (integrity gate) → variance_bridge.py + interactions.py (+ dia.py, tba.py in Phase 2) → report.py + plots.py → outputs/`

**Component boundaries and public interfaces:**
- `model.py` — `Drivers` (frozen dataclass), `compute_fcf(d: Drivers) -> float`, `compute_line_items(d: Drivers) -> dict`. No I/O.
- `ingestion.py` — `load_from_yaml(path) -> Drivers`; `load_from_excel(path) -> Drivers` (round-trip only, raises `BridgeworkSchemaError` on any contract violation, never partially recovers).
- `sia.py` — `run_structural_checks(workbook_path) -> SIAReport` (list of 8 diagnostics, each pass/fail + message).
- `variance_bridge.py` — unchanged Phase-0 `sequential_bridge`, `all_orderings`; new `shapley_attribution(v1, v2, changed, method="exact"|"monte_carlo", seed=None)`.
- `interactions.py` — `pairwise_interactions(v1, v2, changed) -> DataFrame`, `net_non_additivity(...)`, `l1_non_additivity(...)`.
- `dia.py` (Phase 2) — `sobol_indices(...)`, `tornado(...)`.
- `tba.py` (Phase 2, conditional) — `find_threshold(driver, predicate) -> float | ThresholdUndefined`.
- `report.py` — `build_report(results: PipelineResult) -> Report` (pure function of the pipeline's dataclass output; no recomputation).
- `plots.py` — one function per chart in §J's visualisation contract; all matplotlib/Agg.
- `audit.py` — `run_manifest(inputs, code_version) -> dict` (input hash, code version via `git rev-parse`, UTC timestamp, environment fingerprint).
- `cli.py` — single entry point: `bridgework compare <v1> <v2> [--method exact|mc] [--seed N]`.

**Error flow:** any contract violation raises a typed exception (`BridgeworkSchemaError`, `NonMonotoneThresholdError`, `ReconciliationError`) caught only at `cli.py`, printed as a structured, itemized failure list, non-zero exit code. No silent fallback anywhere in the calculation path (hard constraints 1, 8).

**Deliberately not a component:** no database, no API server, no frontend, no ORM, no message queue, no config-management framework beyond the YAML files themselves (anti-overengineering test, §3 principle 10).

---

## F. Excel Contract (fully specified, non-optional)

**Required sheets (exact names, case-sensitive):** `Drivers`, `Calc`, `Meta`.

**Required cells:**
- `Meta!B1` — `schema_version` string, semver (e.g. `"1.0.0"`).
- `Drivers!B4:B10` — the 7 driver values in the fixed canonical order: `revenue_prior, revenue_growth, cogs_pct, opex_pct, tax_rate, nwc_pct, capex_pct`.
- `Calc!B4:B13` — the 10 line-item formulas, unchanged from Phase 0's live-formula structure (`=Drivers!$B$4`, `=B4*(1+Drivers!$B$5)`, … `=B10-B11-B12`).

**Supported formula whitelist (exact function list):** `+ − * / MAX MIN IF SUM ABS ROUND`.

**Explicitly unsupported (fail-fast, never silently ignored):** VBA/macros; `INDIRECT`; `OFFSET`; external workbook links; Excel Tables / structured references; array (CSE) formulas; volatile functions (`NOW`, `TODAY`, `RAND`, `RANDBETWEEN`, `CELL`, `INFO`); iterative/circular calculation mode.

**Reference patterns permitted:** sheet-qualified absolute references (`Drivers!$B$4` style) only. No `INDIRECT`-constructed dynamic references.

**Schema versioning:** `Meta!schema_version` in semver; ingestion requires **major**-version match, warns (does not fail) on minor/patch mismatch.

**Validation rules and failure behaviour:** `ingestion.py` runs every rule (sheet names, required cells, formula whitelist scan) and accumulates **all** violations before raising `BridgeworkSchemaError` with the complete list — never fails on the first violation only, so the user fixes their workbook in one pass, not an iterative loop.

**DECISION 3 (Excel ingestion scope, challenge 5):**
OPTIONS CONSIDERED: (A) no Excel input at all, YAML-only; (B) Excel as unrestricted input (any schema-compliant third-party workbook); (C) Excel as regenerated output only (Phase 0's choice); (D) Excel as a **strictly constrained round-trip** — the tool generates the workbook, a user may edit only the 7 driver values in `Drivers!B4:B10`, and the tool re-ingests, validating every other cell is untouched.
**RECOMMENDATION:** D.
**WHY:** Pure output-only (C) wastes the auditability that Phase 0's own design already earns (a real analyst wants to *tweak a number in Excel and get it re-attributed*, not just view a generated file). Unrestricted input (B) reopens the universal-parser risk explicitly rejected by hard constraint 1. Round-trip (D) delivers real utility — an analyst-editable loop — while keeping the ingestion surface small enough to fully whitelist. It satisfies the roadmap's "Excel ingestion" Phase-1 requirement without violating "no universal Excel interpreter."
**TRADE-OFFS:** third-party, independently-authored workbooks (not Bridgework-generated) cannot be ingested in Phase 1 — this is explicitly deferred (OPEN, contingent on §F contract stress-testing).
**IMPLEMENTATION CONSEQUENCE:** `ingestion.py::load_from_excel` diffs every cell against the exact template the workbook was generated from; any diff outside `Drivers!B4:B10` raises `BridgeworkSchemaError`.
**STATUS: LOCKED.**

---

## G. Analytical Engine

| Module | Algorithm | Complexity | Determinism |
|---|---|---|---|
| SIA | 8 mechanical checks, §D | O(n) cells | Deterministic |
| Sequential bridge | Full permutation walk | O(n!) exact for n≤6; O(k) sampled (k=1000) for n>6 | Deterministic (seeded sampling) |
| Shapley (exact) | 2ⁿ coalition enumeration, weighted marginal sum | O(2ⁿ·n) | Deterministic |
| Shapley (Monte Carlo) | Castro–Gómez–Tejada (2009) permutation sampling | O(m·n), m samples | Seeded, reproducible |
| Interactions | Grabisch–Roubens weighted pairwise formula, §D | O(n²·2ⁿ⁻²) worst case; trivial at n≤8 | Deterministic |
| Sobol (Phase 2) | Saltelli (2010) total-order estimator via SALib | O(N(2k+2)), N base samples, k drivers | Seeded |
| Morris (Phase 2, optional pre-screen) | Elementary effects | O(r(k+1)), r trajectories | Seeded |
| TBA (Phase 2, conditional) | `scipy.optimize.brentq` + monotonicity precheck | O(log(1/ε)) per driver | Deterministic given a valid bracket |

**DECISION 4 (Shapley exact/MC switch, §7 format, challenge-adjacent):**
OPTIONS: exact-always (infeasible beyond ~20 drivers, 2²⁰≈1M evaluations becomes impractical well before that in a fully general model); MC-always (loses exactness for the compact models this tool targets); a documented switch.
RECOMMENDATION: exact for `n_changed ≤ 8` (256 coalitions, sub-millisecond); Monte Carlo above 8.
WHY: 8 is generous headroom over Phase 0's 3-driver case and over the "controlled and deliberately limited" schema philosophy (§3 principle 6) — a model that legitimately needs >8 simultaneously-changed drivers is arguably violating the compact-model design philosophy itself, so the switch is a soft signal, not just a performance cliff.
**MC sample-count default:** `m=10,000` seeded permutation samples (`seed` parameter, default `42`, always exposed per hard constraint 3), following Castro-Gómez-Tejada's O(1/√m) CLT convergence. The engine reports an **empirical 95% CI** via percentile bootstrap over the running per-permutation marginal-contribution samples (not an assumed one) — if the CI half-width exceeds 2% of `|V2−V1|`, the engine automatically doubles `m` (bounded retry ×3) and warns in the output rather than silently reporting an under-converged estimate.
STATUS: LOCKED.

**Handling of opposing-sign drivers:** percentages of variance are reported signed, uncapped (can exceed 100% or go negative), exactly as Phase 0 already does (`opex_pct` = 248%, `capex_pct` = −182%) — never forced to a positive scale (hard constraint respected; matches masterplan §4.2's own reported table).

---

## H. Model-Risk Framework

| Diagnostic | Definition | Threshold | False-pos/neg expectation | Analyst action |
|---|---|---|---|---|
| Attribution instability | Sequential range / |Shapley| per driver | Provisional: flag if >15% | False-positive on genuinely bilinear models with small totals; false-negative if only 2 orderings sampled at n>6 | Report Shapley as primary, disclose range |
| Non-additivity concentration | L1 non-additivity / |total variance| | Provisional: flag if >10% (numeric cutoff not yet evidence-based — PROVISIONAL, §11) | Understates risk if interactions cancel in a way that still confuses a sequential reader | Surface the full pairwise interaction table, not just net |
| SIA structural failure | Any of the 8 §D checks fails | Binary | 27% empirical ceiling on catching seeded errors generally (Anderson 2004) — SIA here is narrower (mechanical schema checks only), so this ceiling is a floor for concern, not a claim of coverage | Halt pipeline, do not compute attribution on a structurally unverified model |
| Sobol first-order ≪ total-order (Phase 2) | Gap indicates interaction-concentrated risk not visible to Shapley alone (different question, §C) | Provisional | N/A pre-Phase-2 | Investigate driver pair via `interactions.py` |
| Unsupported construct detected | §F whitelist violation | Binary | None (deterministic scan) | Fix workbook, re-ingest |

**Honest positioning (mandatory disclosure in README):** "SIA performs mechanical, deterministic checks against Bridgework's own controlled schema. It is not a general-purpose spreadsheet auditor and does not claim the coverage levels of professional audit software, which independent research (Anderson 2004, cited in Aurigemma & Panko 2010) found catches roughly 27% of seeded errors even when purpose-built for the task."

No arbitrary black-box "model-risk score" is produced anywhere in this design — every number above traces to an observable, reproducible model computation (hard constraint).

---

## I. Testing Architecture

**Retained from Phase 0 (10 tests, re-verified this session):** V1/V2 reproducibility; sequential reconciliation (all orderings); Shapley reconciliation (Efficiency); zero-change case; single-driver case (×3); ordering-sensitivity-is-exposed guard; Shapley symmetry axiom.

**New for Phase 1 (target ≥30 total):**
- **Mathematical invariants (new):** Shapley Dummy (driver with zero marginal contribution on every coalition ⇒ φ=0); Shapley Additivity (`φ(f+g)=φ(f)+φ(g)` on a synthetic linear-combination fixture); interaction reconciliation (`net non-additivity == Σ pairwise I(i,j) + three-way term`, verified this session to hold at `0.5976 ≈ 0.60`); L1 non-additivity ≥ |net non-additivity| always (triangle inequality, provable).
- **Ingestion (`test_ingestion.py`):** round-trip fidelity (generate → load → values match to 1e-9); schema-version major-mismatch failure; formula-whitelist violation failure (each banned function individually); non-`Drivers!B4:B10` edit rejection.
- **SIA (`test_sia.py`):** one passing + one deliberately-broken fixture per each of the 8 diagnostics (16 tests minimum).
- **Shapley MC (`test_variance_bridge.py` extension):** seeded MC estimate converges toward the exact value as `m` grows (assert monotonically shrinking |MC−exact| across `m∈{100,1000,10000}`); reported CI narrows correspondingly; same seed ⇒ byte-identical MC result across two runs.
- **TBA (`test_tba.py`, Phase 2):** non-monotone case returns `ThresholdUndefined`, never a spurious root; monotone case matches a hand-computed root within `1e-9`.
- **Golden datasets (`tests/golden/`):** byte-exact expected CSVs for the Zoom V1/V2 fixture (all 7 Phase-0 output files); any regression is a hard CI failure, not a warning.
- **Failure tests:** missing sheet; malformed named range; wrong schema-version format (non-semver string).

**Numerical tolerance:** `1e-9` for all reconciliation assertions, matching Phase 0; documented exception: Monte-Carlo Shapley tolerance is the reported CI, not `1e-9` (stochastic by nature, seeded for reproducibility).

**CI command:** `pip install -r requirements.txt && pytest tests/ -v --tb=short` — deterministic, no network, no wall-clock dependency (verified: Phase 0's `analysis.py` and `model.py` contain zero I/O in the calculation path).

---

## J. Reporting Architecture

**Artefacts (per run):** executive conclusion (≤200 words, template-generated from the numeric results — never LLM-authored, per hard constraint 2); SIA findings; headline V1→V2 change (signed, `$M`, denominator disclosed); Shapley table (signed, %-of-variance, uncapped); sequential ordering matrix; non-additivity diagnostics (net + L1 + full pairwise table); decision-priority table; audit trail (input hash via `audit.py`, code version, UTC timestamp); methodology notes; limitations (verbatim from §N).

**Decision-priority ranking formula — Phase 1 (Shapley-only, since DIA/TBA do not exist yet):**
```
priority_score(driver) = |Shapley_driver| / max_j(|Shapley_j|)
```
**Phase 2+ (once DIA exists):**
```
priority_score(driver) = w1·norm(|Shapley_i|) + w2·norm(Sobol_total_i) + w3·(1/(1+distance_to_threshold_i))
```
default weights `w1=0.5, w2=0.3, w3=0.2` (documented Assumption #2, adjustable, flagged for evidence-based calibration per §11); `norm(x)=x/max_j(x_j)` rescales each metric to [0,1] so no metric's natural scale dominates by accident. `w3` term is 0 whenever TBA has not run (e.g., non-monotone case).

**Visualisation contract (IBCS/ISO 24896:2026-aligned):**
- Variance bridge: Shapley bars as primary series, sequential min–max whisker overlaid per bar, non-additivity annotated as text (not hidden in a tooltip), signed values, single unit of measure, no truncated y-axis, source line citing the run's audit hash.
- Ordering-sensitivity chart: retained exactly as Phase 0 built it (`ordering_sensitivity.png`) — diagnostic, never the headline.
- Sobol chart (Phase 2): first-order + total-order bars per driver, side by side, so the interaction gap (`total−first`) is visually apparent.
- No 3D, no pie charts on flow data, no smoothed lines on discrete-scenario data, no decorative gradients. All charts via matplotlib `Agg` backend (headless-safe, reproducible) — no Plotly/Streamlit/Power BI in v1 (hard constraint 5, REJECTED list).

*Note on citation currency:* IBCS's SUCCESS acronym (1.x) has been superseded structurally by IBCS 2.0's Notation/Composition split, aligned with the newly published **ISO 24896:2026**. This Blueprint cites ISO 24896:2026 as the current standard reference (§C) rather than the legacy SUCCESS-only framing used in earlier Bridgework documents; the underlying chart-design rules above are unchanged in substance.

---

## K. Development Roadmap

| Phase | Content | Definition of Done | Depends on |
|---|---|---|---|
| **0 — Proof of concept** | ✅ Complete (re-verified this session) | 10/10 tests pass; README decision gate = MODIFY | — |
| **1 — Core Bridgework** | Canonical schema + role taxonomy; constrained-round-trip Excel ingestion (Decision 3); SIA (8 checks); hardened Shapley (exact + MC, Decision 4); interactions.py (Decision 2); Zoom golden dataset; ≥30 tests | All §I tests pass in CI; `bridgework compare` CLI runs end-to-end on the Zoom fixture; golden-dataset regression suite green | Phase 0 |
| **2 — Analytical engine expansion** | DIA (tornado + Sobol via SALib); two-way sensitivity heatmap; TBA *if* monotonicity precheck research holds up on ≥3 synthetic nonlinear fixtures (challenge 3, conditional) | Sobol first/total-order reported with documented input-distribution policy; TBA either ships with the monotonicity guard proven safe, or is formally deferred again with evidence | Phase 1 |
| **3 — Professional reporting** | HTML report; IBCS/ISO-24896-aligned visuals; decision-priority table (full 3-factor formula); methodology + reproducibility appendices | A non-technical reviewer can read the HTML report and understand the V1→V2 story without opening Python | Phase 1, partially Phase 2 |
| **4 — Cross-company validation** | 6 synthetic edge cases (§M) as the *primary* generalization evidence; Caterpillar mapping as a stretch goal, not a gate (Decision, challenge 10) | Zero changes to `src/bridgework/*.py` required for the Caterpillar mapping OR for any synthetic edge case; if either requires an engine change, the canonical schema is revised and this phase reruns | Phase 1 |
| **5 — Portfolio polish** | README, decision diary, methodology page, clean repo | Passes the §12 quality gate: a different competent engineer can implement from this Blueprint alone | Phases 1–4 |
| **6 — Optional LLM narrator** | Narration only, never calculation; gated on evidence of genuine incremental value | Not started; no evidence gathered yet — OPEN | Phase 5 |

---

## L. Repository Architecture

```
bridgework/
├── README.md
├── LICENSE
├── pyproject.toml                 # build + lint + test config
├── requirements.txt
├── .github/workflows/ci.yml       # install → lint → pytest, deterministic
├── data/illustrative/
│   ├── zoom_v1_drivers.yaml
│   ├── zoom_v2_drivers.yaml
│   └── assumptions.md             # corrected FY25 citation (Decision 1)
├── schema/
│   ├── excel_contract.md          # human-readable version of §F
│   └── canonical_schema.yaml      # machine-readable role taxonomy (§D)
├── models/
│   ├── zoom_v1.xlsx                # generated
│   └── zoom_v2.xlsx                # generated
├── src/bridgework/
│   ├── __init__.py
│   ├── model.py                   # canonical calc — Drivers, compute_fcf
│   ├── ingestion.py               # YAML + constrained Excel round-trip
│   ├── sia.py                     # 8 structural checks
│   ├── variance_bridge.py         # sequential + Shapley (exact + MC)
│   ├── interactions.py            # pairwise/L1/net non-additivity
│   ├── dia.py                     # Phase 2 — Sobol/Morris via SALib
│   ├── tba.py                     # Phase 2 — Brent root-find + monotonicity guard
│   ├── report.py                  # deterministic HTML/CSV reporter
│   ├── plots.py                   # matplotlib Agg charts, IBCS-aligned
│   ├── audit.py                   # input hash, run manifest
│   └── cli.py                     # single entry point
├── tests/
│   ├── test_model.py
│   ├── test_variance_bridge.py
│   ├── test_shapley_axioms.py
│   ├── test_ingestion.py
│   ├── test_sia.py
│   ├── test_dia.py                # Phase 2
│   ├── test_tba.py                # Phase 2
│   ├── test_report_golden.py
│   └── golden/                    # byte-exact expected CSVs
├── outputs/                        # gitignored, regenerated per run
└── docs/
    ├── methodology.md
    ├── decision_diary.md           # every §7-format decision in this Blueprint
    ├── limitations.md              # §N, verbatim
    └── phase_0_findings.md
```

Every file above has a one-line responsibility stated inline; nothing else is added without justifying it against §3 principle 10.

---

## M. Cross-Company Validation

**DECISION 5 (second company, challenge 10):** OPTIONS: full Volvo build; full Caterpillar build; synthetic edge cases only. RECOMMENDATION: synthetic edge cases as the *primary* Phase-1/4 generalization evidence (per masterplan's own instruction: "if small, replace with synthetic edge-case validation"); Caterpillar as an optional Phase-4 stretch, not a gate. WHY: a full second-company build is a large effort for a marginal signal beyond what a well-designed synthetic suite already proves about the schema's role-based abstraction (§D). If pursued, Caterpillar is preferred over Volvo because both Caterpillar and Zoom report in USD under US-GAAP — testing the schema's industrial-sector generalization without simultaneously introducing FX and IFRS-reconciliation noise that would contaminate the "zero code changes required" test with issues unrelated to the schema itself. STATUS: LOCKED (edge cases primary) / PROVISIONAL (Caterpillar if pursued).

**Mapping-only rule:** adding any second company must require zero changes to `src/bridgework/*.py` — only a new `mapping_<company>.yaml`. If it requires an engine change, the canonical schema (§D) has failed its generalization test and must be revised before Phase 4 is considered complete.

**Six synthetic edge cases (required, Phase 1/4):**
1. Zero variance (`V1==V2`) — Phase 0's test 5, extended to the full pipeline including SIA and reporting.
2. Single-driver change — Phase 0's test 6, extended.
3. All drivers push the same direction — new fixture; expect near-zero non-additivity if the model is close to additive in that region.
4. Drivers push opposite directions (Zoom-like) — already covered by Phase 0's actual fixture.
5. **A driver crosses the tax kink `EBIT=0`** — new fixture: construct V1/V2 where `opex_pct` is high enough that V1's EBIT < 0 and V2's EBIT > 0 (or vice versa); this directly tests the `max(EBIT,0)` non-linearity that Phase 0 never exercised (§4.4.E) and is the exact scenario TBA's monotonicity guard (§D) must correctly refuse or accept.
6. An interaction term equal in magnitude to a main effect — new fixture: choose two drivers whose two-way `I(i,j)` is deliberately calibrated (by the same technique used in Phase 0's symmetry-axiom test) to equal one driver's isolated Shapley value, stress-testing whether the reporting layer (§J) surfaces this rather than burying it under the headline number.

---

## N. Limitations (first-class artefact)

- Not a universal Excel interpreter — a strictly whitelisted, controlled-schema tool only (§F).
- Not a substitute for a full 3-statement model; FCF-only in Phase 1.
- Not a forecast — driver values are inputs supplied by the analyst, not predictions.
- Shapley on a discrete V1→V2 change is **not** Aumann–Shapley on a continuous game; the two must never be conflated (§C).
- SIA cannot catch qualitative business-logic errors; the Panko/Anderson empirical ceiling (~27% detection on seeded errors, even for purpose-built tools) applies as a floor for skepticism, not a coverage claim (§H).
- The illustrative Zoom FCF does **not** reconcile to Zoom's reported non-GAAP FCF (SBC add-back, interest income on ~$7.8B cash, strategic-investment gains, and deferred-revenue mechanics are all excluded by design).
- **New this Blueprint:** the original Phase-0 citation for FY25 GAAP operating income/margin was wrong (cited FY26's $1,123.6M/~24% instead of FY25's actual $813.3M/17.4%) — corrected in `assumptions.md` (Decision 1); the Phase-0 numerical results themselves are unaffected because they were never claimed to reproduce Zoom's actuals.
- Excel ingestion in Phase 1 is round-trip-only (Decision 3): third-party, independently-authored workbooks cannot yet be ingested.
- TBA is not present in Phase 1; its Phase-2 inclusion is conditional on the monotonicity-guard research holding up on the tax-kink edge case (§M #5).
- The L1-non-additivity "material" threshold (§H) is a provisional number, not yet evidence-calibrated across multiple scenario types.
- No claims of "verified," "audited," or "regulatory-grade" status anywhere in this project — it is a portfolio prototype; SR 11-7/IBCS/FAST/ICAEW vocabulary is borrowed for rigor and vocabulary alignment, not as a compliance claim (hard constraint 7).

---

## O. Future Extensions (evidence-gated only)

- **Multi-company canonical schema beyond Caterpillar:** deferred until the Phase-4 mapping-only rule is proven on at least one real second company; cost = one adapter file only if the schema truly generalizes, evidence = §M edge-case suite passing without engine changes.
- **LLM narrator (Phase 6):** deferred until a documented A/B comparison shows a deterministic-template executive summary is measurably less useful to a reader than an LLM-narrated one, on a sample of real FP&A reviewers — no such evidence exists yet.
- **3-statement expansion:** deferred indefinitely; explicitly rejected as a v1 direction (§B) because it recreates commodity GitHub content this project is designed to avoid.

---

*End of Bridgework — Master Research & Architecture Blueprint v1.0. Self-test per §12 applied: every algorithm has an exact function signature and file path (§E, §G); every non-trivial choice uses the §7 format (Decisions 1–5); every §8 mandatory challenge is directly answered (§A, §D, §F, §G, §M); the repository tree (§L) plus this document contain no unresolved "TBD." A competent engineer or AI receiving only this document and the Phase-0 repository should be able to implement Phase 1 without a clarifying question.*
