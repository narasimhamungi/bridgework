# Order-Independent Attribution of Change in Financial Models

**A Shapley-value approach to variance bridges and valuation walks, with an implementation and cross-model evidence**

*Bridgework — technical report, v1.0*

---

## Abstract

When a financial model's output changes between two versions, the standard explanation is a bridge: drivers are switched from their old values to their new ones one at a time, and each is credited with the movement it produced. This procedure is path-dependent. Because the drivers interact, the order in which the analyst walks them changes the numbers reported, with nothing in the output disclosing that a choice was made.

We quantify the effect on four models and find it is not uniformly small. On a compact free-cash-flow model of a software business the spread across orderings reaches $3.86M on a driver whose true contribution is $12.99M — 30% of the figure being reported. On a discounted cash flow model the effect is materially worse: because terminal value divides by the difference between the discount rate and the perpetuity growth rate, the interaction between those two inputs is structurally severe, and the credited impact of the discount rate varies by $8.12 per share on a stock valued near $110.

We implement the Shapley value as the attribution rule. It is the unique allocation satisfying efficiency, symmetry, the dummy property and additivity, and it is by construction independent of ordering. Alongside it we report the interaction structure itself, using the Grabisch–Roubens interaction index, and argue that the correct risk statistic is the sum of absolute interaction terms (which cannot cancel) rather than the net figure (which can, and does, understate the problem by an order of magnitude in one of our cases).

The accompanying implementation, `bridgework`, is an open-source Python package: 4,909 lines, 159 tests, deterministic, with no language model in the calculation or narrative path. It runs unchanged across three companies with deliberately opposing economics and across two model types. We report a class of failure specific to coalition-based attribution — mixtures of two individually valid model versions can be jointly invalid — and describe the guard it requires.

---

## 1. The problem

### 1.1 What a bridge is, and what it hides

An analyst holds two versions of a model. Last month's forecast said free cash flow would be $771M; this month's says $810M. The question from the CFO is the ordinary one: *why?*

The ordinary answer is a bridge. Start at V1. Switch revenue growth to its new value; record the movement. Switch operating expenses; record. Switch capital expenditure; record. The three movements sum to $38.96M and the bridge reconciles exactly. It looks like an accounting identity, and its exactness is part of why it is trusted.

But the reconciliation is exact for *every* ordering, and the individual figures are not the same across them. Switching revenue growth first, before margins have moved, produces a different number than switching it last. The bridge that reaches the CFO is one of six possible bridges (with three drivers; one of 720 with six), and nothing on the page indicates which one, or that the others exist.

This is not a defect of arithmetic. It is a property of the model: when drivers interact — when revenue and margin multiply, when a discount rate and a growth rate appear in the same denominator — their joint effect is not the sum of their separate effects, and any sequential procedure must assign that joint effect to whichever driver happened to move later.

### 1.2 Why it is not self-correcting

Two features make this durable rather than self-limiting.

First, the exactness is reassuring in the wrong direction. Because the bridge always reconciles, it presents as arithmetic rather than as a methodology with degrees of freedom.

Second, the choice is usually not experienced as a choice. Drivers are typically walked in the order they appear on the schedule, or in narrative order — top line first, costs after. The analyst is not aware of having selected among alternatives, so nothing prompts disclosure.

The result is that a figure carrying real methodological variance is presented as if it carried none.

### 1.3 Scope of the claim

We are not claiming bridges are worthless, that all bridges are materially wrong, or that any specific published bridge is misleading. The size of the effect is a property of the model's non-linearity, and in one of our four cases it is under 2% — negligible. The claim is narrower and, we think, harder to dispute: **the size of the effect is unknown to the reader, is not currently reported, is sometimes large, and is computable.**

---

## 2. Background

### 2.1 The Shapley value

