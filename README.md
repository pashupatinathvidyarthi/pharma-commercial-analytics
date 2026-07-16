# Pharma Commercial Analytics Suite

A commercial analytics project built for **US healthcare/pharma consulting** roles —
directly mirrors the use cases in ProcDNA's Business Analyst JD: **HCP segmentation,
call planning, incentive compensation, and marketing analytics**, using **Excel, SQL,
and Python**.

## Business context

Pharma companies deploy sales reps to "detail" (call on) Healthcare Providers (HCPs)
to drive prescription (Rx) volume. Deciding **who to call, how often, and how to pay
reps for hitting targets** is the core of commercial analytics consulting work — this
project builds a working (synthetic-data) version of that whole pipeline.

## What's inside

| Module | Business Question | Tools |
|---|---|---|
| **HCP Segmentation** | Which HCPs are worth the most rep time? | Python (KMeans) + rule-based decile logic, SQL |
| **Call Planning** | How should limited rep capacity be allocated across HCPs? | Python (optimization heuristic), Excel |
| **Incentive Compensation (ICM)** | How much should each rep be paid based on quota attainment? | SQL, Excel (payout curve), Python simulator |
| **Marketing Mix** | Which specialty/region combos give the best return per call? | SQL, Excel pivot-style formulas |

## Project structure

```
pharma-commercial-analytics/
├── data/
│   ├── generate_data.py         # synthetic HCP/rep/call/sales data generator
│   ├── *.csv                    # generated datasets
│   └── model_outputs/           # segmentation + call plan + ICM outputs
├── sql/
│   ├── analysis_queries.sql     # 5 business questions in SQL
│   └── run_sql_analysis.py      # loads CSVs into SQLite, runs the SQL, saves results
├── notebooks/
│   └── segmentation_and_call_planning.py   # KMeans segmentation + call plan optimizer + ICM simulator
├── dashboard/
│   ├── app.py                   # Streamlit dashboard (4 tabs, Plotly charts)
│   └── build_excel.py           # generates the Excel deliverable
├── Commercial_Analytics_Report.xlsx   # Excel deliverable with live SUMIFS/COUNTIFS formulas
└── requirements.txt
```

## How to run

```bash
pip install -r requirements.txt

# 1. Generate the synthetic dataset
python data/generate_data.py

# 2. Run SQL analysis
python sql/run_sql_analysis.py

# 3. Run segmentation + call planning + ICM models
python notebooks/segmentation_and_call_planning.py

# 4. Rebuild the Excel report
python dashboard/build_excel.py

# 5. Launch the dashboard
streamlit run dashboard/app.py
```

## Key methodology notes

- **Segmentation** uses a business-rule cut (potential × receptivity quadrants) *and*
  an unsupervised KMeans clustering on the same features, then reports the agreement
  between the two — a real discussion point in segmentation consulting work (rule-based
  segments are explainable to stakeholders; clustering can reveal groupings the rules miss).
- **Call planning** enforces a minimum coverage floor per HCP, then allocates the
  remaining rep capacity to the highest expected-lift HCPs — reflecting the "concentrate
  effort where it pays off most" principle used in real Sales Force Effectiveness (SFE) work.
- **ICM** uses a standard 3-tier payout curve (threshold / target / accelerator),
  fully parameterized in the Excel `ICM_Assumptions` tab so the curve can be changed
  without touching formulas.
- All Excel formulas are live (`SUMIFS`, `COUNTIFS`, `AVERAGEIFS`) referencing a raw-data
  tab, so the workbook recalculates if the underlying data changes.

## Dataset

Synthetic — 600 HCPs across 5 specialties and 4 US regions, 40 reps, 52 weeks of call
activity, 12 months of Rx volume, and 4 quarters of rep quotas/actuals. Generated with a
fixed random seed for reproducibility.
