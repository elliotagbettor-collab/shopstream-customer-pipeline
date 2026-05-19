import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path to import modules properly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from validate import is_valid_email, validate_dataframe

def test_is_valid_email():
    assert is_valid_email("alice.smith@example.com") is True
    assert is_valid_email("bob.j@example.net") is True
    assert is_valid_email("charlie@gmail.co.uk") is True
    
    assert is_valid_email("ian.taylor.invalid") is False
    assert is_valid_email("missing_at_sign.com") is False
    assert is_valid_email("spaces in@email.com") is False
    assert is_valid_email("") is False
    assert is_valid_email(None) is False

def test_validate_missing_columns():
    # Missing required column: purchase_amount
    df = pd.DataFrame({
        "customer_id": ["C1001"],
        "first_name": ["Alice"],
        "last_name": ["Smith"],
        "email": ["alice.smith@example.com"],
        "phone": ["123-456-7890"],
        "signup_date": ["2025-01-15"],
        "country": ["USA"]
    })
    with pytest.raises(ValueError) as exc_info:
        validate_dataframe(df)
    assert "missing required columns" in str(exc_info.value).lower()

def test_validate_dataframe_metrics():
    future_date = datetime.now() + timedelta(days=365)
    data = {
        "customer_id": ["C1001", None, "C1003", "C1004", "C1005"],
        "first_name": ["Alice", "Bob", "Charlie", "David", "Emma"],
        "last_name": ["Smith", "Johnson", "Brown", "Miller", "Davis"],
        "email": ["alice.smith@example.com", "bob.j@net", "charlie.b@gmail.com", "david.miller@example.org", "invalid-email"],
        "phone": ["123-456-7890", "987-654-3210", None, "444-123-4567", "202-555-0143"],
        "signup_date": [datetime.now(), datetime.now(), datetime.now(), datetime.now(), future_date],
        "country": ["USA", "Canada", "USA", "UK", "Australia"],
        "purchase_amount": [150.50, 45.00, -10.00, 75.25, 1200.00]
    }
    df = pd.DataFrame(data)
    
    # Cast signup_date to datetime to avoid warnings in testing
    df["signup_date"] = pd.to_datetime(df["signup_date"])
    
    validated_df, report = validate_dataframe(df)
    
    # The record with None customer_id (Bob) must have been removed (fatal)
    assert len(validated_df) == 4
    assert report["fatal_records_removed"] == 1
    assert report["missing_customer_ids"] == 1
    
    # Validation flags check
    assert report["missing_phones"] == 1  # Charlie has None phone
    assert report["invalid_emails"] == 1  # Emma has 'invalid-email'
    assert report["negative_purchase_amounts"] == 1  # Charlie has -10.00
    assert report["future_signup_dates"] == 1  # Emma has future date
    
    # Data health score check
    assert report["overall_health_score_pct"] < 100.0
