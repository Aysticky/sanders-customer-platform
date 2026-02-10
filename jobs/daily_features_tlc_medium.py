"""
Daily Features Job - Medium Dataset (1000 rows)
Computes customer features from NYC TLC taxi data - MEDIUM VARIANT
"""
import logging
import os
from datetime import datetime
from decimal import Decimal

import duckdb

from app.config.loader import load_config
from app.libs.ddb import upsert_daily_features
from app.libs.s3_io import put_bytes

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """
    Main job execution:
    1. Read TLC data from S3 (1000 rows only)
    2. Compute daily features per customer (VendorID)
    3. Write features to S3 (parquet) and DynamoDB
    """
    config = load_config()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    logger.info(f"Running MEDIUM daily features (1000 rows) for date={today}")
    
    # Get S3 path from environment variable
    data_path = os.getenv("TLC_DATA_PATH")
    if not data_path:
        data_path = f"s3://{config.s3_bucket}/{config.s3_prefix_raw}/nyc_tlc/tlc_small.parquet"
    
    logger.info(f"Reading TLC data from: {data_path}")
    
    # Use DuckDB for in-memory analytics
    con = duckdb.connect(":memory:")
    
    # Load S3 credentials from AWS environment
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"SET s3_region='{config.aws_region}';")  # Our bucket region
    con.execute("SET s3_use_ssl=true;")
    con.execute("CALL load_aws_credentials();")
    
    # Create view from S3 parquet (LIMIT 1000 rows)
    con.execute(f"CREATE VIEW trips AS SELECT * FROM read_parquet('{data_path}') LIMIT 1000")
    
    # Compute daily features by customer (VendorID as customer_id)
    query = """
    SELECT
        CAST(VendorID AS VARCHAR) as customer_id,
        COUNT(*) as trip_count_1d,
        AVG(total_amount) as avg_fare_1d,
        AVG(trip_distance) as avg_distance_1d
    FROM trips
    GROUP BY VendorID
    """
    
    df = con.execute(query).df()
    logger.info(f"Computed features for {len(df)} customers from 1000 rows")
    
    # Add date column
    df['date'] = today
    
    # Write to S3 (parquet)
    s3_key = f"{config.s3_prefix_features}/daily/date={today}/features_medium.parquet"
    parquet_bytes = df.to_parquet()
    put_bytes(
        key=s3_key,
        data=parquet_bytes,
        content_type="application/octet-stream"
    )
    logger.info(f"Wrote features to s3://{config.s3_bucket}/{s3_key}")
    
    # Convert float to Decimal for DynamoDB
    items = []
    for _, row in df.iterrows():
        items.append({
            'customer_id': row['customer_id'],
            'date': row['date'],
            'trip_count_1d': Decimal(str(row['trip_count_1d'])),
            'avg_fare_1d': Decimal(str(row['avg_fare_1d'])),
            'avg_distance_1d': Decimal(str(row['avg_distance_1d'])),
            'dataset_size': 'medium_1000'
        })
    
    # Write to DynamoDB
    upsert_daily_features(items=items)
    logger.info(f"Upserted {len(items)} feature records to DynamoDB (MEDIUM - 1000 rows)")


if __name__ == "__main__":
    main()
