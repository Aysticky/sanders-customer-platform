# This job downloads a small TLC sample file (real data) and writes it into 
# your S3 as a partition.
# To keep it simple and cheap, we’ll ingest one month file and store it once.

import os
import tempfile

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.config.loader import load_config
from app.libs.logging import get_logger
from app.libs.s3_io import put_file

log = get_logger(__name__)

# NOTE:
# For the repo record, we keep the URL as a config later.
# You can swap the URL to any public TLC parquet/csv mirror you prefer.
DEFAULT_SOURCE_URL = (
    "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet"
)

def main():
    """
    Download a sample of TLC (NYC Taxi & Limousine Commission) parquet data 
    from a source URL, reduce it to 200,000 rows, and upload it to S3 in the 
    raw data prefix. The function creates temporary files for intermediate 
    storage and cleans them up automatically.
    """
    cfg = load_config()
    source_url = os.getenv("TLC_SOURCE_URL", DEFAULT_SOURCE_URL)
    log.info("Ingesting TLC parquet from: %s", source_url)

    with tempfile.TemporaryDirectory() as td:
        local_out = f"{td}/tlc_small.parquet"

        # read a small slice to keep everything lightweight
        df = pd.read_parquet(source_url)
        df = df.head(200_000)  # keep it small for demo + cost control

        table = pa.Table.from_pandas(df)
        pq.write_table(table, local_out, compression="snappy")

        key = f"{cfg.s3_prefix_raw}/dataset=yellow/year=2023/month=01/tlc_small.parquet"
        put_file(key, local_out, content_type="application/octet-stream")

    log.info("Ingest complete to s3://%s/%s", cfg.s3_bucket, key)
