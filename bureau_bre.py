"""
Mock Credit Bureau Business Rule Engine (BRE)

Pipeline:
  1. Generate a synthetic bureau extract (score, enquiries, DPD, utilization...)
  2. Apply policy rules (hard knockouts + approval bands A/B/C)
  3. Compare three policy versions (approval rate, default rate, precision)
  4. Map credit signals to health / protection offer triggers
  5. Save CSV outputs and an approval-vs-default tradeoff chart

Run: python bureau_bre.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path(__file__).parent / "outputs"
OUT.mkdir(exist_ok=True)

rng = np.random.default_rng(42)
N = 5000

# ---------- 1. Synthetic bureau extract ----------
df = pd.DataFrame({
    "applicant_id": np.arange(1, N + 1),
    "bureau_score": np.clip(rng.normal(710, 70, N), 300, 900).astype(int),
    "enq_6m": rng.poisson(2.2, N),                       # enquiry velocity
    "active_tradelines": rng.integers(0, 12, N),
    "max_dpd_12m": rng.choice([0, 30, 60, 90], N, p=[0.80, 0.10, 0.06, 0.04]),
    "utilization_pct": np.clip(rng.normal(45, 25, N), 0, 100).round(1),
    "util_change_3m": rng.normal(0, 8, N).round(1),      # change in utilization
    "monthly_income": rng.integers(15000, 120000, N),
})

# Hidden "true" default outcome so rules can be evaluated (simulated)
z = (-3.0
     - 0.012 * (df.bureau_score - 700)
     + 0.25 * df.enq_6m
     + 0.012 * df.max_dpd_12m
     + 0.015 * df.utilization_pct)
df["defaulted"] = (rng.random(N) < 1 / (1 + np.exp(-z))).astype(int)


# ---------- 2. Rule engine ----------
def decide(row, policy):
    """Return (decision, reason). Rules are evaluated in order."""
    if row.max_dpd_12m >= policy["max_dpd"]:
        return "DECLINE", "DPD breach"
    if row.bureau_score < policy["min_score"]:
        return "DECLINE", "Low score"
    if row.enq_6m > policy["max_enq_6m"]:
        return "DECLINE", "High enquiry velocity"
    if row.utilization_pct > policy["max_util"]:
        return "DECLINE", "High utilization"
    if row.bureau_score >= 750 and row.enq_6m <= 2:
        return "APPROVE_A", "Prime"
    if row.bureau_score >= 700:
        return "APPROVE_B", "Near-prime"
    return "APPROVE_C", "Sub-prime (reduced limit)"


POLICIES = {
    "v1_baseline": dict(min_score=650, max_dpd=90, max_enq_6m=6, max_util=90),
    "v2_tight":    dict(min_score=680, max_dpd=60, max_enq_6m=4, max_util=80),
    "v3_lenient":  dict(min_score=620, max_dpd=90, max_enq_6m=8, max_util=95),
}


# ---------- 3. Evaluate each policy ----------
def evaluate(df, name, policy):
    out = df.apply(lambda r: decide(r, policy), axis=1, result_type="expand")
    d = df.copy()
    d["decision"], d["reason"] = out[0], out[1]
    approved = d[d.decision.str.startswith("APPROVE")]
    declined = d[d.decision == "DECLINE"]
    return d, {
        "policy": name,
        "approval_rate_pct": round(len(approved) / len(d) * 100, 1),
        "default_rate_approved_pct": round(approved.defaulted.mean() * 100, 2),
        "precision_good_pct": round((1 - approved.defaulted.mean()) * 100, 2),
        "defaults_caught_pct": round(declined.defaulted.sum() / d.defaulted.sum() * 100, 1),
    }


results, scored = [], {}
for name, pol in POLICIES.items():
    scored[name], summary = evaluate(df, name, pol)
    results.append(summary)

comparison = pd.DataFrame(results)
print("\n=== POLICY COMPARISON ===")
print(comparison.to_string(index=False))
comparison.to_csv(OUT / "policy_comparison.csv", index=False)

best = scored["v1_baseline"]
bands = best.groupby("decision").agg(
    applicants=("applicant_id", "count"),
    default_rate_pct=("defaulted", lambda x: round(x.mean() * 100, 2)),
    avg_score=("bureau_score", "mean")).round(1)
print("\n=== BAND PERFORMANCE (v1) ===")
print(bands)

print("\n=== DECLINE REASONS (v1) ===")
print(best[best.decision == "DECLINE"].reason.value_counts())


# ---------- 4. Signal-to-trigger: health / protection offer ----------
def health_trigger(r):
    if r.util_change_3m > 10 and r.utilization_pct > 60:
        return "Financial-stress protection + health cover"
    if r.enq_6m >= 4 and r.decision.startswith("APPROVE"):
        return "Credit-active: health membership upsell"
    if r.decision == "APPROVE_A":
        return "Prime: premium family health plan"
    return "No offer"


best = best.assign(offer=best.apply(health_trigger, axis=1))
print("\n=== HEALTH OFFER TRIGGERS ===")
print(best.offer.value_counts())

best.to_csv(OUT / "bre_output_v1.csv", index=False)


# ---------- 5. Tradeoff chart ----------
fig, ax = plt.subplots(figsize=(7, 4.5))
plot_df = comparison.sort_values("approval_rate_pct")
ax.plot(plot_df.approval_rate_pct, plot_df.default_rate_approved_pct,
        "-o", color="#2a6f97", lw=2, ms=9)
for _, r in plot_df.iterrows():
    ax.annotate(r.policy, (r.approval_rate_pct, r.default_rate_approved_pct),
                textcoords="offset points", xytext=(8, -16), fontsize=9)
ax.set_xlim(plot_df.approval_rate_pct.min() - 5, plot_df.approval_rate_pct.max() + 8)
ax.set_ylim(plot_df.default_rate_approved_pct.min() - 1, plot_df.default_rate_approved_pct.max() + 1)
ax.set_xlabel("Approval rate (%)")
ax.set_ylabel("Default rate among approved (%)")
ax.set_title("Approval vs. risk tradeoff across policy versions")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(OUT / "policy_tradeoff.png", dpi=150)

print(f"\nSaved outputs to: {OUT}")
