import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add hardcoded workspace path to sys.path
sys.path.append(r"c:\Users\ElliotAdinorteyAgbet\Documents\github_repos\shopstream-customer-pipeline")

import config
from deduplicate import levenshtein_ratio, merge_duplicate_group

def trace_deduplicate(df, use_fuzzy=True):
    initial_rows = len(df)
    print(f"Initial: {initial_rows} rows")
    
    # Step 1: Remove exact matching rows
    dedup_df = df.drop_duplicates()
    print(f"After exact drop: {len(dedup_df)} rows")
    
    # Standardize empty/null strings in email & phone to facilitate groupings
    dedup_df = dedup_df.copy()
    for col in ["email", "phone", "customer_id"]:
        if col in dedup_df.columns:
            dedup_df[col] = dedup_df[col].replace(r"^\s*$", np.nan, regex=True)
            
    # Step 2: Merge on customer_id
    if "customer_id" in dedup_df.columns:
        has_id = dedup_df[dedup_df["customer_id"].notna()]
        no_id = dedup_df[dedup_df["customer_id"].isna()]
        
        merged_ids = has_id.groupby("customer_id", as_index=False).apply(merge_duplicate_group)
        print("\nMerged IDs:")
        print(merged_ids)
        
        dedup_df = pd.concat([merged_ids, no_id], ignore_index=True)
        print(f"After customer_id merge: {len(dedup_df)} rows")
        
    # Step 3: Merge on Email (if not null)
    if "email" in dedup_df.columns:
        has_email = dedup_df[dedup_df["email"].notna()]
        no_email = dedup_df[dedup_df["email"].isna()]
        
        merged_emails = has_email.groupby("email", as_index=False).apply(merge_duplicate_group)
        print("\nMerged Emails:")
        print(merged_emails)
        print("No Email:")
        print(no_email)
        
        dedup_df = pd.concat([merged_emails, no_email], ignore_index=True)
        print(f"After email merge: {len(dedup_df)} rows")
        
    # Step 4: Merge on Phone (if not null)
    if "phone" in dedup_df.columns:
        has_phone = dedup_df[dedup_df["phone"].notna()]
        no_phone = dedup_df[dedup_df["phone"].isna()]
        
        merged_phones = has_phone.groupby("phone", as_index=False).apply(merge_duplicate_group)
        print("\nMerged Phones:")
        print(merged_phones)
        print("No Phone:")
        print(no_phone)
        
        dedup_df = pd.concat([merged_phones, no_phone], ignore_index=True)
        
        dedup_df = dedup_df.drop_duplicates(subset=["customer_id"])
        print(f"After phone merge: {len(dedup_df)} rows")
        
    return dedup_df

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
trace_deduplicate(df)
