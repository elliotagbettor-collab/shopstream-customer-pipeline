import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path to import modules properly
sys.path.append(str(Path(__file__).resolve().parent.parent))

from deduplicate import levenshtein_ratio, merge_duplicate_group, deduplicate_dataframe

def test_levenshtein_ratio():
    assert levenshtein_ratio("Emma Davis", "Emma Davis") == 100.0
    assert levenshtein_ratio("Emma Davis", "Emma Davies") >= 90.0
    assert levenshtein_ratio("Emma Davis", "Frank Wilson") < 50.0
    assert levenshtein_ratio("", "") == 100.0
    assert levenshtein_ratio(None, "Emma Davis") == 0.0

def test_merge_duplicate_group():
    # Construct synthetic group with duplicate emails
    group_data = [
        {
            "customer_id": "C1003", 
            "first_name": "Charlie", 
            "last_name": "Brown", 
            "email": "charlie.b@gmail.com", 
            "phone": "555-019-2834", 
            "signup_date": pd.Timestamp("2025-03-01"), 
            "country": "USA", 
            "purchase_amount": 320.00
        },
        {
            "customer_id": "C1008", 
            "first_name": "Charlie", 
            "last_name": "Brown", 
            "email": "charlie.b@gmail.com", 
            "phone": "555-999-8888", 
            "signup_date": pd.Timestamp("2025-05-01"), 
            "country": "USA", 
            "purchase_amount": 80.00
        }
    ]
    group_df = pd.DataFrame(group_data)
    merged = merge_duplicate_group(group_df)
    
    # Assert LTV is summed (320 + 80 = 400)
    assert merged["purchase_amount"] == 400.00
    # Assert signup date is earliest (2025-03-01)
    assert merged["signup_date"] == pd.Timestamp("2025-03-01")
    # Assert latest phone is chosen (555-999-8888)
    assert merged["phone"] == "555-999-8888"
    # Assert customer ID is from first row
    assert merged["customer_id"] == "C1003"

def test_deduplicate_dataframe():
    # Construct a dataframe with duplicates
    data = [
        # Exact duplicate rows (should be dropped)
        {"customer_id": "C1001", "first_name": "Alice", "last_name": "Smith", "email": "alice.smith@example.com", "phone": "123-456-7890", "signup_date": pd.Timestamp("2025-01-15"), "country": "USA", "purchase_amount": 100.0},
        {"customer_id": "C1001", "first_name": "Alice", "last_name": "Smith", "email": "alice.smith@example.com", "phone": "123-456-7890", "signup_date": pd.Timestamp("2025-01-15"), "country": "USA", "purchase_amount": 100.0},
        
        # Matching customer_id, differing detail
        {"customer_id": "C1002", "first_name": "Bob", "last_name": "Johnson", "email": "bob.j@example.net", "phone": "987-654-3210", "signup_date": pd.Timestamp("2025-02-10"), "country": "Canada", "purchase_amount": 45.0},
        {"customer_id": "C1002", "first_name": "Bob", "last_name": "Johnson", "email": "bob.j@example.net", "phone": "987-654-3210", "signup_date": pd.Timestamp("2025-02-15"), "country": "Canada", "purchase_amount": 15.0},
        
        # Fuzzy duplicate: similar name, matching phone number
        {"customer_id": "C1005", "first_name": "Emma", "last_name": "Davis", "email": "emma.davis@yahoo.com", "phone": "202-555-0143", "signup_date": pd.Timestamp("2025-05-05"), "country": "Australia", "purchase_amount": 1000.0},
        {"customer_id": "C1010", "first_name": "Emma", "last_name": "Davies", "email": "emma.d@yahoo.com", "phone": "202-555-0143", "signup_date": pd.Timestamp("2025-05-06"), "country": "Australia", "purchase_amount": 200.0}
    ]
    df = pd.DataFrame(data)
    deduped = deduplicate_dataframe(df, use_fuzzy=True)
    
    # Final count should be exactly 3: Alice, Bob (merged), Emma (fuzzy merged)
    assert len(deduped) == 3
    
    # Alice should have purchase amount of 100 (exact duplicate dropped, not summed)
    alice_row = deduped[deduped["customer_id"] == "C1001"].iloc[0]
    assert alice_row["purchase_amount"] == 100.0
    
    # Bob should have summed purchase amount of 60.0 (45 + 15)
    bob_row = deduped[deduped["customer_id"] == "C1002"].iloc[0]
    assert bob_row["purchase_amount"] == 60.0
    assert bob_row["signup_date"] == pd.Timestamp("2025-02-10")
    
    # Emma should have fuzzy merged and summed purchase amount of 1200.0 (1000 + 200)
    emma_row = deduped[deduped["customer_id"] == "C1005"].iloc[0]
    assert emma_row["purchase_amount"] == 1200.0
    assert emma_row["signup_date"] == pd.Timestamp("2025-05-05")