Shapley (1953) considered how to divide the value created by a coalition among its members, and showed that exactly one allocation satisfies four properties simultaneously: *efficiency* (the parts sum to the whole), *symmetry* (members with identical marginal contributions receive identical shares), *dummy* (a member contributing nothing receives nothing), and *additivity* (values of combined games are the sums of the separate values). That allocation is the average of each member's marginal contribution taken over all orderings.

The mapping to our problem is direct. The "players" are the drivers that changed; the "value" of a coalition $S$ is the model output with the drivers in $S$ set to their V2 values and the rest held at V1. The Shapley value of driver $i$ is

$$\phi_i \;=\; \sum_{S \subseteq N \setminus \{i\}} \frac{|S|!\,(n-|S|-1)!}{n!}\,\bigl[f(S \cup \{i\}) - f(S)\bigr]$$

Efficiency means the driver attributions sum exactly to the total change, so the bridge still reconciles. Averaging over all orderings means the answer no longer depends on any one of them. In other words: the property practitioners already rely on is preserved, and the property they did not know they were relying on is removed.

### 2.2 What the coalitions mean, and what the attribution is not

A coalition mixing V1 and V2 driver values is a *counterfactual hybrid* — a model state that never existed and that no analyst chose. Shapley treats all 2ⁿ such hybrids as equally admissible. This is the standard interventional-perturbation construction, the same convention SHAP-style feature attribution adopts, and it is defensible; but it should be said explicitly rather than left for a reader to infer.

It follows that the output is an **allocation of a realised total, not a causal estimate**. "Operating expense contributed +$96.8M" means "under this allocation convention, averaged over all admissible orderings, that share of the movement is credited to opex." It does not mean opex *caused* it in any structural sense. Where drivers stand in a genuine causal or temporal order — a capex step-up triggered by a revenue surge — sequential attribution in that order carries information Shapley deliberately destroys, and is the better tool. We know of no case in ordinary variance reporting where such an order is documented, which is why order-independence is the safer default, but the positive case for sequential exists and should be acknowledged.

### 2.3 Distinguishing this from adjacent techniques

**Aumann–Shapley** (Aumann and Shapley, 1974) values apply to games with a continuum of players or continuously divisible participation. Our drivers take one of two discrete values — V1's or V2's — so the discrete Shapley value is the applicable construction. The two are frequently conflated in applied work; they answer different questions.

**Sobol indices** (Sobol, 2001) decompose output *variance* under an assumed distribution over inputs. This is a different question from attributing a specific realised change, and the difference is practically consequential rather than academic — we return to it in §5.3.

**SHAP** and related machine-learning attribution methods apply Shapley values to feature attribution for model predictions. The mathematics overlaps; the setting does not. We attribute a change between two fully specified deterministic models, not a prediction relative to a background distribution.

### 2.4 Interaction indices

Grabisch and Roubens (1999) axiomatised an interaction index for pairs and larger subsets. For a pair $\{i,j\}$ in an $n$-player game it averages the second difference over subsets of the remaining players:

$$I(i,j) \;=\; \sum_{S \subseteq N \setminus \{i,j\}} \frac{|S|!\,(n-|S|-2)!}{(n-1)!}\Bigl[f(S \cup \{i,j\}) - f(S \cup \{i\}) - f(S \cup \{j\}) + f(S)\Bigr]$$

The naive two-driver formula $f(\{i,j\}) - f(\{i\}) - f(\{j\}) + f(\emptyset)$ coincides with this only when higher-order terms vanish. Our first test fixture happens to satisfy that condition, which makes it a trap: an implementation using the shortcut passes on that fixture and is wrong in general. We implement the weighted form unconditionally and verify divergence on a fixture with a genuine three-way term (§6.2).

### 2.5 Spreadsheet error and model risk

Panko's programme of work (1998, 2008) established that spreadsheet error rates are high and that detection is difficult: individual inspection catches roughly half to two-thirds of seeded errors, and automated auditing tools have been measured near 27% (Anderson 2004, reported in Aurigemma and Panko 2010). We take two things from this. First, structural checking is worth doing. Second, and more importantly, it must be claimed modestly — we describe in §4.2 what our checks do and do not cover, and the honest answer is that they verify conformance to a controlled schema, not economic correctness.

