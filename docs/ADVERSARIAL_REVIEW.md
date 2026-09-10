# Bridgework — Adversarial Review

Twelve challenges, answered honestly. Where a question was empirically
testable I ran the test rather than argued. **Two of these found real bugs
in shipped output.** Verdicts are graded:

- **Survives** — challenge answered, evidence holds
- **Partially survives** — real weakness, bounded and now documented
- **Hit** — the challenge lands; the work is weaker than claimed

---

## Summary

| # | Challenge | Verdict |
|---|---|---|
| 1 | Is Shapley the right method? | Partially survives — right for this question, wrong for two named cases |
| 2 | Does L1 measure real risk? | **Survives — stronger than claimed** |
| 3 | Cross-company under adversarial test? | **Hit** — accepts a bank without complaint |
| 4 | Is the Excel layer useful? | Partially survives — thinner than presented |
| 5 | Does 151 tests create false confidence? | **Hit** — 97% coverage, still missed two bugs |
| 6 | Does DCF broaden scope artificially? | Survives — it strengthens the thesis |
| 7 | Is ±20% defensible? | Partially survives — rankings stable, but breaks at ±40% |
| 8 | Are TBA guards sufficient? | **Hit** — grid-resolution dependent, gives opposite advice |
| 9 | Numerical/scaling problems? | Survives |
| 10 | Finance ability or just Python? | Partially survives — the honest answer is uncomfortable |
| 11 | Citation quality? | Partially survives — one weak link |
| 12 | Over-engineering? | Partially survives — two components don't earn their place |

**Net: 3 hits, 6 partial, 3 clean.** Two shipped bugs found and fixed.

---

## 1. Is Shapley the best attribution method?

**Partially survives.**

Shapley is correct for the question asked — attributing a realised, discrete change between two fully specified model versions — because it is the unique rule satisfying efficiency, symmetry, dummy and additivity, and efficiency is what preserves the reconciliation practitioners already rely on.

But there are cases where it is the wrong tool and the project doesn't say so clearly enough:

**Where Shapley is wrong:**

- **Causally ordered drivers.** Shapley averages over all orderings, treating them as equally admissible. If a price increase *causes* a volume decline, orderings that switch volume first are counterfactually incoherent. Shapley will happily average them in. A structural or causal decomposition is more appropriate, and Shapley's symmetry axiom is actively undesirable there.
- **Continuously varying inputs.** For a path traced over time rather than two snapshots, Aumann–Shapley is the correct construction. The project notes the distinction but frames it as terminology; it is a genuine applicability boundary.
- **Contractual attribution.** Where a bonus pool or transfer price is being split, the "fair division" reading of Shapley is a normative claim, not a descriptive one, and stakeholders may reasonably reject the axioms.

**What I would change:** §2.2 of the paper distinguishes Shapley from adjacent methods. It should also state when Shapley itself should not be used. The current framing implies it is the general answer; it is the right answer to a specific question.

---

## 2. Does L1 non-additivity genuinely measure risk?

**Survives — and the mathematics supports *more* than was claimed.**

The paper claimed only that L1 = 0 ⟺ additive ⟺ no ordering dependence. That is weaker than what is true.

I tested the relationship across 40 randomised FCF fixtures and 38 valid DCF fixtures:

| Model class | corr(L1, max ordering spread) | spread / L1 ratio | L1 an upper bound? |
|---|---:|---:|---|
| FCF (bilinear, 3 drivers) | **1.0000** | exactly 1.000 | Yes |
| DCF (non-zero three-way) | **0.9989** | 0.645 – 0.979 | Yes |

By comparison, the net figure correlates only **0.807**.

So L1 is a **tight upper bound on the maximum ordering spread** — exactly attained in the bilinear case, and never violated in 78 fixtures. It is not decoration; it is close to the sharpest single statistic available. The claim in the paper should be strengthened, not softened.

