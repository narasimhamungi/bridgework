# Bridgework — Limitations

First-class artefact (Blueprint §N). Read this before trusting any output.

- **Not a universal Excel interpreter.** Ingestion accepts only workbooks
  Bridgework itself generated, with edits confined to the 7 driver values.
  Arbitrary third-party workbooks are out of scope for Phase 1.
- **Not a substitute for a full 3-statement model.** FCF-only; no balance
  sheet, no income-statement detail beyond what feeds FCF.
- **Not a forecast.** Driver values are analyst-supplied inputs, not
  predictions Bridgework generates.
- **Shapley on a discrete V1→V2 change is not Aumann–Shapley on a
  continuous game.** The two must never be conflated — this codebase only
  implements the discrete/exact-and-Monte-Carlo case.
- **SIA cannot catch qualitative business-logic errors.** Automated
  spreadsheet-error detection tools, even purpose-built ones, caught only
  ~27% of seeded errors in controlled studies (Anderson 2004, cited in
  Aurigemma & Panko 2010). SIA here is narrower still — schema/contract
  conformance only — and should never be read as a comprehensive audit.
- **The illustrative Zoom FCF does not reconcile to Zoom's reported
  non-GAAP FCF.** Stock-based compensation, interest income on Zoom's cash
  balance, gains on strategic investments, and deferred-revenue mechanics
  are all excluded by design.
- **Zoom's public anchor is FY2025 GAAP operating income of $813.3M
  (17.4% margin)**; the $1,123.6M figure is FY2026 (see
  `data/illustrative/assumptions.md`, Decision 1). The model's results were
  never claimed to reproduce Zoom's actuals.
- **Excel ingestion is round-trip-only.** No support for ingesting a
  workbook Bridgework did not itself generate.
- **DIA and TBA are present (Phase 2) but carry their own assumptions.**
  DIA's Sobol/Morris indices are computed under an *assumed* input
  distribution (independent uniform ±20%, Assumption #1) — the indices
  are only as meaningful as that assumption, which has not been
  calibrated against real driver volatility. TBA's default search ranges
  (Assumption #3) are plausible-but-arbitrary bounds, and TBA reports
  single-driver thresholds only: it does not find multi-driver break
  surfaces.
- **DIA and Shapley answer different questions and must not be read as
  cross-checks on each other.** Disagreement between them is expected and
  informative (a driver can dominate uncertainty while contributing
  nothing to a realized change), not a sign that one is wrong.
- **The L1-non-additivity "material" threshold used in `report.py`'s
  model-risk framing (10% of |total variance|) is provisional**, not yet
  evidence-calibrated across multiple scenario types.
- **The decision-priority weights (w1=0.5, w2=0.3, w3=0.2) are
  Assumption #2, not calibrated.** They are a documented, overridable
  default. The table reports which formula produced it (Phase 1
  Shapley-only vs Phase 2 weighted) so the basis is never ambiguous.
- **The HTML report renders one model's results.** It is not a dashboard:
  no cross-run comparison, no drill-down, no live data. That is deliberate
  (Blueprint hard constraint 5) — a static, self-contained artefact is
  auditable and emailable; a dashboard is neither.
- **Cross-company validation covers three companies, one of which is
  synthetic.** Zoom and Caterpillar use real reported anchors; Northwind
  Grocery is invented and its figures must never be cited. Three companies
  is evidence the schema generalises, not proof it generalises universally.
- **Caterpillar's `sga_and_rd_pct` is a balancing figure, not a reported
  line**, and its tax rate, working-capital intensity and capex ratio are
  illustrative rather than derived from filings. See
  `data/caterpillar/assumptions.md` for exactly which values are reported
  and which are not.
- **The compact 7-driver model does not represent Caterpillar's captive
  finance arm (Cat Financial) at all**, and will not reconcile to CAT's
  reported enterprise operating cash flow.
- **The DCF model is not an IB modelling artefact.** It attributes
  *valuation movement*; it does not build one. No debt schedule, no
  purchase price allocation, no accretion/dilution, no comps or precedent
  transactions, no mid-year convention. Unlevered FCF is an input, not
  derived from revenue and margins.
- **The DCF dataset is fully synthetic** — no real company, no public
  anchors, nothing citable. It is shaped to sit where DCF non-linearity is
  severe (84% of enterprise value in terminal value), which is realistic
  and common but is a deliberate choice, not an observation.
- **`WACC ≤ terminal growth` makes the model undefined**, and Shapley
  coalitions can hit that condition even when both compared versions are
  individually valid. The engine refuses rather than guessing; the
  precondition to check is `min(WACC) > max(g)` across both versions.
- **Adding a *model* is a code change**, unlike adding a *company*. The
  Blueprint's mapping-only rule covers companies only; a new model needs a
  compute function and an Excel contract.
- **The schema cannot detect an inappropriate application.** It validates
  ranges and structure, never economic meaning. A bank mapped onto the
  seven roles runs cleanly, passes all eight structural checks, and
  produces confident, meaningless output. The cross-company evidence is a
  claim about software coupling, not analytical validity.
- **Sobol sampling draws constrained parameters independently.** On the DCF
  this fails outright at wide perturbation ranges (±40%), because the
  sampler can pair a low discount rate with a high perpetuity rate and
  violate WACC > g. Rankings are stable from ±5% to ±30%, so conclusions
  do not depend on the default — but the module is unusable exactly where
  uncertainty is widest.
- **The threshold monotonicity guard is grid-resolution dependent.** A
  feature narrower than the grid spacing is missed, and the tool then
  reports zero crossings and advises widening the range when the correct
  advice is to narrow it. The shipped model is provably single-driver
  monotone so this cannot occur on it; the guard is insurance for future
  models and the insurance is imperfect.
- **Shapley is the wrong tool for causally ordered drivers.** It averages
  over all orderings as equally admissible; if a price increase *causes* a
  volume decline, orderings that move volume first are counterfactually
  incoherent, and a structural decomposition is more appropriate. For a
  continuous path rather than two snapshots, Aumann–Shapley applies.
- **L1 is scenario-conditional ordering exposure, not model risk.** A sound
  Gordon-growth DCF scores 24.9% because the scenario moved two drivers that
  share a denominator; a broken model scores zero if the scenario never moved
  the broken driver (`docs/methodology.md`).
- **The Monte-Carlo Shapley path does not fire on the shipped models.** Both
  cap at 7 changed drivers against an 8-driver threshold; the path is tested
  but unused.
- **Change detection is exact.** `diff_changed` compares with `!=`, so
  float dust (`0.031` vs `0.031000000000000001`) registers as a change with
  dust-level attribution. NaN/inf driver values are not rejected at ingestion.
- **`bridgework derive` does arithmetic, not extraction.** It converts line
  items an analyst supplies into driver ratios. It does not read filings,
  and will not detect a wrong line-item definition — only implausible
  ratios, which it warns about without correcting. Deciding what belongs in
  each line remains the analyst's judgement and responsibility.
- **No claims of "verified," "audited," or "regulatory-grade" status.**
  This is a portfolio prototype. SR 11-7/IBCS/FAST/ICAEW vocabulary is
  borrowed for rigor and terminology alignment, not as a compliance claim.
