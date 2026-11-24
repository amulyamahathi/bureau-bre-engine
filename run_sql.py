"""Load the BRE output into SQLite and run sql/analysis.sql query by query."""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
df = pd.read_csv(ROOT / "outputs" / "bre_output_v1.csv")

con = sqlite3.connect(":memory:")
df.to_sql("bre_output", con, index=False)

sql = (ROOT / "sql" / "analysis.sql").read_text()
queries = [q.strip() for q in sql.split(";") if "SELECT" in q.upper()]
for i, q in enumerate(queries, 1):
    title = next((l for l in q.splitlines() if re.match(r"-- Q\d", l)), f"-- Q{i}")
    print(f"\n{title}")
    print(pd.read_sql_query(q, con).to_string(index=False))
