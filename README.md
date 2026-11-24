# Credit Bureau Business Rule Engine (BRE) - Mock Project

A small, end-to-end project that turns **credit bureau signals into automated lending decisions**, evaluates competing credit policies, and maps credit behaviour to **health and financial-protection offers**.

> **Note:** All data is synthetic. Default outcomes are simulated from a logistic function, so results demonstrate the *method*, not real-world portfolio performance.

## What this project does

1. **Generates a synthetic bureau extract** (5,000 applicants): bureau score, enquiries in last 6 months, max DPD in last 12 months, utilization, 3-month utilization change, tradelines, income.
2. **Runs a rule engine** with ordered hard-knockout rules (DPD, score, enquiry velocity, utilization) followed by approval bands A / B / C.
3. **Compares three policy versions** (`v1_baseline`, `v2_tight`, `v3_lenient`) on approval rate, default rate among approved, precision and share of defaults caught.
4. **Maps signals to triggers** - e.g. a utilization spike triggers a financial-stress protection + health cover offer.
5. **Analyses the output in SQL** - six queries including window functions and a score-cutoff analysis.

## Results

| Policy | Approval rate | Default rate (approved) | Precision (good) | Defaults caught |
|---|---|---|---|---|
| v1_baseline | 73.2% | 12.19% | 87.81% | 52.4% |
| v2_tight | 51.2% | 9.26% | 90.74% | 74.7% |
| v3_lenient | 83.9% | 14.35% | 85.65% | 35.8% |

![Policy tradeoff](outputs/policy_tradeoff.png)

**Band performance (v1)** - default rate rises monotonically as risk increases, confirming the rules rank-order risk correctly:

| Band | Applicants | Default rate |
|---|---|---|
| APPROVE_A (prime) | 753 | 4.25% |
| APPROVE_B (near-prime) | 1,780 | 11.85% |
| APPROVE_C (sub-prime) | 1,126 | 18.03% |
| DECLINE | 1,341 | 36.61% |

**Key findings**
- Tightening from v1 to v2 cuts the approved-book default rate from 12.2% to 9.3%, but costs about 22 points of approval rate. Whether that trade is worth it depends on margin and loss assumptions.
- Score is the dominant decline driver (70.8% of declines), followed by DPD breaches (15.6%).
- Default rate climbs steadily with enquiry velocity: 11.7% at 0 enquiries to 42.9% at 7+.
- Health offer segments: 741 prime applicants (4.2% default) for a premium family plan, 626 credit-active applicants for a membership upsell, and 137 stress-signal applicants for protection cover.

## Repo structure

```
bureau-bre-engine/
├── bureau_bre.py          # data generation, rule engine, policy evaluation, triggers, chart
├── run_sql.py             # loads output CSV into SQLite and runs the SQL file
├── sql/analysis.sql       # 6 analysis queries (aggregation, CASE, window functions)
├── outputs/
│   ├── bre_output_v1.csv      # per-applicant decisions, reasons and offers
│   ├── policy_comparison.csv  # policy metrics
│   └── policy_tradeoff.png    # approval vs. default tradeoff chart
├── requirements.txt
└── README.md
```

## How to run

```bash
pip install -r requirements.txt
python bureau_bre.py     # generates data, evaluates policies, writes outputs/
python run_sql.py        # runs sql/analysis.sql on the generated output
```

## Rule logic (v1_baseline)

| Order | Rule | Outcome |
|---|---|---|
| 1 | Max DPD in 12m >= 90 | Decline |
| 2 | Bureau score < 650 | Decline |
| 3 | Enquiries in 6m > 6 | Decline |
| 4 | Utilization > 90% | Decline |
| 5 | Score >= 750 and enquiries <= 2 | Approve - Band A |
| 6 | Score >= 700 | Approve - Band B |
| 7 | Otherwise | Approve - Band C (reduced limit) |

Policies are plain dictionaries of thresholds, so a new partner policy can be added as a new entry and compared immediately.

## Limitations and next steps

- Synthetic data with simulated outcomes; real bureau data has far messier structure (tradeline-level histories, account classifications, missing values).
- Rules are hand-set. A natural extension is training a logistic regression or gradient-boosted model and comparing it against the rule-based approach.
- Add unit tests for each rule and a config-file (YAML) policy loader.
- Add A/B test simulation for the health offer triggers (conversion lift, significance testing).

## Skills demonstrated

Python (pandas, numpy, matplotlib) · SQL (CASE, GROUP BY, CTEs, window functions) · rule-engine design · risk segmentation · policy evaluation (approval rate, default rate, precision) · signal-to-trigger mapping · reproducible pipelines