**Caveat:** both test families used three changed drivers. The bound is not proven for larger driver sets, and the project's higher-order interaction terms stop at three-way, so at n ≥ 4 the computed L1 would *understate* true non-additivity. That is a real limit on the metric as implemented.

---

## 3. Does "three companies, zero engine changes" hold adversarially?

**Hit. This is the most serious finding.**

The existing evidence is proof by construction: three fixtures I designed, all of which fit the seven-role schema because I chose them to. That is not an adversarial test.

So I ran one. I built a **bank** — net interest income, cost-income ratio, loan loss provisions — mapped onto the schema. Financial services is a business model the governing spec explicitly *rejected* as out of scope.

**Result: it ran cleanly. All eight structural checks passed. It produced a confident attribution with no warning of any kind.**

The output is meaningless. Loan loss provisions are not capital expenditure; regulatory capital movement is not working capital; a bank's cash generation does not work like this at all. The tool cannot tell, because the schema validates *ranges and structure*, never *economic meaning*. Any seven plausibly-scaled numbers pass.

**What this means:** the mapping-only rule is a claim about software coupling, and it holds. It is not a claim about analytical validity, and the project's framing lets those blur together. "Generalises across three companies" invites a reading — the schema captures something general about corporate cash generation — that is not supported.

**What I would change:** the schema should carry an explicit `business_model` declaration with a supported enumeration, and reject anything outside it. Approximately thirty lines. Until then the README should say the tool has no way to detect an inappropriate application, which is a stronger and more honest statement than the current limitations entry.

---

## 4. Is the controlled Excel architecture useful, or now a byproduct?

**Partially survives. Thinner than presented.**

What it genuinely does: workbooks are formula-driven, tie out to the Python engine to four decimals, recalculate with zero errors in an independent engine, and can be edited in declared input cells and re-ingested. The cross-engine tie-out is real validation and it caught a defect Python tests could not (note text beginning with `=` parsed as a formula).

What it does not do: ingest anything the tool did not itself generate. So the realistic workflow is *round-trip*, not *integrate with the analyst's existing model* — which is what a finance reader will assume from "Excel ingestion."

**Honest characterisation:** Excel here is a verification surface and a presentation layer. It provides an independent implementation to check against, and a familiar artefact for a reviewer. It is not an integration path. The paper's §4.3 is defensible; the README oversells by implication.

The SIA checks are correspondingly narrow — schema conformance, not model quality. Against Panko's 27% detection ceiling for purpose-built auditors, eight structural checks against a controlled schema is a much weaker claim, and should be stated as such rather than left for the reader to infer.

---

## 5. Does the test count create false confidence?

**Hit — and the evidence is in this document.**

Line coverage is 97% (1,264 statements, 40 uncovered). By conventional measures the suite is strong.

**It missed two real bugs, both found by adversarial testing during this review:**

1. **Sign loss on negative levels.** The summary formatter used `abs()` for both change magnitudes and output levels. Northwind's V2 free cash flow of **−$152.88M was reported as "$152.88M"** — in shipped output, on a headline figure, in both the markdown and HTML reports. A finance reader would have read a cash-generative business where the model says the opposite.

2. **Interaction CSV not reconciling.** The exported interaction file omitted the three-way term, so summing it gave 21.3% where the report stated 22.7%. In a tool whose entire argument is reconciliation, an output that does not reconcile to its own report is a credibility failure.

Both are now fixed with regression tests. But the lesson is the challenge's point exactly: **the suite tested that computations were right, not that outputs were readable and coherent.** 151 tests and 97% coverage did not catch a missing minus sign on the most prominent number in the report.

**What I would change:** add a class of test that asserts properties of the *rendered artefact* — signs preserved, figures in prose matching figures in tables, exported files reconciling to stated totals. There are now three such tests; there should be a dozen.

---

## 6. Does the DCF extension strengthen or pad the project?

**Survives.**

The test for scope creep is whether the addition strengthens the core argument or merely widens it. This one strengthens it, measurably:

