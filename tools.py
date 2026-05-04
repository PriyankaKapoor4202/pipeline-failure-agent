import re
from datetime import datetime

def parse_log(log_text: str) -> dict:
    """Extracts structured info from a raw log line."""
    result = {
        "raw": log_text,
        "timestamp": None,
        "error_type": None,
        "pipeline": None,
        "details": log_text
    }

    # Extract timestamp
    ts_match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', log_text)
    if ts_match:
        result["timestamp"] = ts_match.group()

    # Detect error type
    log_lower = log_text.lower()
    if any(w in log_lower for w in ["schema", "column", "field", "dtype"]):
        result["error_type"] = "schema_change"
    elif any(w in log_lower for w in ["timeout", "timed out", "connection refused"]):
        result["error_type"] = "timeout"
    elif any(w in log_lower for w in ["null", "none", "nan", "missing value"]):
        result["error_type"] = "null_values"
    elif any(w in log_lower for w in ["memory", "oom", "out of memory"]):
        result["error_type"] = "memory"
    elif any(w in log_lower for w in ["permission", "access denied", "unauthorized"]):
        result["error_type"] = "permissions"
    elif any(w in log_lower for w in ["duplicate", "unique constraint", "primary key"]):
        result["error_type"] = "duplicate_data"
    else:
        result["error_type"] = "unknown"

    # Extract pipeline name
    pipe_match = re.search(r'pipeline[:\s_-]+([a-zA-Z0-9_-]+)', log_text, re.IGNORECASE)
    if pipe_match:
        result["pipeline"] = pipe_match.group(1)

    return result


def check_upstream(error_type: str) -> dict:
    """Simulates checking upstream data sources for anomalies."""
    checks = {
        "schema_change": {
            "status": "anomaly_found",
            "finding": "Source table schema was modified 2 hours ago — column 'user_id' changed from INT to VARCHAR",
            "upstream_system": "PostgreSQL source DB"
        },
        "timeout": {
            "status": "anomaly_found",
            "finding": "Source API response time spiked to 45s avg in last hour (normal: 2s). Likely overloaded.",
            "upstream_system": "REST API source"
        },
        "null_values": {
            "status": "anomaly_found",
            "finding": "Upstream CRM export introduced 34% null rate in 'email' field since yesterday's batch",
            "upstream_system": "CRM export job"
        },
        "memory": {
            "status": "anomaly_found",
            "finding": "Input dataset size increased 8x compared to last run — likely a data explosion upstream",
            "upstream_system": "S3 data lake"
        },
        "permissions": {
            "status": "anomaly_found",
            "finding": "Service account credentials rotated 3 hours ago but pipeline config not updated",
            "upstream_system": "IAM / secrets manager"
        },
        "duplicate_data": {
            "status": "anomaly_found",
            "finding": "Source job ran twice due to scheduler misconfiguration — duplicate records ingested",
            "upstream_system": "Ingestion scheduler"
        },
        "unknown": {
            "status": "no_anomaly",
            "finding": "No upstream anomalies detected. Issue may be in transformation logic.",
            "upstream_system": "All systems"
        }
    }
    return checks.get(error_type, checks["unknown"])


def suggest_fix(error_type: str, upstream_finding: str) -> dict:
    """Returns a concrete fix with code snippet and confidence score."""
    fixes = {
        "schema_change": {
            "confidence": 92,
            "fix_summary": "Cast the column back to expected type in your ingestion query",
            "code": """-- Add this cast to your ingestion SQL
SELECT 
    CAST(user_id AS INT) as user_id,  -- source changed to VARCHAR, cast back
    *
FROM source_table;

# Or in PySpark:
df = df.withColumn("user_id", df["user_id"].cast("integer"))""",
            "prevention": "Add schema validation step at pipeline start using Great Expectations or dbt tests"
        },
        "timeout": {
            "confidence": 85,
            "fix_summary": "Add retry logic with exponential backoff and reduce batch size",
            "code": """import time

def fetch_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            return response
        except requests.Timeout:
            wait = 2 ** attempt  # 1s, 2s, 4s
            print(f"Timeout. Retrying in {wait}s...")
            time.sleep(wait)
    raise Exception("Max retries exceeded")""",
            "prevention": "Set timeout alerts when API response time exceeds 10s"
        },
        "null_values": {
            "confidence": 88,
            "fix_summary": "Add null filter or fill strategy before transformation",
            "code": """# PySpark — drop rows where critical fields are null
df = df.filter(df["email"].isNotNull())

# Or fill with default
df = df.fillna({"email": "unknown@placeholder.com"})

# dbt — add not_null test in schema.yml
columns:
  - name: email
    tests:
      - not_null""",
            "prevention": "Add data quality checks in dbt or Great Expectations on every ingestion"
        },
        "memory": {
            "confidence": 80,
            "fix_summary": "Increase executor memory and process in smaller partitions",
            "code": """# Spark config — increase memory
spark = SparkSession.builder \\
    .config("spark.executor.memory", "8g") \\
    .config("spark.driver.memory", "4g") \\
    .getOrCreate()

# Repartition large dataset
df = df.repartition(200)  # increase partitions""",
            "prevention": "Monitor input dataset size and alert if it grows >3x compared to last run"
        },
        "permissions": {
            "confidence": 95,
            "fix_summary": "Update pipeline credentials with the rotated service account key",
            "code": """# Update your .env or secrets manager:
DB_PASSWORD=<new_rotated_password>

# In AWS Secrets Manager:
aws secretsmanager update-secret \\
    --secret-id pipeline/db-credentials \\
    --secret-string '{"password":"new_value"}'""",
            "prevention": "Use secrets manager with auto-rotation and notify pipeline team on every rotation"
        },
        "duplicate_data": {
            "confidence": 90,
            "fix_summary": "Deduplicate using primary key before loading to target",
            "code": """# PySpark deduplication
df = df.dropDuplicates(["primary_key_column"])

# SQL deduplication
SELECT DISTINCT ON (primary_key) *
FROM staging_table
ORDER BY primary_key, ingested_at DESC;

# dbt — add unique test
columns:
  - name: id
    tests:
      - unique""",
            "prevention": "Add idempotency check in scheduler — prevent duplicate runs within same window"
        },
        "unknown": {
            "confidence": 45,
            "fix_summary": "Check transformation logic and add verbose logging for next run",
            "code": """import logging
logging.basicConfig(level=logging.DEBUG)

# Add checkpoints in your pipeline
print(f"Row count after step 1: {df.count()}")
print(f"Schema: {df.dtypes}")
print(f"Null counts: {df.isnull().sum()}")""",
            "prevention": "Add row count and schema logging at every pipeline stage"
        }
    }
    return fixes.get(error_type, fixes["unknown"])
