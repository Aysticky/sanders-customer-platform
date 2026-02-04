FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv for fast installs
RUN pip install --no-cache-dir uv

COPY pyproject.toml /app/
RUN uv pip install --system -e ".[dev]"

COPY app /app/app
COPY jobs /app/jobs

ENTRYPOINT ["scp-run"]

'''
docker build -t sanders-customer-platform:dev .
docker run --rm \
  -e SCP_ENV=dev \
  -e LOCAL_TLC_PARQUET=/app/data/tlc_small.parquet \
  -v %cd%/data:/app/data \
  sanders-customer-platform:dev jobs/daily_features_tlc.py
'''