| Model | L1 non-additivity |
|---|---:|
| Retail (FCF) | 1.9% |
| Heavy industry (FCF) | 5.0% |
| Software (FCF) | 9.9% |
| **Valuation (DCF)** | **22.7%** |

The DCF is where the thesis is most true, because WACC and terminal growth occupy the same denominator. Without it the project demonstrates the problem on models where it is modest; with it, the problem is shown to be worst in the most externally scrutinised output in finance.

It also surfaced the coalition-validity failure mode, which is a genuinely novel contribution and does not arise in the FCF models at all.

**The honest limit:** it makes the project *legible* to IB and equity research without demonstrating transaction-modelling craft. No debt schedule, no purchase price allocation, no accretion/dilution. That is stated in the limitations and should stay stated.

---

## 7. Are the DIA/Sobol results defensible given ±20%?

**Partially survives. Better than feared on one axis, worse on another.**

I varied the perturbation range on the DCF:

| Range | Ranking | Top ST |
|---|---|---:|
| ±5% | wacc > terminal_growth > growth_explicit | 0.838 |
| ±10% | wacc > terminal_growth > growth_explicit | 0.838 |
| ±20% | wacc > terminal_growth > growth_explicit | 0.837 |
| ±30% | wacc > terminal_growth > growth_explicit | 0.841 |
| **±40%** | **FAILS — `InvalidDCFError`** | — |

**Good news:** the ranking is completely stable from ±5% to ±30%, and the top index moves by 0.004. The conclusions drawn from DIA do not depend on the arbitrary choice. That is a stronger defence than I expected.

**Bad news, and it is real:** at ±40% the analysis *cannot run at all*. The sampler draws WACC and terminal growth independently, so it can pair a low discount rate with a high perpetuity rate and violate WACC > g. At ±20% the margin is 6.00% vs 4.20%; at ±40% it is 4.50% vs 4.90% and the model is undefined.

So the sensitivity module is unusable precisely where uncertainty is widest — which is where sensitivity analysis matters most. The fix is correlated or constrained sampling (sample the *spread* rather than the two rates independently), which is standard practice and not implemented.

**Verdict:** the ±20% choice is not load-bearing for conclusions, which is the more important question. But the independence assumption in the sampler is a genuine methodological weakness that the ±20% default happens to conceal.

---

## 8. Are the TBA monotonicity guards sufficient?

**Hit.**

The guard scans an 11-point grid and counts sign changes. I tested it against a function with a dip narrower than the grid spacing:

| Grid points | Sign changes detected | Verdict |
|---:|---:|---|
| 11 (default) | 0 | **missed it** |
| 21 | 0 | **missed it** |
| 101 | 2 | caught |
| 1001 | 2 | caught |

At default resolution the guard reports **zero crossings** and advises the user to *widen the search range*. The truth is that there are **two roots inside the range** and the correct advice is to *narrow* it. The guard gives the opposite instruction.

This matters more than a generic "sampling can miss features" caveat, because the project makes a specific virtue of these guards — refusing rather than guessing — and here the refusal carries actively wrong guidance.

**Mitigating:** the specific model shipped is provably single-driver monotone (tested, 200 points per driver), so the failure cannot occur on it. The guard is insurance for future models, and it is the insurance that is defective.

**What I would change:** either derivative-sign checking rather than value-sign counting, or an adaptive refinement that subdivides where consecutive values move non-monotonically, or at minimum a warning that a zero-crossing verdict is conditional on grid resolution. Currently it is stated with more confidence than it earns.

---

## 9. Hidden numerical or scaling problems?

**Survives.**

| Test | Result |
|---|---|
| Efficiency error, near-cancelling contributions ($1M revenue, offsetting drivers) | **0.00e+00** — exact |
| Exact Shapley, n=3 / n=5 / n=6 | 0.5 / 0.7 / 0.9 ms |
| Coalition count at the n=8 switch point | 256 — trivial |

No catastrophic cancellation: the marginal-contribution formulation sums differences of similar magnitude rather than differencing large sums, which is numerically well-behaved. Reconciliation asserts at 1e-9 throughout and has never failed.

