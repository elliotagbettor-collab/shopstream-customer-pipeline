import os
from pathlib import Path

# Base workspace directory
BASE_DIR = Path(__file__).resolve().parent

# Core Paths
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
LOGS_DIR = BASE_DIR / "logs"

# Ensure essential folders exist
for folder in [DATA_RAW_DIR, DATA_PROCESSED_DIR, LOGS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)

# File names
DEFAULT_RAW_FILE = DATA_RAW_DIR / "customer_raw.csv"
OUTPUT_CLEANED_CSV = DATA_PROCESSED_DIR / "customer_cleaned.csv"
OUTPUT_CLEANED_PARQUET = DATA_PROCESSED_DIR / "customer_cleaned.parquet"
OUTPUT_CLEANED_JSON = DATA_PROCESSED_DIR / "customer_cleaned.json"
OUTPUT_EDA_REPORT = DATA_PROCESSED_DIR / "eda_report.html"
LOG_FILE = LOGS_DIR / "pipeline.log"

# Schema Configuration
REQUIRED_COLUMNS = [
    "customer_id",
    "first_name",
    "last_name",
    "email",
    "phone",
    "signup_date",
    "country",
    "purchase_amount"
]

COLUMN_TYPES = {
    "customer_id": "string",
    "first_name": "string",
    "last_name": "string",
    "email": "string",
    "phone": "string",
    "country": "string",
    "purchase_amount": "float64"
}

# Cleaning Rules
DEFAULT_COUNTRY = "Unknown"
DEFAULT_PURCHASE_AMOUNT = 0.0

# Validation Rules
# Standard email validation regex
EMAIL_REGEX = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

# Deduplication Configuration
DEDUPLICATE_KEYS = ["email", "phone"] # Unique keys for standard deduplication
FUZZY_MATCH_THRESHOLD = 90             # Out of 100 for name similarity matching

# Logging Setup
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "filename": str(LOG_FILE)
}
