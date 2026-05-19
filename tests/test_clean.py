import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add project root to path to import modules properly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from clean import clean_email, clean_name, clean_phone, clean_country, clean_dataframe

def test_clean_email():
    assert clean_email(" ALICE.SMITH@EXAMPLE.COM ") == "alice.smith@example.com"
    assert clean_email("") is None
    assert clean_email(np.nan) is None
    assert clean_email("bob.j@example.net") == "bob.j@example.net"

def test_clean_name():
    assert clean_name("  frank  ") == "Frank"
    assert clean_name("ALICE smith") == "Alice Smith"
    assert clean_name("  john   doe  ") == "John Doe"
    assert clean_name("") == "Unknown"
    assert clean_name(np.nan) == "Unknown"

def test_clean_phone():
    assert clean_phone("123-456-7890") == "123-456-7890"
    assert clean_phone("(987) 654-3210") == "987-654-3210"
    assert clean_phone("444.123.4567") == "444-123-4567"
    assert clean_phone("+1-202-555-0143") == "202-555-0143"
    assert clean_phone("2025550189") == "202-555-0189"
    assert clean_phone("12345") == "12345" # Unrecognized formats left as is
    assert clean_phone("") is None
    assert clean_phone(np.nan) is None

def test_clean_country():
    assert clean_country("usa") == "USA"
    assert clean_country("united states") == "USA"
    assert clean_country("u.s.a.") == "USA"
    assert clean_country("UK") == "UK"
    assert clean_country("united kingdom") == "UK"
    assert clean_country("germany") == "Germany"
    assert clean_country("") == "Unknown"
    assert clean_country(np.nan) == "Unknown"

def test_clean_dataframe():
    data = {
        "customer_id": [" c1001 "],
        "first_name": [" alice "],
        "last_name": [" smith "],
        "email": [" ALICE.SMITH@EXAMPLE.COM "],
        "phone": [" (123) 456-7890 "],
        "country": [" usa "],
        "purchase_amount": [" 150.50 "],
        "signup_date": [" 2025-01-15 "]
    }
    df = pd.DataFrame(data)
    cleaned_df = clean_dataframe(df)
    
    assert cleaned_df["customer_id"].iloc[0] == "C1001"
    assert cleaned_df["first_name"].iloc[0] == "Alice"
    assert cleaned_df["last_name"].iloc[0] == "Smith"
    assert cleaned_df["email"].iloc[0] == "alice.smith@example.com"
    assert cleaned_df["phone"].iloc[0] == "123-456-7890"
    assert cleaned_df["country"].iloc[0] == "USA"
    assert cleaned_df["purchase_amount"].iloc[0] == 150.50
    assert isinstance(cleaned_df["signup_date"].iloc[0], pd.Timestamp)
