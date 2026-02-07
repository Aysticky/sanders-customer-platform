# Reads your S3 partition, computes daily-style features, writes feature 
# parquet to S3, upserts to DynamoDB.

import os
import tempfile
import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime
from decimal import Decimal

from app.config.loader import load_config
from app.libs.logging import get_logger
from app.libs.ddb import upsert_daily_features
from app.libs.s3_io import put_file

log = get_logger(__name__)

def _scheduled_date() -> str:
    # Step Functions passes SCHEDULED_TIME like 2026-02-04T01:23:45Z
    st = os.getenv("SCHEDULED_TIME", "")
    if st:
        try:
            return datetime.fromisoformat(st.replace("Z", "+00:00")).date().isoformat()
        except Exception:
            pass
    # fallback
    return datetime.utcnow().date().isoformat()

def main():
    cfg = load_config()
    date = _scheduled_date()
    log.info("Running daily features for date=%s", date)

    # Read the ingested TLC parquet from your S3 bucket.
    # DuckDB can read s3:// if creds exist, but simplest is: download via AWS CLI in Batch image later.
    # For local dev, you can just run after downloading file locally.
    #
    # For the first version, we keep it simple: expect a local path mounted or downloaded by the job.
    local_input = os.getenv("LOCAL_TLC_PARQUET", "")
    if not local_input:
        raise RuntimeError("Set LOCAL_TLC_PARQUET to the TLC parquet path for now.")

    con = duckdb.connect(database=":memory:")
    # DuckDB doesn't support parameterized CREATE VIEW, use string formatting
    con.execute(f"CREATE VIEW trips AS SELECT * FROM read_parquet('{local_input}')")

    # Choose a stable “entity id” to feature-engineer.
    # TLC has VendorID; we’ll treat it as customer_id for demo.
    q = """
    SELECT
      CAST(VendorID AS VARCHAR) AS customer_id,
      COUNT(*) AS trip_count_1d,
      AVG(fare_amount) AS avg_fare_1d,
      AVG(trip_distance) AS avg_distance_1d
    FROM trips
    WHERE VendorID IS NOT NULL
    GROUP BY 1
    """
    features = con.execute(q).df()

    # Write features to S3
    with tempfile.TemporaryDirectory() as td:
        out_path = f"{td}/features.parquet"
        table = pa.Table.from_pandas(features)
        pq.write_table(table, out_path, compression="snappy")

        key = f"{cfg.s3_prefix_features}/date={date}/features.parquet"
        put_file(key, out_path)
        log.info("Wrote features to s3://%s/%s", cfg.s3_bucket, key)

    # Upsert to DynamoDB (small demo volume)
    items = []
    for row in features.to_dict(orient="records"):
        items.append({
            "customer_id": row["customer_id"],
            "date": date,
            "trip_count_1d": int(row["trip_count_1d"]),
            "avg_fare_1d": Decimal(str(row["avg_fare_1d"])) if row["avg_fare_1d"] is not None else Decimal("0.0"),
            "avg_distance_1d": Decimal(str(row["avg_distance_1d"])) if row["avg_distance_1d"] is not None else Decimal("0.0"),
        })
    upsert_daily_features(items)
    log.info("Upserted %d feature rows to DynamoDB table=%s", len(items), cfg.ddb_table_daily_features)