The vocabulary of model-risk governance — documented limitations, effective challenge, independent validation — we borrow from SR 11-7 (Federal Reserve, 2011) for terminological alignment. We make no claim of compliance with it.

---

## 3. Method

### 3.1 Attribution

We compute Shapley values by exact enumeration of all $2^n$ coalitions for $n \le 8$ changed drivers, which is instantaneous at the scale of models this addresses. Above that we use permutation sampling (Castro, Gómez and Tejada, 2009), seeded for reproducibility, with an empirical bootstrap 95% confidence interval. If the widest interval exceeds 2% of the total change, the sample count doubles automatically, up to three retries, rather than reporting an under-converged estimate silently.

The threshold of 8 is deliberately generous. A model requiring more than eight drivers to change simultaneously is arguably straining the compact-model discipline this tool assumes, so the switch functions as a design signal as much as a performance boundary.

### 3.2 Reporting the ambiguity rather than hiding it

Removing order-dependence from the headline figure is only half of the response. The other half is telling the reader how much ambiguity was removed, because that is the quantity that determines whether the distinction mattered.

We therefore compute the full set of sequential bridges and report, per driver, the minimum and maximum a sequential walk could have produced. In the visual output these appear as whiskers on the Shapley bars. A short whisker says the ordering question was immaterial here; a long one says the conventional presentation would have been substantially arbitrary.

### 3.3 Net versus L1 non-additivity

Two summary statistics are available, and the choice between them matters more than it appears.

**Net non-additivity** is the total change minus the sum of the isolated one-at-a-time effects. It equals the signed sum of all interaction terms, so positive and negative interactions cancel within it.

**L1 non-additivity** is the sum of absolute Möbius interaction coefficients over all subsets of size ≥ 2. Nothing cancels. Aggregating pairwise indices instead is *not* equivalent: it discards higher-order terms, and a four-player counterexample exists whose pairwise indices are all ≈0 while ordering spread is 0.278.

On our primary fixture these differ by a factor of six: net is $0.60M, L1 is $3.86M. The net figure is the one a naive calculation produces, and it understates the ordering risk badly, because two interactions of opposite sign both create order-dependence — they do not neutralise each other merely because they sum to something small.

L1 also has a clean interpretation: **L1 = 0 if and only if the model is additive over the changed drivers, in which case every ordering yields identical results.** It is therefore the correct diagnostic, and we report it as such, with the net figure shown alongside for completeness and explicitly labelled as the weaker statistic.

### 3.4 Refusing rather than guessing

Two guards deserve mention because both refuse to return an answer.

**Threshold analysis.** Finding the driver value at which an output crosses a level is a root-finding problem, and root-finding on a non-monotone function returns an arbitrary root. Before invoking Brent's method we scan a grid and count sign changes, proceeding only on exactly one. Otherwise we decline — and distinguish the two failure modes, because they have opposite remedies: zero crossings means the root lies outside the search range (widen it), while two or more means genuine non-monotonicity (narrow it to isolate one). Conflating them, as our first implementation did, sends the analyst the wrong way.

**Coalition validity.** This one is specific to coalition-based attribution and we have not seen it discussed. A DCF requires the discount rate to exceed the perpetuity growth rate; otherwise the terminal value denominator is zero or negative and the model is meaningless. Both compared versions will normally satisfy this. But Shapley evaluates *coalitions* — mixtures of V1 and V2 values — and a mixture can violate the condition when neither endpoint does. Concretely: V1 at WACC 6.0% and $g$ 5.0% is valid; V2 at WACC 9.0% and $g$ 7.0% is valid; the coalition taking V1's WACC with V2's growth gives 6.0% < 7.0% and is not. Without a guard the model returns a large negative terminal value and attribution proceeds to a confident, catastrophically wrong answer. We raise an explicit error carrying the checkable precondition:

