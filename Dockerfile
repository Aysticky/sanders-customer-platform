FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv for fast installs
RUN pip install --no-cache-dir uv

# Copy source code and config first
COPY pyproject.toml /app/
COPY app /app/app
COPY jobs /app/jobs

# Install the package in editable mode with all dependencies
RUN uv pip install --system -e ".[dev]"

ENTRYPOINT ["scp-run"]

# Usage:
# docker build -t sanders-customer-platform:dev .
# docker run --rm \
#   -e SCP_ENV=dev \
#   -e LOCAL_TLC_PARQUET=/app/data/tlc_small.parquet \
#   -v ${PWD}/data:/app/data \
#   sanders-customer-platform:dev jobs/daily_features_tlc.py