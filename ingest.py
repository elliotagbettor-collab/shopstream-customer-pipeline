from config import CONFIG
import logging
import sys
import json
import requests
from pathlib import Path
import pandas as pd
import numpy as np


def parse_bool_like(value):
    if pd.isna(value):
        return pd.NA
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "t", "opted_out", "opt_out", "optout", "opt-out"}:
        return True
    if normalized in {"0", "false", "no", "n", "none", "nan", ""}:
        return False
    return pd.NA


def normalize_opt_out(series: pd.Series) -> pd.Series:
    return series.map(parse_bool_like).astype("boolean")

# ── Logging Setup ──────────────────────────────────────────────────────────────
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

CONFIG["log_dir"].mkdir(exist_ok=True)
log_path = CONFIG["log_dir"] / "pipeline.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger("shopstream_pipeline")

# ingest website csv
def ingest_website_csv(filepath: Path) -> pd.DataFrame:
    """
    Ingest the website registration CSV export.

    Args:
        filepath: Path to the CSV file.

    Returns:
        Cleaned DataFrame with source tag and standardized column names.
    """
    logger.info(f"Ingesting website CSV: {filepath}")

    df = pd.read_csv(
        filepath,
        encoding="iso-8859-1",                          # Handle accented characters
        dtype={"Phone": str},                            # Prevent numeric coercion
        parse_dates=["Registration Date"],
        na_values=["", "N/A", "null", "NULL", "none", "NaN"],
    )

    # Standardize column names to snake_case
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r"[^\w]", "_", regex=True)
        .str.replace(r"_+", "_", regex=True)
        .str.strip("_")
    )

    # Rename to standard schema
    df = df.rename(columns={
        "customeremail": "email",
        "first_name": "first_name",
        "last_name": "last_name",
        "registration_date": "registration_date",
        "optout": "opt_out",
    })

    # Remove test accounts
    test_mask = df["email"].str.contains(r"@test\.shopstream\.com$", na=False, case=False)
    removed = test_mask.sum()
    df = df[~test_mask].copy()
    logger.info(f"  Removed {removed} test accounts")

    df["source"] = "website"
    logger.info(f"  Ingested {len(df)} records from website CSV")
    return df


def ingest_crm_json(filepath: Path) -> pd.DataFrame:
    """
    Ingest customer data from the CRM JSON export.
    In production, this would call the paginated REST API.

    Args:
        filepath: Path to the JSON export file.

    Returns:
        Flattened DataFrame with source tag.
    """
    logger.info(f"Ingesting CRM JSON: {filepath}")

    raw = json.loads(filepath.read_text())
    df = pd.json_normalize(
        raw["customers"],
        sep="_",            # Flatten nested keys with underscore separator
    )

    # pd.json_normalize turns "profile.first_name" -> "profile_first_name"
    df = df.rename(columns={
        "profile_first_name": "first_name",
        "profile_last_name": "last_name",
        "registration_date": "registration_date",
    })

    df["registration_date"] = pd.to_datetime(df["registration_date"], format="%Y-%m-%d", errors="coerce")
    df["source"] = "crm"

    logger.info(f"  Ingested {len(df)} records from CRM JSON")
    return df

# ingest crm api
def ingest_crm_api(api_url: str, api_key: str) -> pd.DataFrame:
    """
    Ingest customer data from the CRM REST API with pagination.
    Use this in production instead of ingest_crm_json().

    Args:
        api_url: Base URL of the CRM API.
        api_key: Bearer token for authentication.

    Returns:
        Flattened DataFrame with source tag.
    """
    logger.info("Ingesting CRM API (paginated)...")
    all_records = []
    page = 1

    while True:
        response = requests.get(
            api_url,
            headers={"Authorization": f"Bearer {api_key}"},
            params={"page": page, "per_page": 500},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("customers"):
            break

        all_records.extend(data["customers"])
        logger.info(f"  Fetched page {page} ({len(data['customers'])} records)")
        page += 1

        if page > data.get("total_pages", 1):
            break

    df = pd.json_normalize(all_records, sep="_")
    df["source"] = "crm"
    logger.info(f"  Ingested {len(df)} records from CRM API")
    return df

# ingest erp fixed width
def ingest_erp_fixed_width(filepath: Path) -> pd.DataFrame:
    """
    Ingest the legacy ERP fixed-width text file.
    Column positions defined by ERP system specification v3.2.

    Field layout:
        [0:10]   customer_id
        [10:60]  full_name
        [60:120] email
        [120:140] phone
        [140:145] region_code
        [145:155] registration_date (YYYY-MM-DD)
        [155:160] status

    Args:
        filepath: Path to the fixed-width text file.

    Returns:
        Parsed DataFrame with source tag.
    """
    logger.info(f"Ingesting ERP fixed-width: {filepath}")

    colspecs = [
        (0, 10),     # customer_id
        (10, 60),    # full_name
        (60, 120),   # email
        (120, 140),  # phone
        (140, 145),  # region_code
        (145, 155),  # registration_date
        (155, 160),  # status
    ]
    col_names = ["customer_id", "full_name", "email", "phone",
                 "region_code", "registration_date", "status"]

    df = pd.read_fwf(
        filepath,
        colspecs=colspecs,
        names=col_names,
        dtype=str,                # Read everything as string first
        encoding="iso-8859-1",
    )

    # Strip whitespace from all string columns
    for col in df.select_dtypes(include=["object", "str"]).columns:
        df[col] = df[col].str.strip()

    # Split full_name into first/last
    name_split = df["full_name"].str.split(n=1, expand=True)
    df["first_name"] = name_split[0] if 0 in name_split.columns else np.nan
    df["last_name"] = name_split[1] if 1 in name_split.columns else np.nan

    df["registration_date"] = pd.to_datetime(df["registration_date"], format="%Y-%m-%d", errors="coerce")
    df["region"] = df["region_code"]   # Rename for schema alignment
    df["source"] = "erp"

    logger.info(f"  Ingested {len(df)} records from ERP")
    return df


STANDARD_SCHEMA = [
    "email", "first_name", "last_name", "phone", "region",
    "registration_date", "opt_out", "source"
]

def align_schema(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """
    Align a source DataFrame to the standard schema.
    Missing columns are added as NaN. Extra columns are dropped.
    """
    for col in STANDARD_SCHEMA:
        if col not in df.columns:
            df[col] = np.nan

    df["opt_out"] = normalize_opt_out(df["opt_out"])
    return df[STANDARD_SCHEMA].copy()


def ingest_all_sources() -> pd.DataFrame:
    """Ingest all 4 sources and combine into a single raw DataFrame."""
    logger.info("=" * 60)
    logger.info("STEP 1: Data Ingestion")

    frames = []

    website_df = ingest_website_csv(CONFIG["input_dir"] / "website_customers.csv")
    frames.append(align_schema(website_df, "website"))

    crm_df = ingest_crm_json(CONFIG["input_dir"] / "crm_export.json")
    frames.append(align_schema(crm_df, "crm"))

    erp_df = ingest_erp_fixed_width(CONFIG["input_dir"] / "erp_customers.txt")
    frames.append(align_schema(erp_df, "erp"))

    combined = pd.concat(frames, ignore_index=True)
    logger.info(f"Total records combined: {len(combined)}")
    for source in combined["source"].unique():
        count = (combined["source"] == source).sum()
        logger.info(f"  {source}: {count} records")

    return combined


# run ingestion
ingest_all_sources()