$$\min(\text{WACC}_{V1}, \text{WACC}_{V2}) > \max(g_{V1}, g_{V2})$$

We expect this class of problem to arise wherever coalition-based attribution meets a model with a validity constraint spanning two or more drivers, and we suggest it deserves attention as a general matter rather than as a DCF quirk.

---

## 4. Implementation

### 4.1 Architecture

`bridgework` separates a pure calculation core from all input, output and presentation. The core contains no file access, no clock reads, no network calls, and no randomness that is not explicitly seeded. This is what makes byte-identical reproduction possible and is enforced by regression tests over committed golden outputs.

The engine requires only a deterministic function from a frozen driver record to a scalar. This was made explicit when the second model type was added: rather than generalise the driver container — which would have disturbed the Excel contract, the golden datasets and every company adapter — we threaded a model function through the engine with the original as default. All 125 tests existing at that point passed unchanged at every step of the refactor, including byte-exact output regression.

### 4.2 Structural checks

Eight mechanical checks run before any attribution: schema version, required sheets, absence of hardcoded values where formulas belong, cross-sheet reference integrity, sign and range plausibility, driver row order, and absence of unsupported constructs (`INDIRECT`, `OFFSET`, volatile functions, macros). A failure halts the pipeline.

The halt is the point. Attributing variance within a structurally broken model produces output that is fluent, precise and worthless. We would rather return nothing.

What these checks do **not** do: they cannot detect a driver that is internally consistent and economically wrong. Given the empirical detection ceilings in §2.4, that limit is stated in the tool's own output, not only in its documentation.

### 4.3 The spreadsheet boundary

Generated workbooks are formula-driven throughout — the Python values are never pasted in — so a reviewer can open the file, trace precedents, and change an input. Ingestion is restricted to workbooks the tool generated, with edits confined to declared input cells; every other cell is compared against the template and any difference is rejected with an itemised report.

This is deliberately narrow. Parsing arbitrary spreadsheets is a research problem, and a tool that half-solves it produces silent misreadings — the opposite of the property we are arguing for. Workbooks are verified to recalculate without error, and the recalculated share price ties to the Python engine to four decimal places.

### 4.4 Reporting

Output is a single self-contained HTML document with charts embedded, no external assets, and no interactivity. This is a considered choice rather than a limitation. A variance workpaper's value lies substantially in being archivable — attached to a close file, sent to a reviewer, reopened years later to answer why a figure was stated. A live dashboard cannot be archived.

The document opens with the same driver shown three ways: the least favourable ordering, the most favourable, and the Shapley figure. Conventional structure — headline, driver table, diagnostics — is the format that creates the problem, because it presents one number as though it were the only available answer. Leading with the contrast lets the reader see why an order-independent figure is needed before being asked to accept one.

No narrative, ranking or figure in the output is generated by a language model.

---

## 5. Results

### 5.1 Datasets

Four datasets, chosen for contrasting structure rather than for coverage.

| Dataset | Type | Gross margin | Capex intensity | Working capital | Provenance |
|---|---|---:|---:|---:|---|
| Software (Zoom) | FCF | ~76% | 3.0% | positive | Public anchors; illustrative drivers |
| Heavy industry (Caterpillar) | FCF | ~38% | 5.0% | positive | Public anchors; some illustrative |
| Retail (Northwind) | FCF | ~26% | 2.0% | **negative** | Fully synthetic |
| Valuation target | DCF | — | — | — | Fully synthetic |

Public anchors are verified against filings. Where a value is illustrative or a balancing figure rather than a reported line, the dataset documentation says so explicitly and per value. Two datasets are wholly synthetic and are labelled as such throughout; none of their figures should be cited.

### 5.2 Magnitude of the ordering effect

