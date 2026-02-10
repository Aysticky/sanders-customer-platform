# Core job runner (Entrypoint)

import importlib.util
import os
import sys
from pathlib import Path

from app.libs.exceptions import NoWorkFound
from app.libs.logging import get_logger

log = get_logger(__name__)

# Loads job module dynamically from file path
def import_module_from_path(file_path: str):
    p = Path(file_path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Job file not found: {p}")

    spec = importlib.util.spec_from_file_location(p.stem, str(p))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load job module: {p}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Calls the job's main() function
def run_job(job_path: str):
    log.info("Starting job: %s", job_path)

    module = import_module_from_path(job_path)
    if not hasattr(module, "main"):
        raise AttributeError(f"Job {job_path} must define main()")

    try:
        module.main()
        log.info("Job succeeded: %s", job_path)
        # Handles NoWorkFound exceptions gracefully
    except NoWorkFound as e:
        log.warning("No work found (treated as success): %s", e)
    except Exception:
        log.exception("Job failed: %s", job_path)
        raise


def cli():
    if len(sys.argv) != 2:
        print("Usage: scp-run <job_file_path>")
        sys.exit(2)

    job_path = sys.argv[1]
    # Step Functions / Batch can pass this; jobs can read it
    os.environ.setdefault("SCHEDULED_TIME", "")
    run_job(job_path)

# CLI command:
# export LOCAL_TLC_PARQUET="data/tlc_small.parquet"
# uv run scp-run jobs/daily_features_tlc.py