# Phase 0 Findings (reference)

Phase 0 was a proof-of-concept: a compact 7-driver Zoom Communications FCF
model, exercised through a sequential bridge and exact Shapley attribution,
to answer one question — does the Variance Bridge produce enough analytical
value to justify making it a central component of Bridgework?

**Locked numerical results** (independently re-verified in Phase 1,
`tests/test_report_golden.py::test_golden_locked_headline_numbers`):

| | Value |
|---|---:|
| V1 FCF | $771.4949616M |
| V2 FCF | $810.4529655M |
| Total variance | +$38.958M |

**Shapley attribution:**

| Driver | Shapley ($M) | % of variance |
|---|---:|---:|
| revenue_growth | +12.989 | 33% |
| opex_pct | +96.794 | 248% |
| capex_pct | −70.825 | −182% |

**Sequential ordering range vs Shapley:**

| Driver | Seq min | Seq max | Range | Shapley |
|---|---:|---:|---:|---:|
| revenue_growth | +11.060 | +14.917 | 3.857 | +12.989 |
| opex_pct | +95.680 | +97.908 | 2.227 | +96.794 |
| capex_pct | −71.640 | −70.010 | 1.630 | −70.825 |

**Verdict: MODIFY.** The concept works — Shapley closes the ordering gap
and reconciles exactly — but two changes were required before Phase 1:
ship Shapley as the primary number with sequential as a diagnostic
whisker, and report the interaction/non-additivity structure explicitly
rather than leaving it implicit in a single ordering choice. Both are
implemented in this Phase-1 codebase.

Four corrections were mandated for all downstream documentation
(Blueprint §4.4), all applied in Phase 1:
1. "Interaction effect" retired in favor of precisely-named net vs. L1
   non-additivity.
2. Full two-way interaction table reported (not just the net figure).
3. FY25 GAAP operating income citation corrected ($813.3M/17.4%, not
   $1,123.6M/~24% which was actually FY26) — see
   `data/illustrative/assumptions.md` and `docs/decision_diary.md`
   Decision 1.
4. The "~30% swing" framing reworded as scenario-specific, not universal.

Full detail: `Financecore_prompt_and_responses.pdf` (Phase 0 prompt and
response) and the Master Research & Architecture Blueprint v1.0 §B.