| Dataset | Total change | L1 non-additivity | As % of change |
|---|---:|---:|---:|
| Retail | −$248.29M | $4.78M | 1.9% |
| Heavy industry | −$1,679.78M | $84.57M | 5.0% |
| Software | +$38.96M | $3.86M | 9.9% |
| **Valuation (DCF)** | **−$45.11/share** | **$11.25/share** | **24.9%** |

The three cash-flow models are near-bilinear and the effect is modest, though at the software model's 9.9% the largest driver's credited impact still spans $11.06M to $14.92M across orderings — a 30% range on the figure reported.

The valuation model is different in kind. Terminal value is

$$TV = \frac{FCF_5\,(1+g)}{\text{WACC} - g}$$

so the discount rate and perpetuity growth rate interact through a difference in a denominator. The WACC × terminal-growth pair alone accounts for over half of total pairwise interaction. In per-share terms the discount rate's credited impact ranges from −$25.58 to −$17.45 depending on ordering, a spread of $8.12 per share against a total move of $45.11, on a stock valued near $110.

The practical reading: **the ordering problem is most severe precisely in valuation work, where the outputs are most consequential and most externally scrutinised.** We did not anticipate this when we began; we tested it because it was the pivotal question for whether the extension was worth building, and the measurement is what settled it.

### 5.3 Attribution and sensitivity answer different questions

In the software dataset, cost of goods sold did not change between versions. Its Shapley value is therefore zero — correctly, and necessarily.

Global sensitivity analysis assigns it a total-order Sobol index of 0.17: roughly 17% of the model's output uncertainty. The driver contributed nothing to what happened and is the second-largest contributor to what might.

Both statements are true and neither substitutes for the other. Attribution is retrospective and forensic; sensitivity is prospective and distributional. A report presenting only the first is silent on a material risk — not through error, but by construction. We therefore report both and label the distinction rather than allowing a reader to treat one as a check on the other.

### 5.4 Schema generality

The canonical driver schema was tested by adding companies with unrelated vocabularies — "sales and revenues" and "cost of sales" rather than "revenue" and "COGS" — through adapter files mapping native names onto canonical roles.

The test was constructed to be meaningful. Building the mapping mechanism was itself a source change; a rule requiring zero source changes cannot be satisfied by a codebase with no mapping layer. So the mechanism was built, that state committed, and a *third* company added afterwards. It required three configuration files and no source changes, verified mechanically rather than by inspection.

This establishes that the schema generalises. It does **not** establish that the outputs are independently correct for those companies — only that they are internally consistent. That gap is real and we name it in §7.

---

## 6. Validation

### 6.1 Test suite

159 tests. Beyond conventional unit and integration coverage:

- **Axioms.** Efficiency, symmetry, dummy and additivity are each verified directly, not assumed from the implementation.
- **Golden datasets.** Committed byte-exact expected outputs; any change is a hard failure. These held through two substantial refactors and are the principal reason we can claim reproducibility rather than merely intend it.
- **Edge cases.** Zero change, single-driver change, unidirectional drivers, opposing drivers, a driver crossing the tax floor discontinuity, and an interaction calibrated to rival a main effect in magnitude.
- **Failure modes.** Every structural check has a deliberately broken fixture. Every ingestion rule has a violating input.

### 6.2 Findings established by testing

Three results came from the test suite rather than from design, and we record them because they are the substance of what validation produced.

**Interaction formula divergence.** Our primary fixture has a three-way interaction term of exactly zero, so the naive pairwise formula and the general weighted formula agree on it. A fixture crossing the tax floor produces a non-zero three-way term and separates them. Had we validated only against the first fixture, an incorrect implementation would have passed.

**Single-driver monotonicity.** Sweeping 200 points per driver establishes that this model's output is monotone in every individual driver across its full range, including across the tax floor discontinuity — because each driver enters through at most a two-piece piecewise-linear relationship whose pieces share slope sign. Threshold analysis is therefore safe by construction here; the monotonicity guard is insurance for the general case, not a local necessity. This is a tested claim, not an assumption.

