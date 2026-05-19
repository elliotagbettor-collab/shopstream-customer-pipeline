import logging
import pandas as pd
import numpy as np
import config

logger = logging.getLogger("pipeline.deduplicate")

def levenshtein_ratio(s1: str, s2: str) -> float:
    """
    Calculates the Levenshtein distance similarity ratio between two strings.
    Returns a score between 0 and 100.
    """
    if not isinstance(s1, str) or not isinstance(s2, str):
        return 0.0
        
    s1 = s1.strip().lower()
    s2 = s2.strip().lower()
    
    if s1 == s2:
        return 100.0
    if not s1 or not s2:
        return 0.0
        
    len1, len2 = len(s1), len(s2)
    # Initialize matrix
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    
    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j
        
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            if s1[i - 1] == s2[j - 1]:
                cost = 0
            else:
                cost = 2 # weight substitution as 2 (standard edit distance matching)
            dp[i][j] = min(
                dp[i - 1][j] + 1,       # Deletion
                dp[i][j - 1] + 1,       # Insertion
                dp[i - 1][j - 1] + cost # Substitution
            )
            
    # Calculate similarity ratio
    total_len = len1 + len2
    ratio = ((total_len - dp[len1][len2]) / total_len) * 100.0
    return ratio

def merge_duplicate_group(group: pd.DataFrame) -> pd.Series:
    """
    Merges a group of duplicate records into a single consolidated record.
    - signup_date: Takes the earliest signup date.
    - purchase_amount: Sums all purchase amounts (lifetime value).
    - first_name, last_name, email, phone, country: Takes the latest active non-null value.
    - customer_id: Takes the first customer ID in the group.
    """
    # Sort the group by signup_date (placing earliest signups first)
    # Handle NaT by placing them last
    sorted_group = group.sort_values(by="signup_date", na_position="last")
    
    merged = {}
    
    # Retrieve the group's name (the grouping key value) from the original group DataFrame
    group_key_val = getattr(group, "name", None)
    
    # Customer ID (First ID)
    if "customer_id" in sorted_group.columns:
        merged["customer_id"] = sorted_group["customer_id"].iloc[0]
    else:
        merged["customer_id"] = group_key_val
        
    # Signup Date (Earliest)
    if "signup_date" in sorted_group.columns:
        merged["signup_date"] = sorted_group["signup_date"].min()
    else:
        merged["signup_date"] = group_key_val
        
    # Purchase Amount (Sum for lifetime value)
    if "purchase_amount" in sorted_group.columns:
        merged["purchase_amount"] = sorted_group["purchase_amount"].sum()
    else:
        merged["purchase_amount"] = group_key_val
        
    # Demographic / contact fields: take the latest non-null value (last in sorted group)
    for col in ["first_name", "last_name", "email", "phone", "country"]:
        if col in sorted_group.columns:
            non_null_vals = sorted_group[col].dropna()
            if not non_null_vals.empty:
                merged[col] = non_null_vals.iloc[-1]
            else:
                merged[col] = None
        else:
            merged[col] = group_key_val
            
    return pd.Series(merged)