Above n=8 the Monte-Carlo path takes over with a seeded estimator, bootstrap CI, and automatic sample doubling when the interval is too wide. That path is tested for convergence and reproducibility.

**Residual concern, minor:** `all_orderings` enumerates n! exhaustively up to n=6 (720 orderings). At n=6 that is 4,320 model evaluations — fine for these models, but it would become the bottleneck for an expensive model long before Shapley did. The sampled fallback above n=6 handles it.

---

## 10. Does this demonstrate finance ability, or just Python?

**Partially survives. The honest answer is uncomfortable.**

**What genuinely requires financial judgement:**

- Recognising that bridge ordering is a real, unaddressed problem in practice. A pure engineer would not know that variance bridges are ubiquitous, that ordering is undisclosed, or that this bothers anyone.
- Knowing that L1 rather than net is the right statistic, because *sign cancellation between interactions does not cancel the ambiguity they create*. That is a modelling insight, not a coding one.
- Predicting that a DCF would be worse than an FCF model because of the (WACC − g) denominator — then testing it.
- The coalition-validity failure. Spotting that WACC > g must hold across *mixtures* requires knowing both what Shapley does and why the constraint exists.
- Catching that a cited FY2025 operating income figure was actually FY2026.

**What does not:**

- The seven-driver model is elementary. There is no three-statement linkage, no debt schedule, no working-capital detail, no deferred revenue, no segment build.
- A strong quantitative engineer with a finance textbook could implement everything here.

**The fair characterisation:** this demonstrates **financial-methodology judgement**, not **financial-modelling craft**. It shows someone who can identify a flaw in standard practice, select a defensible technique, and validate it. It does not show someone who can build a complex model.

Those are different competencies and different roles value them differently. For risk, model validation and FP&A analytics, the former is the more relevant. For IB and M&A, the latter is what gets tested, and this project does not supply it. The positioning already says this, and it should stay prominent rather than softened.

---

## 11. Are the research claims and citations strong enough?

**Partially survives.**

**Strong:** Shapley (1953), Aumann–Shapley (1974), Grabisch–Roubens (1999), Sobol (2001), Saltelli et al. (2010), Castro–Gómez–Tejada (2009) are the correct primary sources, each attached to a specific implementation decision rather than decorating a bibliography. The Grabisch–Roubens citation is load-bearing — it drove implementing the general weighted form over the shortcut, and a test proves the difference.

**Weak, and it is the one most likely to be challenged:** the "27% detection" figure is cited as *Anderson (2004), reported in Aurigemma and Panko (2010)*. That is a secondary citation of a single study, used to bound a claim about automated auditing. I have not read the primary source. In a finance portfolio that invites exactly the challenge it deserves. It should either be verified at source or replaced with the better-established Panko inspection figures (50–63% individual, 70–83% group), which are more robust and make the same point.

**Missing:** no engagement with the practitioner literature on variance analysis in management accounting, where mix/volume/price decomposition has been discussed for decades and standard treatments exist. The project asserts that bridges are ubiquitous and their ordering undisclosed. That is my observation of practice, not a cited finding, and a reviewer would reasonably ask for support.

**Also missing:** no citation for the claim that the ordering problem is *unaddressed*. Absence of evidence is not evidence of absence, and I did not conduct a systematic search.

---

## 12. Has the architecture drifted into over-engineering?

**Partially survives. Two components do not earn their place.**

The anti-overengineering test asks whether each piece is justified by a stated requirement. Applying it honestly:

**Earns its place:** the model/engine separation (enabled a second model type without disturbing the golden datasets); the ModelSpec registry (contained a large change to one module plus one entry); the frozen dataclasses (required for safe coalition enumeration); the golden-dataset suite (caught a genuine regression during this review).

**Does not:**