**Coalition validity.** The failure described in §3.4 was found by constructing the case and observing the model return a large negative terminal value without complaint.

### 6.3 External tie-out

Generated workbooks recalculate in an independent spreadsheet engine with zero formula errors across all four datasets. The recalculated DCF share price of $110.2103 matches the Python engine to four decimal places. This is a genuine cross-implementation check: two different evaluation engines, the same result.

One defect was found only this way. Explanatory note text in the workbook began with `=`, which spreadsheet software interprets as a formula. Every generated file would have displayed `#NAME?` errors on opening. The Python-side tests could not have detected it.

---

## 7. Discussion

### 7.0 The status of this work

**This is a demonstration of a methodological problem and a defensible fix,
on a controlled model. It is not a deployable tool and should not be read
as one.**

The problem is real and general; the correction is correct and proven; the
implementation is tested and reproducible. But it operates on a compact
seven-driver model rather than on production financial models, and the
schema silently accepts business models it cannot represent. The distance
between "this method is right" and "an organisation can use this" is
substantial, and is not bridged here.

### 7.1 What this establishes

That order-dependence in bridges is real, measurable, sometimes material, and removable at negligible computational cost. That its magnitude varies by more than a factor of ten across model types, and is largest in valuation. That the appropriate risk statistic is the L1 rather than the net figure. That coalition-based attribution introduces a validity failure mode absent from sequential procedures.

### 7.2 What it does not

**Correctness beyond internal consistency.** Our models reconcile to themselves. Except where public anchors are cited, they have not been checked against an independently produced bridge for the same entity. Reproducing a published bridge is the natural next step and we regard its absence as the most substantive gap.

**The sensitivity distribution.** Sobol indices are computed under an assumed independent uniform ±20% range on each driver. This is a documented placeholder, not a calibrated input, and every sensitivity result is conditional on it. Deriving ranges from observed dispersion is straightforward and would materially strengthen §5.3.

**Model construction.** The tool interrogates models; it does not build them. Drivers are supplied.

**Transaction modelling.** The DCF module attributes valuation movement. It contains no debt schedule, no purchase price allocation, no accretion/dilution, no comparables.

**Frequency in practice.** We show the effect exists and is sometimes large. We do not know how often published bridges are materially affected, which would require a survey we have not conducted.

### 7.3 On refusing to answer

Three components decline to return results under conditions where an answer would be available but unreliable: structural failure, non-monotone threshold search, invalid coalitions.

This is uncomfortable in a tool whose purpose is producing numbers, and it is the design position we would most defend. The failure mode these guards prevent is not an error message — it is a plausible, precise, confidently-presented figure that is wrong. In a variance workpaper that reaches a decision-maker, that failure is worse than no output, because nothing downstream will catch it.

---

## 8. Limitations

Consolidated; expanded in the repository's limitations register.

1. Internal consistency is established; independent correctness is not.
2. The ±20% sensitivity range is a documented assumption, uncalibrated.
3. Structural checks verify schema conformance, not economic validity.
4. Spreadsheet ingestion is restricted to generated workbooks.
5. Unlevered free cash flow will not reconcile to reported non-GAAP figures; exclusions are by design.
6. Interaction reporting covers pairs and one three-way term; higher orders are omitted and would understate non-additivity in larger driver sets.
7. Decision-priority weights are unjustified defaults.
8. Two datasets are synthetic and one real dataset contains illustrative values, each flagged per value.
9. Adding a *model* requires source changes; only adding a *company* is configuration-only.
10. No claim of audit, verification, or regulatory-grade status is made anywhere.

---

## 9. Conclusion

The variance bridge is among the most common artefacts in corporate finance, and it embeds an undisclosed methodological choice. The choice is usually invisible to the person making it and always invisible to the person reading the result. Its consequence is modest in some models and substantial in others, and — this is the operative point — the reader currently has no way to tell which case they are looking at.

