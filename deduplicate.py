from venv import logger

import pandas as pd

from config import CONFIG


def deduplicate_customers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deduplicate customer records across sources.

    Strategy:
        1. Sort by source priority (CRM is most trusted)
        2. Group by standardized email (primary key)
        3. Within each group, merge fields: take first non-null value
           from the highest-priority source
        4. GDPR compliance: if ANY source has opt_out=True, mark as opted out

    Args:
        df: Cleaned DataFrame with 'email', 'email_valid', 'source' columns.

    Returns:
        Deduplicated DataFrame with provenance tracking.
    """
    logger.info("STEP 3: Deduplication")
    initial_count = len(df)

    df["source_priority"] = df["source"].map(CONFIG["source_priority"]).fillna(99)
    df = df.sort_values("source_priority")

    def merge_group(group: pd.DataFrame) -> pd.Series:
        """Merge duplicate records, preferring higher-priority sources."""
        best = group.iloc[0].copy()

        # For key fields, take the first non-null value from priority-sorted group
        for col in ["phone", "region", "first_name", "last_name", "registration_date"]:
            if col in group.columns and pd.isna(best.get(col)):
                non_null = group[col].dropna()
                if len(non_null) > 0:
                    best[col] = non_null.iloc[0]

        # GDPR: opt-out from any source is final
        if "opt_out" in group.columns:
            best["opt_out"] = bool(group["opt_out"].fillna(False).astype(bool).any())

        # Provenance tracking
        best["sources"] = ",".join(group["source"].unique())
        best["source_count"] = len(group["source"].unique())

        return best

    # Deduplicate valid-email records on email key
    valid_mask = df["email_valid"] == True
    valid_df = df[valid_mask]
    invalid_df = df[~valid_mask]

    deduped = (
        valid_df
        .groupby("email", sort=False)
        .apply(merge_group, include_groups=False)
        .reset_index(drop=True)
    )

    # Append invalid-email records (cannot be deduplicated by email)
    result = pd.concat([deduped, invalid_df], ignore_index=True)
    if "opt_out" in result.columns:
        result["opt_out"] = result["opt_out"].astype("boolean")

    removed = initial_count - len(result)
    logger.info(f"  Records before deduplication: {initial_count}")
    logger.info(f"  Duplicate records removed: {removed}")
    logger.info(f"  Records after deduplication: {len(result)}")
    return result