- **The decision-priority composite** (0.5 / 0.3 / 0.2 weights). Three metrics normalised and blended with unjustified weights into a single score. This is worse than showing three honest columns: it manufactures precision, invites "why those weights?", and has no answer. It should be deleted, not calibrated.
- **Morris screening.** Implemented as a cheap pre-screen for large driver sets. The largest model has seven drivers, where Sobol runs in under a second. It solves a problem the project does not have. Roughly forty lines of unused capability.

**Borderline:** the Monte-Carlo Shapley path with bootstrap CI and adaptive sample doubling is genuinely sophisticated and never fires, because no model exceeds eight changed drivers. It is defensible as demonstrating the scaling story is understood, and it is tested. But it is a real answer to a hypothetical need.

**Overall:** roughly 5–8% of the codebase is capability without a driving requirement. That is not egregious, and the core is disciplined. But "no feature without a stated need" was a governing principle, and it was not fully honoured.

---

## What changed as a result of this review

**Fixed:**
1. Sign loss on negative output levels — shipped bug, headline figure, both report formats. Regression test added.
2. Interaction CSV not reconciling to the reported L1 figure. Regression test added.

**Documented as newly-understood limits:**
3. The schema accepts business models it cannot meaningfully represent, silently.
4. Sobol sampling fails entirely at wide perturbation ranges on the DCF, due to independent sampling of constrained parameters.
5. The threshold guard is grid-resolution dependent and can give inverted advice.

**Strengthened:**
6. L1's status upgraded from "correct diagnostic" to "tight upper bound on maximum ordering spread," with 78 fixtures of evidence.

**Recommended, not done:**
7. Delete the decision-priority composite.
8. Verify or replace the 27% auditing citation.
9. Add a `business_model` declaration to the schema with rejection of unsupported types.
10. Constrained sampling for parameters with joint validity conditions.
11. Rendered-artefact tests as a first-class category.

---

## Closing assessment

The core is sound. The central claim — that bridge attribution is order-dependent, that the effect is sometimes material, that it is measurable and removable — is correct, tested and now better evidenced than before this review. The L1 result strengthened under attack, which is the outcome one hopes for and rarely gets.

The weaknesses are real and they cluster in one place: **the project is stronger at computing than at knowing when it should decline to compute.** It will attribute a bank's cash flow, misreport a negative level, and give inverted advice about a threshold it cannot resolve. Each is fixable and two are now fixed, but the pattern is worth naming, because a diagnostic tool that produces confident output on inappropriate input is failing at precisely the thing it exists to do.

Nothing here is fatal. Nothing here should be hidden either.

---

# Round 2 — External red-team review

An independent reviewer red-teamed the project with from-scratch oracle
implementations rather than trusting its tests. **Every P0 finding was
independently reproduced here before being accepted.** All are now fixed.

## P0 findings — all confirmed, all fixed

**1. A shipped invariant was mathematically false.**
`l1_non_additivity` summed absolute pairwise Grabisch–Roubens indices and
added the three-way term only at exactly n=3, silently discarding all
higher-order terms at n ≥ 4. The documented claim — "L1 == 0 implies
provably zero ordering dependence" — was therefore false.

Reproduced: a four-player game with Möbius mass +0.277 on each 3-subset
and −0.832 on the 4-set has all six pairwise indices ≈ 0, so the old L1
read **0.002** while every player's sequential marginal swings by
**0.278**. Wrong by a factor of 140.

*Fixed:* L1 is now `Σ|m(T)|` over all subsets of size ≥ 2, computed from
the Möbius coefficients. No hole at any n. The counterexample is now a
test. **Consequence: the DCF headline moves 22.7% → 24.9%** — the
previously-discarded higher-order term. The three FCF datasets are
unchanged, because their three-way terms are exactly zero.

**2. The security boundary was misattributed.**
The Blueprint claimed SIA "catches silent hand-edits that break the
formula-driven contract." It does not. Reproduced: a semantically tampered
formula (`=B8-B10*2` — whitelisted functions, resolvable references,
completely wrong economics) **passes SIA 8/8** and is caught only by
ingestion's round-trip diff.