The Shapley value removes the ambiguity at a cost that is trivial for models of the size this concerns. The interaction structure that produces the ambiguity can be reported directly, and the appropriate statistic for doing so is the one that does not permit cancellation. Both are implemented, tested, and reproducible.

The finding we did not expect is that the problem is worst in valuation. The discount rate and the perpetuity growth rate sit in the same denominator, and that single structural fact makes discounted cash flow analysis — the most externally scrutinised output in applied finance — the setting where sequential attribution is least defensible.

---

## References

Anderson, cited in Aurigemma, S. and Panko, R.R. (2010) 'The Detection of Human Spreadsheet Errors by Humans versus Inspection (Auditing) Software', *Proceedings of EuSpRIG*.

Aumann, R.J. and Shapley, L.S. (1974) *Values of Non-Atomic Games*. Princeton University Press.

Castro, J., Gómez, D. and Tejada, J. (2009) 'Polynomial calculation of the Shapley value based on sampling', *Computers & Operations Research*, 36(5), pp. 1726–1730.

Federal Reserve Board and OCC (2011) *Supervisory Guidance on Model Risk Management*, SR 11-7 / OCC Bulletin 2011-12.

Grabisch, M. and Roubens, M. (1999) 'An axiomatic approach to the concept of interaction among players in cooperative games', *International Journal of Game Theory*, 28(4), pp. 547–565.

Herman, J. and Usher, W. (2017) 'SALib: An open-source Python library for sensitivity analysis', *Journal of Open Source Software*, 2(9), p. 97.

ICAEW (2014) *Twenty Principles for Good Spreadsheet Practice*.

Panko, R.R. (1998) 'What we know about spreadsheet errors', *Journal of End User Computing*, 10(2), pp. 15–21.

Panko, R.R. (2008) 'Spreadsheet Errors: What We Know. What We Think We Can Do', *Proceedings of EuSpRIG*.

Saltelli, A. et al. (2010) 'Variance based sensitivity analysis of model output', *Computer Physics Communications*, 181(2), pp. 259–270.

Shapley, L.S. (1953) 'A Value for n-Person Games', in *Contributions to the Theory of Games II*. Princeton University Press, pp. 307–317.

Sobol, I.M. (2001) 'Global sensitivity indices for nonlinear mathematical models and their Monte Carlo estimates', *Mathematics and Computers in Simulation*, 55(1–3), pp. 271–280.

---

## Appendix A — Reproducing the results

```bash
pip install -r requirements.txt && pip install -e .
pytest tests/ -v                                    # 159 tests

bridgework compare data/illustrative/zoom_v1_drivers.yaml \
                   data/illustrative/zoom_v2_drivers.yaml --full
bridgework compare data/dcf_valuation/target_v1_drivers.yaml \
                   data/dcf_valuation/target_v2_drivers.yaml --full
```

Every run emits an audit manifest with an input hash, code version and environment fingerprint. Identical inputs and code version reproduce identical outputs byte for byte; this is enforced by the golden-dataset tests rather than asserted.

## Appendix B — Figures cited

| Quantity | Value | Source |
|---|---|---|
| Software FCF, V1 → V2 | $771.4950M → $810.4530M | `examples/zoom/` |
| Largest ordering spread (software) | $3.86M on a $12.99M driver | `sequential_vs_shapley.csv` |
| Valuation, V1 → V2 | $110.21 → $65.10 per share | `examples/dcf/` |
| Largest ordering spread (valuation) | $8.12/share on a $21.41 driver | `sequential_vs_shapley.csv` |
| L1 non-additivity by dataset | 1.9% / 5.0% / 9.9% / 24.9% | `pairwise_interactions.csv` (sums to the reported L1, higher-order term included) |
| Unchanged driver's sensitivity | Sobol total-order 0.17 | `dia_sobol.csv` |
| DCF terminal value share of EV | 84% | `compute_dcf_line_items` |
| Spreadsheet tie-out | $110.2103 both engines | §6.3 |
