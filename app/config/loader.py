# Config loader (dev/stg/prod ready)
# Loads environment-specific YAML configs (dev/stg/prod)

import os
from dataclasses import dataclass
from pathlib import Path
import yaml


@dataclass(frozen=True) 
# Returns typed AppConfig dataclass with AWS resource names
# This class holds the configuration parameters for the application
class AppConfig:
    env: str
    aws_region: str
    s3_bucket: str
    s3_prefix_raw: str
    s3_prefix_features: str
    ddb_table_daily_features: str

# Reads SCP_ENV environment variable to load correct config file
def load_config() -> AppConfig:
    """
    Load application configuration from environment-specific YAML file.
    This function determines the current environment (dev/stg/prod) from the SCP_ENV
    environment variable and loads the corresponding YAML configuration file. The
    configuration includes AWS resource settings such as region, S3 buckets, prefixes,
    and DynamoDB table names.'
    """
    env = os.getenv("SCP_ENV", "dev").lower()
    cfg_path = Path(__file__).parent / f"{env}.yml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Missing config file: {cfg_path}")
    
    # Loads environment-specific YAML configs (dev/stg/prod)
    data = yaml.safe_load(cfg_path.read_text())
    return AppConfig(
        env=env,
        aws_region=data["aws_region"],
        s3_bucket=data["s3_bucket"],
        s3_prefix_raw=data["s3_prefix_raw"],
        s3_prefix_features=data["s3_prefix_features"],
        ddb_table_daily_features=data["ddb_table_daily_features"],
    )

# Used by all jobs to get S3 buckets, DynamoDB tables, etc.