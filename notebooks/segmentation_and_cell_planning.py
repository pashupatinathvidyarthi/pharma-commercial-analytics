"""
Core analytics module for the ProcDNA-style commercial analytics project.

1. HCP Segmentation      -> KMeans clustering on potential + receptivity (replaces
                             the rule-based segment with a data-driven one, then
                             compares the two).
2. Call Plan Optimization -> given a fixed rep capacity (calls/month), allocate
                             calls across HCPs to maximize expected Rx lift,
                             respecting a minimum-coverage floor per segment.
3. Incentive Compensation -> quota-attainment payout simulator with configurable
                             accelerator curve, used to sanity-check the SQL ICM output.

Outputs saved to ../data/model_outputs/
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "model_outputs"
OUT.mkdir(exist_ok=True)

hcps = pd.read_csv(DATA / "hcps_with_segment.csv")
sales = pd.read_csv(DATA / "sales.csv")
calls = pd.read_csv(DATA / "calls.csv")

# ------------------------------------------------------------------
# 1. KMeans-based segmentation (data-driven, mirrors real SFE projects)
# ------------------------------------------------------------------
features = hcps[["potential_score", "receptivity_score", "decile", "patient_volume"]].copy()
X = StandardScaler().fit_transform(features)

km = KMeans(n_clusters=4, n_init=10, random_state=42)
hcps["kmeans_cluster"] = km.fit_predict(X)

# Label clusters by their mean potential/receptivity so labels are business-readable
cluster_profile = hcps.groupby("kmeans_cluster")[["potential_score", "receptivity_score"]].mean()
cluster_profile = cluster_profile.sort_values("potential_score", ascending=False)
rank_to_label = {}
labels_pool = ["Key Target", "Growth", "Maintain", "Low Priority"]
for i, (cluster_id, row) in enumerate(cluster_profile.iterrows()):
    rank_to_label[cluster_id] = labels_pool[i] if i < len(labels_pool) else f"Segment {i}"
hcps["kmeans_segment"] = hcps["kmeans_cluster"].map(rank_to_label)

agreement = (hcps["segment"] == hcps["kmeans_segment"]).mean()
print(f"Rule-based vs KMeans segment agreement: {agreement:.1%}")

hcps.to_csv(OUT / "hcps_segmented.csv", index=False)

# ------------------------------------------------------------------
# 2. Call plan optimization
#    Maximize sum(expected_lift) subject to total call budget constraint.
#    expected_lift ~ receptivity * potential  (simple greedy knapsack-style allocation)
# ------------------------------------------------------------------
MONTHLY_CALL_BUDGET_PER_REP = 60   # capacity constraint
reps_n = hcps["rep_id"].nunique()
TOTAL_BUDGET = MONTHLY_CALL_BUDGET_PER_REP * reps_n

hcps["expected_lift_per_call"] = (hcps["potential_score"] * hcps["receptivity_score"]) / 100
# Minimum coverage floor: every HCP gets >=1 call every other month, remaining budget goes to top lift
MIN_FLOOR_CALLS = 0.5
hcps["floor_calls"] = MIN_FLOOR_CALLS
remaining_budget = TOTAL_BUDGET - hcps["floor_calls"].sum()

hcps_sorted = hcps.sort_values("expected_lift_per_call", ascending=False).copy()
# Allocate remaining budget proportionally to lift score among top 50% of HCPs (concentration principle)
top_half = hcps_sorted.iloc[: len(hcps_sorted) // 2]
weight = top_half["expected_lift_per_call"] / top_half["expected_lift_per_call"].sum()
extra_calls = (weight * remaining_budget).round(2)

hcps["optimized_calls_per_month"] = hcps["floor_calls"]
hcps.loc[top_half.index, "optimized_calls_per_month"] += extra_calls

call_plan = hcps[[
    "hcp_id", "segment", "kmeans_segment", "potential_score", "receptivity_score",
    "expected_lift_per_call", "optimized_calls_per_month"
]].sort_values("optimized_calls_per_month", ascending=False)
call_plan.to_csv(OUT / "optimized_call_plan.csv", index=False)

print("\nCall plan by segment (avg optimized calls/month):")
print(hcps.groupby("segment")["optimized_calls_per_month"].mean().round(2))

# ------------------------------------------------------------------
# 3. Incentive compensation payout simulator
# ------------------------------------------------------------------
rep_targets = pd.read_csv(DATA / "rep_targets.csv")

def payout_pct(attainment):
    if attainment >= 1.10:
        return 1.50
    elif attainment >= 1.00:
        return 1.00
    elif attainment >= 0.80:
        return 0.50
    return 0.0

rep_targets["attainment"] = rep_targets["actual_volume"] / rep_targets["quota_volume"]
rep_targets["payout_pct"] = rep_targets["attainment"].apply(payout_pct)
BASE_INCENTIVE = 5000  # illustrative quarterly target incentive $
rep_targets["incentive_payout_usd"] = (BASE_INCENTIVE * rep_targets["payout_pct"]).round(0)

rep_targets.to_csv(OUT / "icm_payouts.csv", index=False)
print("\nICM payout distribution (count of reps per tier, all quarters):")
print(rep_targets["payout_pct"].value_counts().sort_index())

print("\nAll model outputs saved to:", OUT)

