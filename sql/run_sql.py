"""Execute every named query in queries.sql against the cleaned parquet using DuckDB."""
import re
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
con = duckdb.connect()
con.execute(f"CREATE VIEW prices AS SELECT * FROM read_parquet('{(ROOT / 'data/processed/wfp_prices_clean.parquet').as_posix()}')")
text = (ROOT / "sql/queries.sql").read_text()
out_dir = ROOT / "outputs" / "sql"
out_dir.mkdir(parents=True, exist_ok=True)
for block in re.split(r"(?m)^-- name: ", text)[1:]:
    name, _, sql = block.partition("\n")
    df = con.execute(sql).df()
    df.to_csv(out_dir / f"{name.strip()}.csv", index=False)
    print(f"\n=== {name.strip()} ===\n{df.head(10).to_string(index=False)}")
