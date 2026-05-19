import re
import logging
from datetime import datetime
import pandas as pd
import config

logger = logging.getLogger("pipeline.validate")

def is_valid_email(email: str) -> bool:
    """Verifies email structure using standard config regex pattern."""
    if not email or pd.isna(email) or not isinstance(email, str):
        return False
    return bool(re.match(config.EMAIL_REGEX, email))

def validate_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Validates structural integrity and checks for business logic anomalies.
    
    Checks applied:
    - Missing required columns
    - Missing customer_id
    - Missing email/phone (critical contacts)
    - Invalid email addresses (regex check)
    - Invalid/Negative purchase amounts
    - Future signup dates
    
    Returns:
        tuple[pd.DataFrame, dict]: 
            - Filtered/validated DataFrame (excluding fatal errors like missing customer_id)
            - Validation metrics report (dictionary)
    """
    logger.info("Initializing data quality validation checks.")
    
    validation_report = {
        "total_records": len(df),
        "missing_columns": [],
        "missing_customer_ids": 0,
        "missing_emails": 0,
        "missing_phones": 0,
        "invalid_emails": 0,
        "negative_purchase_amounts": 0,
        "future_signup_dates": 0,
        "fatal_records_removed": 0,
        "overall_health_score_pct": 100.0
    }
    
    # 1. Structural check: Verify required columns exist
    missing_cols = [col for col in config.REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        validation_report["missing_columns"] = missing_cols
        logger.error(f"Missing critical pipeline columns: {missing_cols}")
        raise ValueError(f"DataFrame is missing required columns: {missing_cols}")
        
    if df.empty:
        logger.warning("Empty dataframe provided to validate_dataframe.")
        return df, validation_report
        
    # Create working copy
    valid_df = df.copy()
    
    # 2. Check for missing customer_id (fatal)
    missing_id_mask = valid_df["customer_id"].isna() | (valid_df["customer_id"] == "") | (valid_df["customer_id"] == "NAN")
    missing_id_count = missing_id_mask.sum()
    validation_report["missing_customer_ids"] = int(missing_id_count)
    
    if missing_id_count > 0:
        logger.warning(f"Found {missing_id_count} records missing critical customer_id. These will be discarded.")
        # Filter out fatal rows
        valid_df = valid_df[~missing_id_mask]
        validation_report["fatal_records_removed"] += int(missing_id_count)
        
    # 3. Check for missing emails / phones (non-fatal, but logged)
    missing_email_count = valid_df["email"].isna().sum()
    validation_report["missing_emails"] = int(missing_email_count)
    
    missing_phone_count = valid_df["phone"].isna().sum()
    validation_report["missing_phones"] = int(missing_phone_count)
    
    # 4. Check for invalid email formats
    invalid_email_mask = valid_df["email"].notna() & ~valid_df["email"].apply(is_valid_email)
    invalid_email_count = invalid_email_mask.sum()
    validation_report["invalid_emails"] = int(invalid_email_count)
    if invalid_email_count > 0:
        logger.warning(f"Found {invalid_email_count} records with invalid email address structures.")
        
    # 5. Check for negative purchase amounts
    negative_purchase_mask = valid_df["purchase_amount"] < 0
    negative_purchase_count = negative_purchase_mask.sum()
    validation_report["negative_purchase_amounts"] = int(negative_purchase_count)
    if negative_purchase_count > 0:
        logger.warning(f"Found {negative_purchase_count} records with negative purchase amounts.")
        
    # 6. Check for future signup dates
    current_time = datetime.now()
    # If signup_date wasn't successfully parsed as datetime, handle it gracefully
    future_date_count = 0
    if pd.api.types.is_datetime64_any_dtype(valid_df["signup_date"]):
        future_date_mask = valid_df["signup_date"] > current_time
        future_date_count = future_date_mask.sum()
        validation_report["future_signup_dates"] = int(future_date_count)
        if future_date_count > 0:
            logger.warning(f"Found {future_date_count} records with registration dates in the future.")
            
    # Calculate Data Health Score (Percentage of clean values across these checks)
    total_checks = len(valid_df) * 4 # 4 quality checks per remaining row (valid email, phone, non-neg amount, non-future date)
    if total_checks > 0:
        failures = (invalid_email_count + 
                    (valid_df["email"].isna().sum()) +
                    (valid_df["phone"].isna().sum()) +
                    negative_purchase_count + 
                    future_date_count)
        health_pct = ((total_checks - failures) / total_checks) * 100.0
        validation_report["overall_health_score_pct"] = round(max(0.0, health_pct), 2)
        
    logger.info(f"Validation completed. Data health score: {validation_report['overall_health_score_pct']}%")
    return valid_df, validation_report