*Fixed:* the boundary is now stated precisely in the module docstring —
ingestion is the tamper gate, SIA is a regression gate on self-generated
workbooks validating syntax classes, never semantics. A test locks the
distinction so the claim cannot drift back.

**3. "8 structural checks" was 7 plus a hardcoded placeholder**, and the
Blueprint's promised orphaned-driver check did not exist in the code —
contract and enforcement had drifted apart.

*Fixed:* the orphaned-driver check is implemented (every declared driver
must be referenced by ≥1 Calc formula), replacing the placeholder. It is
now genuinely 8 active checks, with a test.

**4. The README quickstart was broken** — it referenced
`models/zoom_v2.xlsx` after the layout moved to `models/zoom/v2.xlsx`. A
copy-paste failure in a reviewer's first five minutes. *Fixed.*

## P1 findings — fixed

**5. TBA reported a confident wrong root on discontinuities.** Brent's
method brackets a *sign change*, which a step function produces just as a
root does. A jump from −1 to +1 returned `defined=True, threshold=0.7499…`
where the function never equals the target. *Fixed* with a residual
post-check: if `|f(root) − target|` doesn't vanish, refuse and say the sign
change is a discontinuity. This closes the only path where the
"refuse rather than guess" guarantee was violated.

**6. The DCF coalition guard fired mid-pipeline**, after workbooks were
already written, as a raw exception. *Fixed* with a CLI pre-flight check
of `min(WACC) > max(g)` that halts with an actionable message before any
side effects.

**7. Repo hygiene.** Duplicate `examples/`≡`outputs/` trees, a stale
`financecore.egg-info` from before the rename, pytest in runtime
requirements. *Fixed:* one committed tree, artefacts gitignored,
dependencies pinned with upper bounds.

**8. The reproducibility claim rested on unpinned dependencies.** The
manifest recorded Python and platform but not package versions, so a SALib
or NumPy bump could silently change Sobol output while the audit trail
looked identical. *Fixed:* the manifest now carries a dependency
fingerprint (hashed version list of every calculation dependency).

**9. Runtime invariants used `assert`**, which `python -O` strips —
disabling reconciliation and efficiency checks in exactly the optimised
runs a user would most trust. *Fixed:* explicit `ReconciliationError`
raises, subclassing `AssertionError` for compatibility. Verified under
`-O`.

## Accepted, not yet acted on

- **"Model-risk diagnostic" was too strong a label.** L1 measures
  scenario-conditional interaction intensity: a sound Gordon-growth DCF
  scores 24.9% while a genuinely broken model scores zero if the scenario
  never moved the broken driver. The methodology doc now says this
  explicitly and proposes "ordering-sensitivity exposure" as the accurate
  term. The 10% warning threshold remains flagged as an uncalibrated
  heuristic.
- **The Monte-Carlo Shapley path is unreachable.** Both models cap at 7
  changed drivers against an 8-driver threshold. ~80 lines of tested,
  correct, dead generality. Documented as pre-built rather than removed —
  but it is the project's clearest remaining over-engineering, and
  "documented" is a weaker answer than "deleted."
- **Float-dust change detection.** `diff_changed` uses exact `!=`, so
  `0.031` vs `0.031000000000000001` registers as a change with dust-level
  attribution. Cosmetic; an epsilon tolerance is the fix.
- **NaN/inf drivers are not rejected** at ingestion.

## What this round says about the project

The reviewer could not make the numbers wrong. Every headline figure
survived independent oracle recomputation: FCF, Shapley values, ordering
ranges, the DCF valuation, efficiency across the tax kink, and the Zoom
FY2025 citation correction (verified against the primary SEC filing).

What did not survive was **claim calibration**. Exactly one shipped
invariant was false, one security boundary was misattributed, and three
headline phrases — "model-risk diagnostic," "proves generalisation," "8
checks" — were each a notch stronger than the evidence. That is the same
pattern the first review found: the engineering is sound, and the language
around it was consistently slightly ahead of what had been demonstrated.

Both rounds found real defects. Neither found a wrong number.
