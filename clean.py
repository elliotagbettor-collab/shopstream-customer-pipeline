import re
import logging
import pandas as pd
import numpy as np
import config

logger = logging.getLogger("pipeline.clean")

def clean_email(email) -> str:
    """Normalizes a single email string by lowercasing and trimming whitespaces."""
    if pd.isna(email) or not isinstance(email, str):
        return None
    cleaned = email.strip().lower()
    return cleaned if cleaned != "" else None

def clean_name(name) -> str:
    """Cleans a single name string: trims whitespace and capitalizes properly."""
    if pd.isna(name) or not isinstance(name, str):
        return "Unknown"
    cleaned = name.strip()
    # Normalize multiple whitespaces inside names
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.title() if cleaned != "" else "Unknown"

def clean_phone(phone) -> str:
    """
    Standardizes a phone number.
    Extracts all digits. If it starts with country code 1 and is 11 digits, we strip 1.
    If it results in 10 digits, formats it as 'XXX-XXX-XXXX'.
    Otherwise, returns digits-only string or None if empty.
    """
    if pd.isna(phone) or not isinstance(phone, str):
        return None
    
    # Strip all non-numeric characters
    digits = re.sub(r"\D", "", phone)
    
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
        
    if len(digits) == 10:
        return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
        
    return digits if digits != "" else None

def clean_country(country) -> str:
    """Normalizes country abbreviations or casings."""
    if pd.isna(country) or not isinstance(country, str):
        return config.DEFAULT_COUNTRY
    cleaned = country.strip()
    if cleaned.lower() in ["usa", "united states", "u.s.a.", "us"]:
        return "USA"
    if cleaned.lower() in ["uk", "united kingdom", "u.k."]:
        return "UK"
    return cleaned.title() if cleaned != "" else config.DEFAULT_COUNTRY

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Executes the comprehensive cleaning rules across the DataFrame.
    Copies the original data, parses types, cleans individual elements, and fills defaults.
    """
    logger.info("Starting customer data cleaning process.")
    cleaned_df = df.copy()
    
    # Check if there are columns in the df, handle gracefully
    if cleaned_df.empty:
        logger.warning("Empty dataframe provided to clean_dataframe.")
        return cleaned_df
        
    # Clean text-based columns
    if "first_name" in cleaned_df.columns:
        cleaned_df["first_name"] = cleaned_df["first_name"].apply(clean_name)
    if "last_name" in cleaned_df.columns:
        cleaned_df["last_name"] = cleaned_df["last_name"].apply(clean_name)
    if "email" in cleaned_df.columns:
        cleaned_df["email"] = cleaned_df["email"].apply(clean_email)
    if "phone" in cleaned_df.columns:
        cleaned_df["phone"] = cleaned_df["phone"].apply(clean_phone)
    if "country" in cleaned_df.columns:
        cleaned_df["country"] = cleaned_df["country"].apply(clean_country)
        
    # Clean numeric fields
    if "purchase_amount" in cleaned_df.columns:
        cleaned_df["purchase_amount"] = pd.to_numeric(cleaned_df["purchase_amount"], errors="coerce")
        # Fill missing purchase amount with configuration default
        cleaned_df["purchase_amount"] = cleaned_df["purchase_amount"].fillna(config.DEFAULT_PURCHASE_AMOUNT)
        
    # Parse dates
    if "signup_date" in cleaned_df.columns:
        cleaned_df["signup_date"] = pd.to_datetime(cleaned_df["signup_date"], errors="coerce")
        
    # Standardize ID column
    if "customer_id" in cleaned_df.columns:
        # Trim whitespace and capitalize letters
        cleaned_df["customer_id"] = cleaned_df["customer_id"].astype(str).str.strip().str.upper()
        
    logger.info("Cleaning process completed successfully.")
    return cleaned_df
