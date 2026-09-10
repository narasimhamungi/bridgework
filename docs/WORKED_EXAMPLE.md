# A Worked Example

*Read this first if you want to know what Bridgework is for. No code, no
game theory. One variance, walked end to end the way you would actually
talk about it in a meeting.*

---

## The situation

You are an FP&A analyst. Last month you published a forecast. This month
you have published a revised one. Free cash flow moved from **$771.5M** to
**$810.5M** — up **$39.0M**.

Three assumptions changed:

| Driver | Last month | This month | Change |
|---|---:|---:|---|
| Revenue growth | 3.1% | 5.5% | +240bps — enterprise demand recovered |
| Operating expense (% of revenue) | 52.0% | 49.5% | −250bps — cost discipline held |
| Capital expenditure (% of revenue) | 3.0% | 4.5% | +150bps — AI infrastructure build |

Your CFO asks the ordinary question: **why did cash flow go up $39M?**

---

## What you would normally do

Build a bridge. Start at last month's number, switch one assumption at a
time, record what each does.

| Step | Driver | Running FCF | Impact |
|---|---|---:|---:|
| Start | — | 771.5 | — |
| 1 | Revenue growth 3.1% → 5.5% | 784.2 | **+12.7** |
| 2 | Opex 52.0% → 49.5% | 882.1 | **+97.9** |
| 3 | Capex 3.0% → 4.5% | 810.5 | **−71.6** |
| | | | **+39.0 ✓** |

It reconciles exactly. You put it in the deck:

> *"Cost discipline drove the improvement, adding $97.9M. Revenue growth
> contributed a further $12.7M. Both were partly offset by $71.6M of
> incremental capex."*

That is a completely normal, competent piece of variance commentary. Every
number in it is arithmetically correct.

**And it is one of six possible answers.**

---

## The part nobody sees

You walked revenue → opex → capex. That was not a decision you consciously
made; it is the order the drivers sit in on your schedule.

Had you walked **opex → revenue → capex**, the same model, with the same
assumptions, would have produced this:

| Driver | Your order | Other order | Difference |
|---|---:|---:|---:|
| Revenue growth | +12.69 | **+14.92** | 2.23 |
| Opex | +97.91 | **+95.68** | 2.23 |
| Capex | −71.64 | −71.64 | — |

Both bridges reconcile to +$39.0M. Both are arithmetically flawless.
Neither page tells the reader an ordering was chosen.

Across all six orderings, revenue growth's credited contribution ranges
from **+$11.06M to +$14.92M**. That is a **$3.86M spread on a $13M line** —
roughly 30% of the number — created entirely by which column you happened
to type first.

If someone challenges your $12.7M in a meeting, you cannot defend it. It is
not wrong. It is just not the only right answer, and you have no principled
reason for preferring it.

---

## Why this happens

Because opex is a *percentage of revenue*.

Move revenue growth first, and the opex saving then applies to a bigger
revenue base — so opex gets credited with more. Move opex first, and the
saving applies to the smaller base, leaving more of the benefit to be
picked up by revenue when it moves.

The two drivers share a term. Their combined effect is **$2.23M larger**
than the sum of their separate effects. That $2.23M is real, and it has to
be credited to *somebody* — a sequential bridge always hands it to whichever
driver happened to move second.

Same story with revenue and capex, in the other direction: **−$1.63M**.

None of this is an error. It is a property of the model. The problem is
that the bridge silently resolves it by a coin-flip and presents the result
as fact.

---

## What Bridgework does instead

It computes **all six orderings** and takes the average contribution of
each driver across them. This is the Shapley value — the standard tool for
splitting a joint result among contributors when their effects interact.

| Driver | Your bridge | Range across orderings | **Bridgework** |
|---|---:|---:|---:|
| Revenue growth | +12.69 | +11.06 to +14.92 | **+12.99** |
| Opex | +97.91 | +95.68 to +97.91 | **+96.79** |
| Capex | −71.64 | −71.64 to −70.01 | **−70.82** |
| **Total** | **+39.0** | | **+39.0 ✓** |

Two properties matter here:

1. **It still reconciles exactly.** You have not given up the thing that
   made the bridge trustworthy.
2. **It does not depend on ordering.** There is no longer an undisclosed
   choice sitting underneath the number. Whoever runs it, in whatever
   order, gets $12.99M.

It also tells you **how much ambiguity it removed**: the "L1" figure of
**$3.86M**, or 9.9% of the total move. That is the size of the interaction
you were previously assigning by accident.

---

