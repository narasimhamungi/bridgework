# Bridgework — Decision Diary

Every non-trivial architectural choice, in the Blueprint's DECISION format.
Full rationale in the Master Research & Architecture Blueprint v1.0; this
is the repo-local reference.

---

### Decision 1 — FY25 citation correction
**Options:** (a) fix the citation only, keep Phase-0 numbers unchanged; (b) re-derive V1 to match the corrected 17.4% margin.
**Chosen:** (a).
**Why:** Phase 0's numbers are locked regression fixtures; the model was always labeled illustrative, not a reproduction of Zoom's actuals. Re-deriving would break comparability for no accuracy gain.
**Status:** LOCKED. See `data/illustrative/assumptions.md`.

---

### Decision 2 — General vs. plain pairwise interaction formula
**Options:** (a) plain shortcut `f({i,j})-f({i})-f({j})+f(∅)`; (b) general Grabisch–Roubens (1999) weighted formula.
**Chosen:** (b), unconditionally.
**Why:** The two formulas coincide only when the model's three-way (and higher) term is exactly zero — a property of the Phase-0 bilinear fixture, not a general one. Implementing (a) directly would silently produce wrong numbers on any model with genuine higher-order interaction (e.g. one that crosses the `MAX(EBIT,0)` tax kink).
**Status:** LOCKED. Verified in `tests/test_shapley_axioms.py`.

---

