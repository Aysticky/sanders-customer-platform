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

**Manual Batch Submission (Recommended for Testing):**
```bash
aws batch submit-job \
  --job-name daily-features-test \
  --job-queue sanders-batch-queue-prod \
  --job-definition sanders-job-8g-prod:1 \
  --container-overrides '{
    "command":["jobs/daily_features_tlc.py"],
    "environment":[
      {"name":"SCP_ENV","value":"prod"},
      {"name":"TLC_DATA_PATH","value":"s3://sanders-customer-platform-prod/raw/nyc_tlc/tlc_small.parquet"},
      {"name":"LOG_LEVEL","value":"INFO"}
    ]
  }' \
  --region eu-central-1
```

**Automated (EventBridge Scheduler):**
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
├── app/                        # Application code
│   ├── config/                # Environment configs (dev/prod)
│   ├── libs/                  # Shared libraries (S3, DynamoDB, logging)
│   └── main.py                # CLI entrypoint (scp-run)
├── jobs/                       # ETL jobs
│   ├── daily_features_tlc.py  # Feature extraction
│   └── ingest_tlc_sample.py   # Data ingestion
├── cdk/                        # Infrastructure as Code
│   ├── cdk_constructs/        # Reusable CDK components
│   ├── app.py                 # CDK app entrypoint
│   └── cdk-wrapper.py         # Python 3.13 compatibility fix
├── .github/workflows/          # CI/CD pipelines
│   ├── ci.yml                 # Linting, testing, security
│   ├── deploy-app.yml         # Docker + Batch deployment
│   └── deploy-infra.yml       # CDK infrastructure deployment
├── docs/                       # Documentation
│   └── ARCHITECTURE.md        # Detailed architecture guide
├── Dockerfile                  # Container definition
└── pyproject.toml             # Python project config
```

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
| **Prod** | Production workloads | Tag-based | Full (alarms) |

**Resource Naming:**
- Dev: `sanders-*-dev`
- Prod: `sanders-*-prod`

**Promotion Strategy:**
1. Develop on `feature/*` branch
2. Test in dev environment
3. Merge to `master`
4. Create release tag: `git tag v1.x.x`
5. Auto-deploy to prod (GitHub Actions)

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
- **Data Processed**: 200k records (4.2 MB parquet)
- **Job Duration**: ~30 seconds (8GB job)
- **Features Generated**: 3 metrics per customer (trip count, avg fare, avg distance)
- **Cost**: ~$0.01 per run (Fargate + S3 + DynamoDB)

**Scalability:**
- Auto-scales with Batch compute
- DynamoDB on-demand (no provisioned capacity)
- S3 unlimited storage
- Can handle millions of records with proper partitioning

## Known Issues

### 1. Step Functions Environment Variables
**Problem**: Step Functions doesn't pass dynamic env vars to Batch jobs  
**Workaround**: Use manual Batch submission or EventBridge scheduler  
**Solution**: Update CDK to embed env vars in job definitions

### 2. Python 3.13 CDK Compatibility
**Problem**: `aws-cdk-lib` doesn't fully support Python 3.13  
**Solution**: Use `cdk-wrapper.py` to inject sys.path  
**Recommendation**: Stick with Python 3.11/3.12 for CDK

### 3. Windows Git Bash Path Translation
**Problem**: AWS CLI converts paths like `/aws/batch/job`  
**Solution**: Use `MSYS_NO_PATHCONV=1` prefix

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
