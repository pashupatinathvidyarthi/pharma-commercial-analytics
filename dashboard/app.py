"""
Pharma Commercial Analytics Dashboard
Run: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

st.set_page_config(page_title="Pharma Commercial Analytics", layout="wide", page_icon="💊")

DATA = Path(__file__).resolve().parent.parent / "data"
MODEL = DATA / "model_outputs"

@st.cache_data
def load_data():
    hcps = pd.read_csv(MODEL / "hcps_segmented.csv")
    calls = pd.read_csv(DATA / "calls.csv")
    sales = pd.read_csv(DATA / "sales.csv")
    call_plan = pd.read_csv(MODEL / "optimized_call_plan.csv")
    icm = pd.read_csv(MODEL / "icm_payouts.csv")
    reps = pd.read_csv(DATA / "reps.csv")
    return hcps, calls, sales, call_plan, icm, reps

hcps, calls, sales, call_plan, icm, reps = load_data()

st.title("💊 Pharma Commercial Analytics Suite")
st.caption("HCP Segmentation · Call Planning · Incentive Compensation · Marketing Mix — "
           "built for US healthcare/pharma commercial analytics use cases")

tab1, tab2, tab3, tab4 = st.tabs(
    ["🎯 HCP Segmentation", "📞 Call Planning", "💰 Incentive Compensation", "📊 Marketing Mix"]
)

# ============================================================
# TAB 1 — Segmentation
# ============================================================
with tab1:
    st.subheader("HCP Segmentation: Potential × Receptivity")

    col1, col2, col3, col4 = st.columns(4)
    seg_counts = hcps["segment"].value_counts()
    for col, seg in zip([col1, col2, col3, col4], ["Key Target", "Growth", "Maintain", "Low Priority"]):
        col.metric(seg, int(seg_counts.get(seg, 0)))

    fig = px.scatter(
        hcps, x="potential_score", y="receptivity_score", color="segment",
        hover_data=["hcp_id", "specialty", "region"],
        title="HCP Segmentation Map (rule-based)",
        color_discrete_map={
            "Key Target": "#d62728", "Growth": "#ff7f0e",
            "Maintain": "#1f77b4", "Low Priority": "#7f7f7f"
        }
    )
    fig.add_vline(x=60, line_dash="dash", line_color="gray")
    fig.add_hline(y=55, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Rule-based vs. KMeans (data-driven) segmentation agreement**")
    agreement = (hcps["segment"] == hcps["kmeans_segment"]).mean()
    st.info(
        f"Agreement between the business-rule segmentation and an unsupervised KMeans "
        f"clustering on the same features is **{agreement:.1%}** — highlighting where "
        f"a purely rule-based (decile-cutoff) approach and a data-driven clustering approach diverge, "
        f"a common discussion point in real segmentation projects."
    )

    seg_by_spec = hcps.groupby(["specialty", "segment"]).size().reset_index(name="count")
    fig2 = px.bar(seg_by_spec, x="specialty", y="count", color="segment", barmode="stack",
                  title="Segment Mix by Specialty")
    st.plotly_chart(fig2, use_container_width=True)

# ============================================================
# TAB 2 — Call Planning
# ============================================================
with tab2:
    st.subheader("Call Plan: Actual vs. Target vs. Optimized")

    target_freq = {"Key Target": 2.0, "Growth": 1.5, "Maintain": 1.0, "Low Priority": 0.4}
    calls_per_hcp = calls.groupby("hcp_id").size().rename("total_calls").reset_index()
    hcp_calls = hcps.merge(calls_per_hcp, on="hcp_id", how="left").fillna({"total_calls": 0})
    hcp_calls["actual_calls_per_month"] = hcp_calls["total_calls"] / 12
    hcp_calls["target_calls_per_month"] = hcp_calls["segment"].map(target_freq)

    summary = hcp_calls.groupby("segment")[["actual_calls_per_month", "target_calls_per_month"]].mean().reset_index()
    summary = summary.merge(
        call_plan.groupby("segment")["optimized_calls_per_month"].mean().reset_index(),
        on="segment"
    )
    summary_melt = summary.melt(id_vars="segment", var_name="metric", value_name="calls_per_month")
    fig3 = px.bar(summary_melt, x="segment", y="calls_per_month", color="metric", barmode="group",
                  title="Avg Calls/Month per HCP: Actual vs Target vs Optimized Allocation")
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown(
        "**Optimization logic:** every HCP gets a coverage floor; remaining rep capacity "
        "is allocated to the top 50% of HCPs by `expected_lift = potential × receptivity`, "
        "concentrating effort on the highest-return targets rather than spreading calls evenly."
    )

    st.dataframe(
        call_plan.sort_values("optimized_calls_per_month", ascending=False).head(20),
        use_container_width=True
    )

# ============================================================
# TAB 3 — Incentive Compensation
# ============================================================
with tab3:
    st.subheader("Incentive Compensation Simulator")

    q_filter = st.selectbox("Quarter", sorted(icm["quarter"].unique()))
    icm_q = icm[icm["quarter"] == q_filter]

    c1, c2, c3 = st.columns(3)
    c1.metric("Avg Attainment", f"{icm_q['attainment'].mean()*100:.1f}%")
    c2.metric("Reps at Accelerator (>=110%)", int((icm_q["attainment"] >= 1.10).sum()))
    c3.metric("Total Payout ($)", f"${icm_q['incentive_payout_usd'].sum():,.0f}")

    fig4 = px.histogram(icm_q, x="attainment", nbins=25, title=f"Attainment Distribution — {q_filter}")
    fig4.add_vline(x=0.8, line_dash="dash", line_color="orange", annotation_text="Threshold")
    fig4.add_vline(x=1.0, line_dash="dash", line_color="green", annotation_text="Target")
    fig4.add_vline(x=1.10, line_dash="dash", line_color="red", annotation_text="Accelerator")
    st.plotly_chart(fig4, use_container_width=True)

    st.markdown("**Payout curve used:** <80% attainment = 0% payout · 80-99% = 50% · 100-109% = 100% · ≥110% = 150% (accelerator)")
    st.dataframe(icm_q.merge(reps, on="rep_id")[
        ["rep_id", "rep_name", "region", "quota_volume", "actual_volume", "attainment", "incentive_payout_usd"]
    ].sort_values("attainment", ascending=False), use_container_width=True)

# ============================================================
# TAB 4 — Marketing Mix
# ============================================================
with tab4:
    st.subheader("Marketing Mix: Rx Efficiency by Specialty × Region")

    mm = calls.merge(hcps[["hcp_id", "specialty", "region"]], on="hcp_id")
    mm_calls = mm.groupby(["specialty", "region"]).size().rename("total_calls").reset_index()
    mm_sales = sales.merge(hcps[["hcp_id", "specialty", "region"]], on="hcp_id") \
                     .groupby(["specialty", "region"])["rx_volume"].sum().reset_index()
    mm_final = mm_calls.merge(mm_sales, on=["specialty", "region"])
    mm_final["rx_per_call"] = (mm_final["rx_volume"] / mm_final["total_calls"]).round(2)

    fig5 = px.density_heatmap(
        mm_final, x="region", y="specialty", z="rx_per_call",
        title="Rx Volume per Call (Efficiency) by Specialty × Region", text_auto=True,
        color_continuous_scale="RdYlGn"
    )
    st.plotly_chart(fig5, use_container_width=True)

    st.markdown(
        "**Business read:** cells with high Rx-per-call are candidates for reallocating rep time "
        "or increasing detailing investment; low-efficiency cells suggest channel or message mix "
        "should be revisited before adding more calls."
    )

    st.dataframe(mm_final.sort_values("rx_per_call", ascending=False), use_container_width=True)

st.divider()
st.caption("Synthetic dataset generated for portfolio purposes. Methodology mirrors real-world "
           "pharma commercial analytics workflows: HCP segmentation, call plan design, "
           "incentive compensation, and marketing mix modeling.")

