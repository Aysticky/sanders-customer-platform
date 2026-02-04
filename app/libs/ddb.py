# Upserts (inserts or updates) daily feature records into a DynamoDB table.

import boto3
from app.config.loader import load_config

def ddb_resource():
    cfg = load_config()
    return boto3.resource("dynamodb", region_name=cfg.aws_region)

def upsert_daily_features(items: list[dict]):
    """
    This function loads the application configuration, retrieves the DynamoDB table
    for daily features, and writes each item from the provided list to the table.
    Note that this implementation uses simple put_item operations, which is suitable
    for small demo volumes but may not be optimal for high-throughput scenarios.
    """
    cfg = load_config()
    table = ddb_resource().Table(cfg.ddb_table_daily_features)
    # simple writes; good enough for small demo volumes
    for it in items:
        table.put_item(Item=it)