def deduplicate_dataframe(df: pd.DataFrame, use_fuzzy: bool = True) -> pd.DataFrame:
    """
    Orchestrates the deduplication of the customer DataFrame.
    
    Steps:
    1. Exact row deduplication.
    2. Grouping & merging on matching customer_id.
    3. Grouping & merging on unique contact fields (email, phone).
    4. Optional fuzzy name similarity matching for contacts with shared details.
    """
    if df.empty:
        logger.info("Empty dataframe passed for deduplication.")
        return df
        
    initial_rows = len(df)
    logger.info(f"Starting deduplication. Initial record count: {initial_rows}")
    
    # Step 1: Remove exact matching rows
    dedup_df = df.drop_duplicates()
    exact_duplicates_removed = initial_rows - len(dedup_df)
    if exact_duplicates_removed > 0:
        logger.info(f"Removed {exact_duplicates_removed} exact duplicate records.")
        
    # Standardize empty/null strings in email & phone to facilitate groupings
    dedup_df = dedup_df.copy()
    for col in ["email", "phone", "customer_id"]:
        if col in dedup_df.columns:
            dedup_df[col] = dedup_df[col].replace(r"^\s*$", np.nan, regex=True)
            
    # Step 2: Merge on customer_id
    if "customer_id" in dedup_df.columns:
        logger.info("Merging duplicates with matching customer_id...")
        # Separate rows with valid customer_id from nulls
        has_id = dedup_df[dedup_df["customer_id"].notna()]
        no_id = dedup_df[dedup_df["customer_id"].isna()]
        
        # Merge has_id rows by customer_id
        merged_ids = has_id.groupby("customer_id", as_index=False).apply(merge_duplicate_group)
        
        # Re-combine
        dedup_df = pd.concat([merged_ids, no_id], ignore_index=True)
        logger.info(f"Record count after customer_id merge: {len(dedup_df)}")
        
    # Step 3: Merge on Email (if not null)
    if "email" in dedup_df.columns:
        logger.info("Merging duplicates with matching email...")
        has_email = dedup_df[dedup_df["email"].notna()]
        no_email = dedup_df[dedup_df["email"].isna()]
        
        merged_emails = has_email.groupby("email", as_index=False).apply(merge_duplicate_group)
        dedup_df = pd.concat([merged_emails, no_email], ignore_index=True)
        logger.info(f"Record count after email merge: {len(dedup_df)}")
        
    # Step 4: Merge on Phone (if not null)
    if "phone" in dedup_df.columns:
        logger.info("Merging duplicates with matching phone...")
        has_phone = dedup_df[dedup_df["phone"].notna()]
        no_phone = dedup_df[dedup_df["phone"].isna()]
        
        merged_phones = has_phone.groupby("phone", as_index=False).apply(merge_duplicate_group)
        dedup_df = pd.concat([merged_phones, no_phone], ignore_index=True)
        
        # We need to drop duplicates that might have been reintroduced/re-grouped
        dedup_df = dedup_df.drop_duplicates(subset=["customer_id"])
        logger.info(f"Record count after phone merge: {len(dedup_df)}")
        
    # Step 5: Optional Fuzzy Matching (e.g. same phone or email but slightly different names)
    if use_fuzzy and len(dedup_df) > 1:
        logger.info("Executing fuzzy matching deduplication...")
        merged_indices = set()
        rows_to_drop = []
        
        # Let's check for pairs with very similar names and matching phone/email
        records = dedup_df.to_dict(orient="records")
        num_records = len(records)
        
        for i in range(num_records):
            if i in merged_indices:
                continue
            for j in range(i + 1, num_records):
                if j in merged_indices:
                    continue
                    
                rec1 = records[i]
                rec2 = records[j]
                
                # Check if they share a key (either same email or same phone)
                shared_key = False
                if rec1["email"] and rec1["email"] == rec2["email"]:
                    shared_key = True
                if rec1["phone"] and rec1["phone"] == rec2["phone"]:
                    shared_key = True
                    
                if shared_key:
                    # Check name similarity
                    name1 = f"{rec1['first_name']} {rec1['last_name']}"
                    name2 = f"{rec2['first_name']} {rec2['last_name']}"
                    
                    similarity = levenshtein_ratio(name1, name2)
                    if similarity >= config.FUZZY_MATCH_THRESHOLD:
                        logger.info(f"Fuzzy match found between C_ID {rec1['customer_id']} ({name1}) and C_ID {rec2['customer_id']} ({name2}) - Similarity: {similarity:.1f}%")
                        
                        # Merge the two rows
                        temp_df = pd.DataFrame([rec1, rec2])
                        merged_series = merge_duplicate_group(temp_df)
                        
                        # Update record i with the merged values
                        records[i] = merged_series.to_dict()
                        merged_indices.add(j)
                        rows_to_drop.append(dedup_df.index[j])
                        
        if rows_to_drop:
            # Reconstruct the DataFrame from updated records, filtering out dropped ones
            active_records = [records[idx] for idx in range(num_records) if idx not in merged_indices]
            dedup_df = pd.DataFrame(active_records)
            logger.info(f"Fuzzy deduplication merged and removed {len(rows_to_drop)} fuzzy duplicates.")
            
    final_rows = len(dedup_df)
    duplicates_merged = initial_rows - final_rows
    logger.info(f"Deduplication completed. Final record count: {final_rows}. Total duplicates resolved: {duplicates_merged}")
    
    return dedup_df
