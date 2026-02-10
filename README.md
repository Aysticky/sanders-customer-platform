# Sanders Customer Platform

**Production-grade AWS Batch ETL pipeline** for customer feature engineering using real public data (NYC TLC taxi dataset).

[![CI](https://github.com/Aysticky/sanders-customer-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Aysticky/sanders-customer-platform/actions/workflows/ci.yml)

## Overview

Enterprise-scale data pipeline that:
- **Processes 200k+ records** with AWS Batch + Fargate
- **Stores features** in S3 (analytics) + DynamoDB (real-time lookups)
- **Orchestrates workflows** with Step Functions
- **Monitors & alerts** via CloudWatch + SNS
- **Automates deployments** with CDK + GitHub Actions
- **Scales automatically** with containerized workloads

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  EventBridge │────>│  AWS Batch   │────>│   DuckDB     │
│  (Schedule)  │     │  (Fargate)   │     │  (In-Memory) │
└──────────────┘     └──────────────┘     └──────────────┘
                            │                      │
                            │                      ▼
                            │              ┌──────────────┐
                            │              │  S3 + Parquet│
                            │              │  (Data Lake) │
                            │              └──────────────┘
                            ▼
                     ┌──────────────┐     ┌──────────────┐
                     │  DynamoDB    │     │  CloudWatch  │
                     │  (Features)  │     │  (Monitoring)│
                     └──────────────┘     └──────────────┘
```

### Key Components

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **AWS Batch** | Compute engine | Fargate, 0.5-4 vCPU, 2-16GB RAM |
| **Step Functions** | Workflow orchestration | Parallel + sequential jobs |
| **S3** | Data lake (parquet) | Raw data + computed features |
| **DynamoDB** | Feature store | PAY_PER_REQUEST, real-time access |
| **ECR** | Container registry | Docker images (~800 MB) |
| **CloudWatch** | Monitoring | Dashboards + alarms |
| **EventBridge** | Job scheduling | Daily (2 AM UTC), Weekly (Sun 3 AM) |
| **SNS** | Alerting | Email notifications on failures |
| **CDK** | Infrastructure as Code | Python-based, multi-environment |

## Quick Start

### Prerequisites

- Python 3.11+ (Python 3.13 has CDK compatibility issues)
- AWS CLI configured with credentials
- Docker Desktop
- UV package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- CDK CLI: `npm install -g aws-cdk`

### Installation

```bash
# Clone repository
git clone https://github.com/Aysticky/sanders-customer-platform.git
cd sanders-customer-platform

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# Install CDK dependencies
cd cdk
uv pip install -r requirements-cdk.txt
cd ..
```

### Deploy Infrastructure

```bash
# Deploy dev environment
cd cdk
cdk bootstrap  # First time only
cdk deploy --context environment=dev

# Deploy production environment
cdk deploy --context environment=prod
```

### Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region eu-central-1 | \
  docker login --username AWS --password-stdin \
  120569615884.dkr.ecr.eu-central-1.amazonaws.com

# Build and tag
docker build -t sanders-customer-platform:prod .
docker tag sanders-customer-platform:prod \
  120569615884.dkr.ecr.eu-central-1.amazonaws.com/sanders-customer-platform-prod:latest

# Push to ECR
docker push 120569615884.dkr.ecr.eu-central-1.amazonaws.com/sanders-customer-platform-prod:latest
```

### Run Jobs

**Option 1: Manual Batch Submission (Recommended):**

This is the most flexible approach for passing environment variables at runtime.

```bash
# Single job submission
aws batch submit-job \
  --job-name daily-features-test \
  --job-queue sanders-batch-queue-prod \
  --job-definition sanders-job-8g-prod:1 \
  --container-overrides '{
    "command":["jobs/daily_features_tlc.py"],
    "environment":[
      {"name":"SCP_ENV","value":"prod"},
      {"name":"TLC_DATA_PATH","value":"s3://sanders-customer-platform-prod/raw/nyc_tlc/yellow_tripdata_2024-01.parquet"}
    ]
  }' \
  --region eu-central-1

# Check job status
aws batch describe-jobs --jobs <job-id> --region eu-central-1 \
  --query "jobs[0].[jobName,status,container.exitCode]"

# View logs
aws logs tail /aws/batch/job --follow --region eu-central-1
```

**Option 2: Parallel Job Testing:**

Test different data volumes concurrently:

```bash
# Upload sample data to S3
aws s3 cp data/tlc_raw.parquet \
  s3://sanders-customer-platform-prod/raw/nyc_tlc/yellow_tripdata_2024-01.parquet

# Submit 3 parallel jobs (500, 1000, 2000 rows)
aws batch submit-job --job-name small-500 \
  --job-queue sanders-batch-queue-prod \
  --job-definition sanders-job-2g-prod:1 \
  --container-overrides '{
    "command":["jobs/daily_features_tlc_small.py"],
    "environment":[
      {"name":"SCP_ENV","value":"prod"},
      {"name":"TLC_DATA_PATH","value":"s3://sanders-customer-platform-prod/raw/nyc_tlc/yellow_tripdata_2024-01.parquet"}
    ]
  }' --region eu-central-1

aws batch submit-job --job-name medium-1000 \
  --job-queue sanders-batch-queue-prod \
  --job-definition sanders-job-2g-prod:1 \
  --container-overrides '{
    "command":["jobs/daily_features_tlc_medium.py"],
    "environment":[
      {"name":"SCP_ENV","value":"prod"},
      {"name":"TLC_DATA_PATH","value":"s3://sanders-customer-platform-prod/raw/nyc_tlc/yellow_tripdata_2024-01.parquet"}
    ]
  }' --region eu-central-1

aws batch submit-job --job-name large-2000 \
  --job-queue sanders-batch-queue-prod \
  --job-definition sanders-job-2g-prod:1 \
  --container-overrides '{
    "command":["jobs/daily_features_tlc_large.py"],
    "environment":[
      {"name":"SCP_ENV","value":"prod"},
      {"name":"TLC_DATA_PATH","value":"s3://sanders-customer-platform-prod/raw/nyc_tlc/yellow_tripdata_2024-01.parquet"}
    ]
  }' --region eu-central-1

# Verify outputs in S3
aws s3 ls s3://sanders-customer-platform-prod/features/daily/daily/date=$(date +%Y-%m-%d)/ \
  --region eu-central-1

# Check DynamoDB records
aws dynamodb scan --table-name sanders_daily_customer_features_prod \
  --filter-expression "attribute_exists(dataset_size)" \
  --region eu-central-1
```

**Option 3: Automated Scheduling (EventBridge):**
- Daily features: Runs automatically at 2 AM UTC (prod only)
- Weekly training: Disabled by default (enable when ready)

## Monitoring

### CloudWatch Dashboard
View real-time metrics:
```
https://console.aws.amazon.com/cloudwatch/home?region=eu-central-1#dashboards:name=sanders-platform-prod
```

**Metrics:**
- Batch job success/failure rates
- Job duration
- DynamoDB read/write capacity
- Step Functions execution status

### Alarms
Automatic SNS alerts for:
- Batch job failures
- Step Functions execution failures
- High DynamoDB write capacity (cost control)

**Configure Email Alerts:**
Edit `cdk/sanders_customer_platform_stack.py`:
```python
monitoring = MonitoringDashboard(
    ...
    alarm_email="your-email@example.com"
)
```

## Development

### Project Structure

```
sanders-customer-platform/
├── app/                               # Application code
│   ├── config/                       # Environment configs (dev/prod)
│   │   ├── dev.yml                   # Dev environment settings
│   │   ├── prod.yml                  # Prod environment settings
│   │   └── loader.py                 # Config loader
│   ├── libs/                         # Shared libraries
│   │   ├── s3_io.py                  # S3 operations
│   │   ├── ddb.py                    # DynamoDB operations
│   │   ├── logging.py                # Structured logging
│   │   └── exceptions.py             # Custom exceptions
│   └── main.py                       # CLI entrypoint (scp-run)
├── jobs/                              # ETL jobs
│   ├── daily_features_tlc.py         # Main feature extraction (200k rows)
│   ├── daily_features_tlc_small.py   # Small variant (500 rows)
│   ├── daily_features_tlc_medium.py  # Medium variant (1000 rows)
│   ├── daily_features_tlc_large.py   # Large variant (2000 rows)
│   └── ingest_tlc_sample.py          # Data ingestion
├── cdk/                               # Infrastructure as Code
│   ├── cdk_constructs/               # Reusable CDK components
│   │   ├── batch_environment.py      # Batch compute + queue
│   │   ├── batch_iam_roles.py        # IAM roles for Batch
│   │   ├── dynamodb_table.py         # DynamoDB table
│   │   ├── ecr_repository.py         # Container registry
│   │   ├── monitoring.py             # CloudWatch dashboards + alarms
│   │   ├── s3_bucket.py              # S3 data lake
│   │   ├── scheduler.py              # EventBridge job scheduler
│   │   ├── stepfunctions_statemachine.py  # Step Functions workflow
│   │   └── vpc_network.py            # VPC + security groups
│   ├── app.py                        # CDK app entrypoint
│   ├── sanders_customer_platform_stack.py  # Main stack definition
│   └── cdk-wrapper.py                # Python 3.13 compatibility fix
├── .github/workflows/                 # CI/CD pipelines
│   └── ci.yml                        # Linting, testing, security
├── tests/                             # Unit tests
│   └── test_imports.py               # Import validation
├── docs/                              # Documentation
│   └── ARCHITECTURE.md               # Detailed architecture guide
├── data/                              # Local sample data
│   ├── tlc_raw.parquet               # NYC TLC sample (200k rows)
│   └── tlc_small.parquet             # Small sample
├── Dockerfile                         # Container definition
├── pyproject.toml                     # Python project config
├── uv.lock                            # Dependency lock file
└── README.md                          # This file
```

### Available Jobs

| Job File | Description | Data Volume | Output |
|----------|-------------|-------------|--------|
| `daily_features_tlc.py` | Main feature extraction | 200k rows | `features.parquet` |
| `daily_features_tlc_small.py` | Small batch processing | 500 rows | `features_small.parquet` |
| `daily_features_tlc_medium.py` | Medium batch processing | 1000 rows | `features_medium.parquet` |
| `daily_features_tlc_large.py` | Large batch processing | 2000 rows | `features_large.parquet` |
| `ingest_tlc_sample.py` | Data ingestion from NYC TLC | Configurable | Raw parquet |

All jobs output to:
- **S3**: `s3://<bucket>/features/daily/date=YYYY-MM-DD/<file>.parquet`
- **DynamoDB**: `sanders_daily_customer_features_<env>` table

### Adding New Jobs

1. **Create job file** in `jobs/`:
```python
# jobs/my_new_job.py
import logging
from app.config.loader import load_config
from app.libs.s3_io import s3_client

logger = logging.getLogger(__name__)

def main():
    config = load_config()
    logger.info(f"Running my new job for {config.s3_bucket}")
    # Your job logic here
```

2. **Test locally with Docker**:
```bash
docker run -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY \
  -e SCP_ENV=dev \
  sanders-customer-platform:latest \
  jobs/my_new_job.py
```

3. **Submit to Batch**:
```bash
aws batch submit-job --job-name my-new-job \
  --job-queue sanders-batch-queue-dev \
  --job-definition sanders-job-8g-dev:1 \
  --container-overrides '{"command":["jobs/my_new_job.py"]}'
```

### Running Tests

```bash
# Linting
ruff format . && ruff check .

# Tests
pytest tests/

# Security scan
pip-audit
```

## Environments

| Environment | Purpose | Auto-Deploy | Monitoring |
|-------------|---------|-------------|------------|
| **Dev** | Development & testing | Manual | Basic |
| **Prod** | Production workloads | Manual | Full (alarms + dashboard) |

**Resource Naming:**
- Dev: `sanders-*-dev`
- Prod: `sanders-*-prod`

**Deployment Workflow:**
1. Develop on `feature/*` branch
2. Test in dev environment:
   - Build Docker image: `docker build -t sanders-customer-platform:dev .`
   - Push to dev ECR
   - Submit test jobs to dev Batch queue
3. Verify dev results in S3 and DynamoDB
4. Merge to `master` branch
5. Deploy to prod:
   - Update CDK if needed: `cd cdk && cdk deploy --context environment=prod`
   - Build and push prod Docker image
   - Test with manual Batch submission
6. Create release tag: `git tag v1.x.x && git push origin v1.x.x`
7. Monitor CloudWatch dashboard and alarms

**Testing Strategy:**
- Unit tests run on every push (GitHub Actions)
- Manual testing in dev before prod deployment
- Parallel job testing validates concurrent workloads
- DynamoDB and S3 outputs verified after each deployment

## Security

### Current Setup
- **IAM User**: `sanders-platform-dev` (AdministratorAccess)
- **Credentials**: Single user for both environments
- **Networking**: VPC with public/private subnets

### Production Best Practices (TODO)
- [ ] Separate AWS accounts for dev/prod (AWS Organizations)
- [ ] Least privilege IAM policies
- [ ] AWS Secrets Manager for credentials
- [ ] VPC endpoints for S3/DynamoDB (private connectivity)
- [ ] Enable CloudTrail audit logging
- [ ] S3 bucket versioning and encryption
- [ ] DynamoDB point-in-time recovery

## Performance

**Current Capacity:**
- **Data Processed**: 200k records (NYC TLC taxi data, ~4.2 MB parquet)
- **Job Duration**: 15-30 seconds (2GB job), 10-20 seconds (8GB job)
- **Features Generated**: 3 metrics per customer (trip_count_1d, avg_fare_1d, avg_distance_1d)
- **Customers**: 2 unique VendorIDs in sample data
- **Cost**: ~$0.01 per run (Fargate + S3 + DynamoDB writes)

**Job Variants Tested:**
- Small (500 rows): 2 customers, ~6 seconds
- Medium (1000 rows): 2 customers, ~8 seconds  
- Large (2000 rows): 2 customers, ~10 seconds
- Full (200k rows): 2 customers, ~15 seconds

**Scalability:**
- Batch compute auto-scales with Fargate (no servers to manage)
- DynamoDB on-demand (no provisioned capacity, auto-scales to millions of writes)
- S3 unlimited storage with partitioning by date
- Can handle millions of records with proper data partitioning
- Parallel job execution tested and validated in dev and prod

**Production Validation:**
- Both dev and prod environments deployed successfully
- Parallel jobs tested: 3 concurrent jobs processing different data volumes
- All jobs completed with exit code 0
- S3 outputs verified: features_small/medium/large.parquet
- DynamoDB records written with dataset_size tracking

## Known Issues

### 1. Step Functions Environment Variables
**Problem**: Step Functions doesn't pass dynamic env vars to Batch jobs  
**Workaround**: Use manual Batch submission or EventBridge scheduler  
**Solution**: Update CDK to embed env vars in job definitions

### 2. Python 3.13 CDK Compatibility
**Problem**: `aws-cdk-lib` doesn't fully support Python 3.13  
**Error**: `ModuleNotFoundError: No module named 'constructs._jsii'`  
**Solution**: Use `cdk-wrapper.py` to inject sys.path before importing  
**Recommendation**: Use Python 3.11 or 3.12 for CDK operations

### 3. Windows Git Bash Path Translation
**Problem**: AWS CLI converts Unix paths like `/aws/batch/job` to Windows paths  
**Solution**: Use `MSYS_NO_PATHCONV=1` prefix or `//` for Unix paths  
**Example**: `MSYS_NO_PATHCONV=1 aws logs get-log-events --log-group-name /aws/batch/job`

### 4. NYC TLC Public Bucket Access
**Problem**: NYC TLC S3 bucket (s3://nyc-tlc) requires special access or has changed  
**Solution**: Upload sample data to your own S3 bucket:
```bash
aws s3 cp data/tlc_raw.parquet \
  s3://sanders-customer-platform-<env>/raw/nyc_tlc/yellow_tripdata_2024-01.parquet
```
**Note**: Jobs are configured to use your S3 bucket with proper IAM credentials

### 5. UV Package Manager in CI
**Problem**: UV requires virtual environment or `--system` flag  
**Solution**: Use `uv pip install --system -e ".[dev]"` in GitHub Actions  
**Reference**: See `.github/workflows/ci.yml` for working configuration

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md) - Detailed system design
- [API Reference](docs/API.md) - Code documentation (TODO)
- [Runbook](docs/RUNBOOK.md) - Operations guide (TODO)

## Contributing

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and commit: `git commit -m "Add my feature"`
3. Push and create PR: `git push origin feature/my-feature`
4. Wait for CI checks to pass
5. Request review

## License

MIT License - see [LICENSE](LICENSE) file

## Support

- **Issues**: [GitHub Issues](https://github.com/Aysticky/sanders-customer-platform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Aysticky/sanders-customer-platform/discussions)

---

**Built with AWS CDK, Python, and DuckDB**
