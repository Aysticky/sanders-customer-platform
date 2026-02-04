# Real data jobs (NYC TLC) using DuckDB + S3

import boto3
from app.config.loader import load_config

def s3_client():
    cfg = load_config()
    return boto3.client("s3", region_name=cfg.aws_region)

# uploads bytes to S3
def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream"):
    cfg = load_config()
    s3 = s3_client()
    s3.put_object(Bucket=cfg.s3_bucket, Key=key, Body=data, ContentType=content_type)

# uploads local file to S3
def put_file(key: str, local_path: str, content_type: str = "application/octet-stream"):
    cfg = load_config()
    s3 = s3_client()
    s3.upload_file(local_path, cfg.s3_bucket, key, ExtraArgs={"ContentType": content_type})

# List all object in S3 prefix.
def list_keys(prefix: str):
    cfg = load_config()
    s3 = s3_client()
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=cfg.s3_bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys
