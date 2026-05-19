import os
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import config

logger = logging.getLogger("pipeline.ingest")

def load_data(file_path: str = None) -> pd.DataFrame:
    """
    Loads raw customer data from a specified file path.
    If the file does not exist, triggers automatic mock data generation.
    
    Args:
        file_path (str): Path to raw file. Defaults to config.DEFAULT_RAW_FILE.
        
    Returns:
        pd.DataFrame: Raw customer DataFrame.
    """
    if file_path is None:
        file_path = config.DEFAULT_RAW_FILE
        
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.info(f"File not found at {file_path}. Generating a realistic mock dataset to start with.")
        generate_mock_data(file_path)
        
    logger.info(f"Loading raw customer data from: {file_path}")
    ext = file_path.suffix.lower()
    
    try:
        if ext == ".csv":
            df = pd.read_csv(file_path, dtype=object) # Load as object to preserve formatting noise
        elif ext in [".xls", ".xlsx"]:
            df = pd.read_excel(file_path, dtype=object)
        elif ext == ".json":
            df = pd.read_json(file_path, dtype=object)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
            
        logger.info(f"Successfully loaded raw dataset with {len(df)} records and {len(df.columns)} columns.")
        return df
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {e}")
        raise

def generate_mock_data(output_path: Path):
    """
    Generates a realistic mock customer dataset with noise:
    - Uppercase/lowercase letters in emails, whitespaces
    - Null values in various columns
    - Exact duplicate records
    - Duplicate keys (same email/phone) with differing information (for resolution)
    - Formatting issues in phone numbers
    - Invalid records (bad email formats, negative purchase amounts)
    """
    logger.info(f"Creating synthetic mock data at: {output_path}")
    
    # Base clean-ish records
    base_data = [
        {"customer_id": "C1001", "first_name": "Alice", "last_name": "Smith", "email": "alice.smith@example.com", "phone": "123-456-7890", "signup_date": "2025-01-15", "country": "USA", "purchase_amount": "150.50"},
        {"customer_id": "C1002", "first_name": "Bob", "last_name": "Johnson", "email": "bob.j@example.net", "phone": "(987) 654-3210", "signup_date": "2025-02-10", "country": "Canada", "purchase_amount": "45.00"},
        {"customer_id": "C1003", "first_name": "Charlie", "last_name": "Brown", "email": "charlie.b@gmail.com", "phone": "555-019-2834", "signup_date": "2025-03-01", "country": "USA", "purchase_amount": "320.00"},
        {"customer_id": "C1004", "first_name": "David", "last_name": "Miller", "email": "david.miller@example.org", "phone": "444.123.4567", "signup_date": "2025-04-12", "country": "UK", "purchase_amount": "75.25"},
        {"customer_id": "C1005", "first_name": "Emma", "last_name": "Davis", "email": "emma.davis@yahoo.com", "phone": "+1-202-555-0143", "signup_date": "2025-05-05", "country": "Australia", "purchase_amount": "1200.00"},
    ]
    
    noisy_records = [
        # Whitespace noise in text and wrong casings
        {"customer_id": "C1006", "first_name": " Frank  ", "last_name": "Wilson", "email": " FRANK.W@example.com ", "phone": "2025550189", "signup_date": "2025-05-10", "country": "usa", "purchase_amount": "23.40"},
        
        # Missing values (missing country and missing purchase amount)
        {"customer_id": "C1007", "first_name": "Grace", "last_name": "Lee", "email": "grace.lee@example.com", "phone": "301-555-0177", "signup_date": "2025-05-12", "country": None, "purchase_amount": None},
        
        # Exact duplicate of C1001 (representing tracking error or duplicate ingest)
        {"customer_id": "C1001", "first_name": "Alice", "last_name": "Smith", "email": "alice.smith@example.com", "phone": "123-456-7890", "signup_date": "2025-01-15", "country": "USA", "purchase_amount": "150.50"},
        
        # Duplicate email conflict (C1008 has same email as Charlie Brown C1003 but updated phone/amount)
        {"customer_id": "C1008", "first_name": "Charlie", "last_name": "Brown", "email": "charlie.b@gmail.com", "phone": "555-999-8888", "signup_date": "2025-05-01", "country": "USA", "purchase_amount": "400.00"},
        
        # Duplicate phone conflict (same phone as Bob Johnson C1002 but email/purchase changed)
        {"customer_id": "C1009", "first_name": "Robert", "last_name": "Johnson", "email": "rob.j@example.net", "phone": "(987) 654-3210", "signup_date": "2025-05-02", "country": "Canada", "purchase_amount": "50.00"},
        
        # Name similarity/fuzzy duplicate (representing double registration)
        {"customer_id": "C1010", "first_name": "Emma", "last_name": "Davies", "email": "emma.d@yahoo.com", "phone": "+1-202-555-0143", "signup_date": "2025-05-06", "country": "Australia", "purchase_amount": "150.00"},
        
        # Invalid email formatting (missing @, missing domain)
        {"customer_id": "C1011", "first_name": "Ian", "last_name": "Taylor", "email": "ian.taylor.invalid", "phone": "777-888-9999", "signup_date": "2025-04-20", "country": "UK", "purchase_amount": "10.00"},
        
        # Negative purchase amount (Data entry error)
        {"customer_id": "C1012", "first_name": "Julia", "last_name": "Thomas", "email": "julia.t@example.com", "phone": "222-333-4444", "signup_date": "2025-03-15", "country": "Germany", "purchase_amount": "-50.00"},
        
        # Future signup date (Invalid)
        {"customer_id": "C1013", "first_name": "Kevin", "last_name": "White", "email": "kevin.white@example.com", "phone": "888-555-0122", "signup_date": "2027-12-25", "country": "USA", "purchase_amount": "80.00"},
        
        # Completely empty record fields except ID
        {"customer_id": "C1014", "first_name": None, "last_name": None, "email": None, "phone": None, "signup_date": None, "country": None, "purchase_amount": None}
    ]
    
    all_data = base_data + noisy_records
    df = pd.DataFrame(all_data)
    
    # Save the synthetic dataset
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info(f"Mock raw customer file generated successfully at {output_path} with {len(df)} rows.")
