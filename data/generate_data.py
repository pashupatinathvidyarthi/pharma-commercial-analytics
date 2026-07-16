"""
Generates a synthetic US pharma commercial dataset:
- hcps.csv          : Healthcare Provider (HCP) master + potential/receptivity
- reps.csv          : Sales rep / territory master
- calls.csv         : Rep-HCP call activity log (12 months)
- sales.csv         : Monthly product sales (Rx volume) by HCP
- rep_targets.csv   : Quarterly quota for incentive compensation

Run: python generate_data.py
Output: writes CSVs into ../data/
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

rng = np.random.default_rng(42)

# ---------------------------------------------------------------
# 1. HCP master data
# ---------------------------------------------------------------
N_HCP = 600
SPECIALTIES = ["Cardiology", "Endocrinology", "Oncology", "Neurology", "Primary Care"]
REGIONS = ["Northeast", "Midwest", "South", "West"]

hcps = pd.DataFrame({
    "hcp_id": [f"HCP{i:04d}" for i in range(N_HCP)],
    "specialty": rng.choice(SPECIALTIES, N_HCP, p=[0.15, 0.15, 0.15, 0.15, 0.40]),
    "region": rng.choice(REGIONS, N_HCP),
    "decile": rng.integers(1, 11, N_HCP),           # prescribing decile (1=low,10=high writer)
    "patient_volume": rng.integers(50, 2000, N_HCP),
})

# Potential (future Rx opportunity) and Receptivity (openness to detailing) drive segmentation
hcps["potential_score"] = (
    hcps["decile"] * 8 + hcps["patient_volume"] / 40 + rng.normal(0, 8, N_HCP)
).clip(0, 100)
hcps["receptivity_score"] = rng.normal(55, 20, N_HCP).clip(0, 100)

# ---------------------------------------------------------------
# 2. Rep / territory master
# ---------------------------------------------------------------
N_REP = 40
reps = pd.DataFrame({
    "rep_id": [f"REP{i:03d}" for i in range(N_REP)],
    "rep_name": [f"Rep_{i:03d}" for i in range(N_REP)],
    "region": rng.choice(REGIONS, N_REP),
    "tenure_years": rng.integers(0, 15, N_REP),
})

hcps["rep_id"] = hcps["region"].apply(
    lambda r: rng.choice(reps.loc[reps.region == r, "rep_id"].values)
)

# ---------------------------------------------------------------
# 3. Call activity log (weekly cadence over 12 months)
# ---------------------------------------------------------------
start = datetime(2025, 1, 6)
weeks = [start + timedelta(weeks=w) for w in range(52)]

# Target call frequency by segment (defined later using potential x receptivity)
def segment_of(row):
    if row.potential_score >= 60 and row.receptivity_score >= 55:
        return "Key Target"
    elif row.potential_score >= 60:
        return "Growth"
    elif row.receptivity_score >= 55:
        return "Maintain"
    else:
        return "Low Priority"

hcps["segment"] = hcps.apply(segment_of, axis=1)

TARGET_FREQ = {"Key Target": 2, "Growth": 1.5, "Maintain": 1, "Low Priority": 0.4}  # calls/month

call_rows = []
for _, hcp in hcps.iterrows():
    target = TARGET_FREQ[hcp.segment]
    for wk in weeks:
        # probability a call happens this week, with rep-level noise (some reps under/over deliver)
        p = min(target / 4.3, 0.9) * rng.uniform(0.6, 1.15)
        if rng.random() < p:
            call_rows.append({
                "hcp_id": hcp.hcp_id,
                "rep_id": hcp.rep_id,
                "call_date": wk.date().isoformat(),
                "call_type": rng.choice(["In-person", "Virtual", "Speaker Program"], p=[0.65, 0.30, 0.05]),
                "duration_min": rng.integers(8, 30),
            })

calls = pd.DataFrame(call_rows)

# ---------------------------------------------------------------
# 4. Monthly Rx sales, influenced by segment, call volume, and baseline
# ---------------------------------------------------------------
months = pd.date_range("2025-01-01", periods=12, freq="MS")
calls["month"] = pd.to_datetime(calls.call_date).values.astype("datetime64[M]")
monthly_calls = calls.groupby(["hcp_id", "month"]).size().rename("call_count").reset_index()

sales_rows = []
for _, hcp in hcps.iterrows():
    base = hcp.patient_volume * (hcp.decile / 10) * 0.4
    for m in months:
        mc = monthly_calls[(monthly_calls.hcp_id == hcp.hcp_id) & (monthly_calls.month == m)]
        n_calls = int(mc.call_count.iloc[0]) if len(mc) else 0
        lift = 1 + 0.06 * n_calls * (hcp.receptivity_score / 100)
        seasonal = 1 + 0.05 * np.sin(2 * np.pi * m.month / 12)
        noise = rng.normal(1, 0.08)
        rx = max(0, base * lift * seasonal * noise)
        sales_rows.append({"hcp_id": hcp.hcp_id, "month": m.date().isoformat(), "rx_volume": round(rx, 1)})

sales = pd.DataFrame(sales_rows)

# ---------------------------------------------------------------
# 5. Rep quarterly quota + attainment (for incentive compensation)
# ---------------------------------------------------------------
sales_m = sales.copy()
sales_m["month"] = pd.to_datetime(sales_m.month)
sales_hcp_rep = sales_m.merge(hcps[["hcp_id", "rep_id"]], on="hcp_id")
sales_hcp_rep["quarter"] = sales_hcp_rep.month.dt.quarter
rep_actuals = sales_hcp_rep.groupby(["rep_id", "quarter"])["rx_volume"].sum().reset_index()
rep_actuals.rename(columns={"rx_volume": "actual_volume"}, inplace=True)

rep_targets_rows = []
for _, r in reps.iterrows():
    for q in [1, 2, 3, 4]:
        actual = rep_actuals[(rep_actuals.rep_id == r.rep_id) & (rep_actuals.quarter == q)]
        actual_val = actual.actual_volume.iloc[0] if len(actual) else 0
        # quota set with some noise around a rolling territory potential, so attainment varies 80-120%
        quota = actual_val / rng.uniform(0.8, 1.2) if actual_val > 0 else rng.uniform(500, 2000)
        rep_targets_rows.append({
            "rep_id": r.rep_id, "quarter": f"2025-Q{q}",
            "quota_volume": round(quota, 1), "actual_volume": round(actual_val, 1)
        })

rep_targets = pd.DataFrame(rep_targets_rows)

# ---------------------------------------------------------------
# Save
# ---------------------------------------------------------------
hcps.drop(columns=["segment"]).to_csv("hcps.csv", index=False)  # segment recomputed in analysis (as taught)
hcps.to_csv("hcps_with_segment.csv", index=False)  # convenience copy incl. segment for dashboard speed
reps.to_csv("reps.csv", index=False)
calls.drop(columns=["month"]).to_csv("calls.csv", index=False)
sales.to_csv("sales.csv", index=False)
rep_targets.to_csv("rep_targets.csv", index=False)

print("Generated:")
print(f"  hcps: {len(hcps)} | reps: {len(reps)} | calls: {len(calls)} | sales rows: {len(sales)} | rep_targets: {len(rep_targets)}")