## What you would now say to the CFO

> *"Free cash flow improved $39.0M. Cost discipline is the main driver at
> $96.8M, revenue growth adds $13.0M, and capex takes back $70.8M.*
>
> *One thing worth flagging: revenue and opex interact — the cost saving is
> worth more on a bigger revenue base — so about $3.9M of this movement
> can't be cleanly assigned to a single driver. I've split it on a
> consistent basis rather than letting the order I built the bridge in
> decide. Under the old approach that $3.9M would have landed wherever I
> happened to put revenue in the sequence."*

That is a stronger position than the original commentary in three ways.
The number is defensible under challenge. The ambiguity is disclosed rather
than hidden. And it is reproducible — anyone re-running it gets the same
answer.

---

## The thing you would have missed entirely

Bridgework also runs a sensitivity analysis, and it flags something the
variance bridge is structurally incapable of seeing.

**Cost of goods sold did not change this month.** It contributed nothing to
the $39M, so it is correctly absent from every bridge, in every ordering.

But it accounts for **17% of the model's total output uncertainty** —
second only to opex. It is the second most dangerous assumption in the
model, and your variance commentary is silent on it *by construction*,
because it happens not to have moved.

| Driver | Contribution to what happened | Share of what could happen |
|---|---:|---:|
| Opex | +$96.8M | 81% |
| **COGS** | **$0 — didn't move** | **17%** |
| Revenue growth | +$13.0M | ~0% |
| Capex | −$70.8M | ~0% |

Two different questions. *"Who caused the change?"* and *"what should I be
worried about?"* have almost opposite answers here. Revenue growth explains
a third of the movement and almost none of the risk; COGS explains none of
the movement and a sixth of the risk.

A variance report that only answers the first question is not wrong. It is
just quiet about the thing most likely to hurt you next quarter.

---

## Where this gets serious: valuation

The Zoom model is nearly linear, so the interaction is modest — 9.9%.

Run the same analysis on a **DCF** and it roughly triples, to **24.9%**.
The reason is structural: terminal value is

```
FCF₅ × (1 + g) / (WACC − g)
```

The discount rate and the perpetuity growth rate sit in the *same
denominator*, so they interact violently. On a stock valued near $110, the
credited impact of the discount rate swings **$8.12 per share** depending
on the order you walk the drivers.

The practical consequence: **the ordering problem is worst in valuation
work** — the most externally scrutinised output in finance, the one that
goes in front of investment committees and clients. That was the single
most useful finding in this project, and it was not predicted; it was
measured.

---

## How you would actually run this

Two files, seven numbers each. **Not a 10-K, not a spreadsheet dump** — the
drivers you already decided when you built your forecast.

```yaml
# last_month.yaml
schema_version: "1.0.0"
drivers:
  revenue_prior: 4527.0     # $M
  revenue_growth: 0.031     # 3.1%
  cogs_pct: 0.240
  opex_pct: 0.520
  tax_rate: 0.180
  nwc_pct: 0.050
  capex_pct: 0.030
```

```bash
bridgework compare last_month.yaml this_month.yaml --full
```

**If you have line items rather than ratios**, `bridgework derive` computes
them for you and shows the arithmetic:

```bash
bridgework derive --template lines_v1.yaml    # blank form
bridgework derive lines_v1.yaml lines_v2.yaml # writes both driver files
```

It is arithmetic only — it does not read 10-Ks or annual reports. Deciding
what counts as operating expense is your call, not the tool's.

Out comes `report.html` — a self-contained workpaper you can email or
attach to a close file — plus CSVs, charts, and two formula-driven Excel
workbooks you can open and trace precedents in.

It takes about a second.

---

## What this is not

Honesty matters more than pitch here.

- **It does not read your 10-K or your spreadsheet.** You supply the
  drivers. It explains movement; it does not extract or build.
- **It does not build models.** Seven drivers, one output. That is a
  substrate for the attribution question, not a modelling tool.
- **It will not fit most real models as-is.** The seven-role schema suits
  a compact operating model. A bank, a segmented conglomerate, a levered
  industrial — none map cleanly, and the tool will not warn you (see
  `docs/ADVERSARIAL_REVIEW.md`).
- **It does not tell you whether your assumptions are right.** It tells you
  what they imply and how confidently that can be attributed.

---

## The one-sentence version

**Variance bridges contain a hidden choice — the order you walk the
drivers — that changes the numbers you report and that nobody discloses.
Bridgework removes the choice, reconciles exactly as before, and tells you
how big the ambiguity was.**
