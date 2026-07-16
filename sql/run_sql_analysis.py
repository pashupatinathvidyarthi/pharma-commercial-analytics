"""
Loads the generated CSVs into a local SQLite DB and runs analysis_queries.sql,
printing/saving each query's result. This simulates the SQL workflow a
Business Analyst at ProcDNA would run against a client's data warehouse.
"""
import sqlite3
import pandas as pd
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = Path(__file__).resolve().parent / "query_results"
OUT.mkdir(exist_ok=True)

con = sqlite3.connect(":memory:")

pd.read_csv(DATA / "hcps_with_segment.csv").to_sql("hcps_with_segment", con, index=False)
pd.read_csv(DATA / "reps.csv").to_sql("reps", con, index=False)
pd.read_csv(DATA / "calls.csv").to_sql("calls", con, index=False)
pd.read_csv(DATA / "sales.csv").to_sql("sales", con, index=False)
pd.read_csv(DATA / "rep_targets.csv").to_sql("rep_targets", con, index=False)

sql_text = (Path(__file__).parent / "analysis_queries.sql").read_text()
queries = [q.strip() for q in sql_text.split(";") if q.strip() and not q.strip().startswith("--")]

# Split on the '-- Q' comment markers to keep query labels
blocks = sql_text.split("-- Q")[1:]
for i, block in enumerate(blocks, start=1):
    label, _, query = block.partition("\n")
    query = query.strip().rstrip(";")
    df = pd.read_sql_query(query, con)
    fname = OUT / f"Q{i}_result.csv"
    df.to_csv(fname, index=False)
    print(f"\n=== Q{i}. {label.strip()} ===")
    print(df.to_string(index=False))