### Decision 3 — Excel ingestion scope
**Options:** (a) no Excel input, YAML-only; (b) unrestricted third-party workbook ingestion; (c) output-only (Phase 0's choice); (d) constrained round-trip.
**Chosen:** (d).
**Why:** (c) wastes real utility (an analyst wants to tweak a number and re-run); (b) reopens the universal-parser risk explicitly rejected as a hard constraint. (d) delivers the analyst-editable loop while keeping the ingestion surface fully whitelistable.
**Trade-off:** third-party, independently-authored workbooks cannot be ingested in Phase 1 — explicitly deferred.
**Status:** LOCKED. Implemented in `ingestion.py`; enforced by diffing every non-driver cell against the exact template.

---

### Decision 4 — Shapley exact/Monte-Carlo switch
**Options:** exact-always; Monte-Carlo-always; a documented threshold.
**Chosen:** exact for `n_changed ≤ 8` (256 coalitions); Monte Carlo above that.
**Why:** 8 is generous headroom over the compact-model design philosophy — a model needing more than 8 simultaneously-changed drivers is arguably violating "controlled and deliberately limited" scope on its own terms.
**Implementation:** default `m=10,000` seeded permutation samples (Castro–Gómez–Tejada, 2009); empirical 95% bootstrap CI; auto-doubles `m` (up to 3 retries) if CI half-width exceeds 2% of `|total variance|`.
**Status:** LOCKED. Implemented in `variance_bridge.py`.

---

### Decision 5 — Second-company validation strategy
**Options:** full Volvo build; full Caterpillar build; synthetic edge cases only.
**Chosen:** 6 synthetic edge cases as primary evidence (Phase 1/4); Caterpillar mapping as an optional Phase-4 stretch, not a gate.
**Why:** a full second-company build is a large effort for a marginal signal beyond what the role-based canonical schema already proves via edge cases. If pursued, Caterpillar over Volvo: both Caterpillar and Zoom report in USD/US-GAAP, avoiding FX/IFRS noise that would contaminate the "zero code changes" test.
**Status:** LOCKED (edge cases primary) / PROVISIONAL (Caterpillar if pursued). All 6 synthetic edge cases implemented and passing in `tests/test_synthetic_edge_cases.py`. Caterpillar mapping itself is not built in Phase 1 (see `docs/limitations.md`).

---

### Decision 6 — TBA inclusion (Phase 2 conditional, now resolved)
**Blueprint status:** conditional on "the monotonicity-guard research holding up on ≥3 synthetic nonlinear fixtures."
**Resolved: ship it.**
**Why:** the guard is implemented and tested against both failure modes (0 crossings, ≥2 crossings), and `test_fcf_is_provably_single_driver_monotone` establishes something stronger than the Blueprint anticipated — for this model, single-driver FCF is provably monotone in every canonical driver, including across the `MAX(EBIT,0)` tax kink, because each driver enters through at most a two-piece piecewise-linear relationship with same-sign slopes. So TBA is safe *by construction* here, and the guard is insurance for the general case.
**Trade-off:** TBA reports single-driver thresholds only; multi-driver break surfaces are out of scope.
**Status:** LOCKED (shipped in `tba.py`).

---

### Decision 7 — Phase-2 stages opt-in, not default
**Options:** (a) DIA/TBA always run; (b) opt-in via `--dia` / `--tba` / `--full`.
**Chosen:** (b).
**Why:** three reasons. DIA is materially compute-heavier (Sobol needs `N(2k+2)` model evaluations). TBA requires a documented default search range (Assumption #3) that will not suit every model. And keeping them off by default guarantees the Phase-1 golden dataset stays byte-identical — a regression-safety property worth preserving, verified by `test_phase2_does_not_change_phase1_numbers`.
**Status:** LOCKED.

---

### Decision 8 — TBA failure-mode messaging
**Problem found during Phase-2 integration testing:** the initial implementation reported "non-monotone in search range" for *both* the zero-crossing and multiple-crossing cases. That is wrong for the zero case: no crossing in range says nothing about monotonicity, and the function may be perfectly monotone with the root simply outside the bounds.
**Chosen:** distinct diagnoses — zero crossings advises **widening** the range, multiple crossings advises **narrowing** it.
**Why:** the two failure modes have opposite corrective actions. Conflating them would send an analyst the wrong way. Locked in by `test_zero_and_multiple_crossings_give_distinct_diagnoses`.
**Status:** LOCKED.

---

### Decision 9 — Report medium: static HTML, not a dashboard
**Options:** (a) markdown only; (b) Streamlit/Power BI dashboard; (c) self-contained static HTML.
**Chosen:** (c).
**Why:** the Blueprint rejects dashboards outright (hard constraint 5, REJECTED list) and the reason holds up: a variance workpaper needs to be *archivable* — attached to a close file, emailed to a reviewer, opened in two years to answer "why did we say that?". A dashboard is a live surface that cannot be archived; markdown alone cannot carry charts. Static HTML with base64-embedded charts satisfies both, with zero runtime dependencies.
**Trade-off:** no interactivity, no cross-run comparison.
**Status:** LOCKED (`html_report.py`).

---

### Decision 10 — The report leads with the ordering problem, not the headline number
**Options:** (a) conventional structure — headline variance, then driver table, then diagnostics; (b) lead with the thesis: the same driver shown with three different figures depending on method.
**Chosen:** (b).
**Why:** (a) is the format that *creates* the problem this tool exists to solve — it presents one number as if it were the only possible answer. Opening with the three-way contrast makes the reader understand within seconds why an order-independent figure is needed, before any table asks them to trust one. The design follows the argument rather than convention.
**Status:** LOCKED. Verified by `test_html_contains_the_thesis_three_answers`.

---

### Decision 11 — Cross-company validation: the mapping mechanism vs the mapping-only rule
**The Blueprint rule (§M):** adding a company must require zero changes to `src/bridgework/*.py`.
**The honest complication:** the *mechanism* that makes company-native naming possible (`ingestion.load_role_map` plus `mapping:` handling in `load_from_yaml`) is itself a change to `ingestion.py`. The rule cannot be satisfied by a codebase that has no mapping layer at all.
**Chosen:** build the mechanism once as generic infrastructure, then prove the rule with a *third* company added afterwards.
**Why:** this is the only version of the test that actually proves anything. Caterpillar alone would prove the mechanism works; it would not prove that the *next* company needs no code. Northwind was added after the mechanism landed and required exactly three YAML files and zero source changes — verified mechanically with `git status --porcelain src/` returning empty.
**Status:** LOCKED. Covered by `tests/test_cross_company.py`.

---

### Decision 12 — Caterpillar over Volvo (confirming Blueprint Decision 5)
**Confirmed on execution.** Both Caterpillar and Zoom report in USD under US-GAAP, which isolates the variable actually under test — whether the *schema* generalises across business models — without simultaneously introducing FX translation and IFRS reconciliation noise. A failure with Volvo would have been ambiguous between "the schema doesn't generalise" and "currency/standard differences broke it."
**Status:** LOCKED.

---

### Decision 13 — A third, synthetic company with inverted economics
**Options:** (a) stop at two real companies; (b) add a third real company; (c) add a synthetic company with a deliberately opposite financial shape.
**Chosen:** (c) — Northwind Grocery, a thin-margin, high-turnover retailer with **negative working capital**.
**Why:** the point of the third case is to prove the mapping-only rule and to stress the schema's range, neither of which requires real filings. Synthetic also allows deliberately engineering a case neither real company provides: FCF that crosses through zero between versions, which exercises sign handling across attribution, charts and the HTML report. Clearly labelled synthetic throughout so no figure can be mistaken for a real company's.
**Status:** LOCKED.

---

### Decision 14 — Add DCF valuation attribution (Phase 6)
**Options:** (a) stay FP&A-only; (b) add a DCF valuation model; (c) build three-statement + LBO + merger models to serve IB/M&A properly.
**Chosen:** (b).
**Why:** tested before deciding rather than assuming. A DCF is severely non-linear because terminal value divides by (WACC − g), so measured L1 non-additivity is **22.7% of the change versus 9.9%** on the FCF fixture, and WACC's sequential ordering range is **$8.12/share on a $45.11 move**. The DCF does not merely broaden the tool — it demonstrates the core thesis better than the original fixture does. That is unusual: broadening scope normally weakens a thesis.
**Why not (c):** a full three-statement/LBO/merger build is a different project (4–8 weeks) and would put this in direct competition with the thousands of commodity DCF/LBO repositories the masterplan explicitly rejects. It would dilute the one thing that makes this distinctive.
**Trade-off, stated plainly:** this makes the project *legible* to IB and equity research. It does not demonstrate IB modelling craft — no debt schedules, no purchase price allocation, no accretion/dilution, no comps.
**Status:** LOCKED.

---

### Decision 15 — Model registry rather than a generic driver container
**Options:** (a) rewrite `Drivers` as a generic dict-backed container validated against a schema; (b) keep frozen per-model dataclasses and thread a `model_fn` through the engine, with a `ModelSpec` registry for pipeline-level concerns.
**Chosen:** (b).
**Why:** the engine already used `dataclasses.replace` and `getattr`, which work on *any* frozen dataclass — it was nearly model-agnostic already and only the direct `compute_fcf` import coupled it. Option (a) would have touched the Excel contract, the golden dataset and every company adapter for no functional gain. Option (b) kept all 125 pre-existing tests passing unchanged, including byte-exact golden-dataset regression, at every step of the refactor.
**Status:** LOCKED (`model_spec.py`).

---

### Decision 16 — Guard the DCF against invalid Shapley coalitions
**Problem found while building:** `WACC ≤ terminal growth` makes a Gordon Growth terminal value undefined. The non-obvious part is that Shapley evaluates every coalition, so a *mix* of two individually-valid versions can be invalid — V1 at WACC 6.0%/g 5.0% and V2 at WACC 9.0%/g 7.0% are both fine, but the coalition taking V1's WACC with V2's g gives 6.0% < 7.0%.
**Chosen:** raise `InvalidDCFError` in the model, and flag the same condition in SIA at the structural gate.
**Why:** silently returning a negative-denominator terminal value would produce a confident, catastrophically wrong attribution. Same philosophy as the TBA monotonicity guard. The checkable rule — `min(WACC) > max(g)` across both versions — is stated in the error message itself.
**Status:** LOCKED. Covered by `test_guard_catches_the_coalition_case_not_just_the_endpoints`.
