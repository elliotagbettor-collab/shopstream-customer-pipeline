import os
import json
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import config

logger = logging.getLogger("pipeline.export")

def export_data(df: pd.DataFrame, formats: list[str] = None) -> dict[str, str]:
    """
    Exports the final processed customer DataFrame to multiple standard formats.
    
    Args:
        df (pd.DataFrame): Processed customer DataFrame.
        formats (list): Formats to save. E.g., ['csv', 'parquet', 'json']. 
                        If None, exports to all configured paths.
                        
    Returns:
        dict: Dict containing saved formats and their file paths.
    """
    if formats is None:
        formats = ["csv", "parquet", "json"]
        
    export_results = {}
    
    if df.empty:
        logger.warning("Empty dataframe provided to export_data. Writing empty files.")
        
    # Ensure processed directory exists
    config.DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Export CSV
    if "csv" in formats:
        try:
            path = config.OUTPUT_CLEANED_CSV
            df.to_csv(path, index=False)
            file_size_kb = Path(path).stat().st_size / 1024
            logger.info(f"Exported CSV to: {path} ({file_size_kb:.2f} KB)")
            export_results["csv"] = str(path)
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            
    # 2. Export Parquet
    if "parquet" in formats:
        try:
            path = config.OUTPUT_CLEANED_PARQUET
            # Parquet requires datetime objects rather than NaT/None if string parsing was done,
            # or pandas will convert them correctly.
            df.to_parquet(path, index=False, engine="pyarrow")
            file_size_kb = Path(path).stat().st_size / 1024
            logger.info(f"Exported Parquet to: {path} ({file_size_kb:.2f} KB)")
            export_results["parquet"] = str(path)
        except Exception as e:
            logger.error(f"Failed to export Parquet: {e}")
            
    # 3. Export JSON
    if "json" in formats:
        try:
            path = config.OUTPUT_CLEANED_JSON
            # Serialize datetimes correctly using isoformat
            df.to_json(path, orient="records", date_format="iso", indent=2)
            file_size_kb = Path(path).stat().st_size / 1024
            logger.info(f"Exported JSON to: {path} ({file_size_kb:.2f} KB)")
            export_results["json"] = str(path)
        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")
            
    return export_results

def generate_run_summary(
    raw_count: int, 
    cleaned_count: int, 
    duplicates_resolved: int, 
    validation_report: dict, 
    export_results: dict,
    start_time: datetime
) -> str:
    """
    Generates a structured execution metadata summary JSON file.
    
    Returns:
        str: Path to the generated run summary file.
    """
    summary_path = config.DATA_PROCESSED_DIR / "run_summary.json"
    end_time = datetime.now()
    duration_sec = (end_time - start_time).total_seconds()
    
    summary_data = {
        "pipeline_name": "ShopStream Customer Data Pipeline",
        "execution_timestamp": end_time.isoformat(),
        "duration_seconds": round(duration_sec, 3),
        "metrics": {
            "raw_records_ingested": raw_count,
            "fatal_records_removed": validation_report.get("fatal_records_removed", 0),
            "duplicates_resolved": duplicates_resolved,
            "final_clean_records": cleaned_count,
        },
        "quality_audit": {
            "health_score_pct": validation_report.get("overall_health_score_pct", 100.0),
            "missing_emails": validation_report.get("missing_emails", 0),
            "missing_phones": validation_report.get("missing_phones", 0),
            "invalid_emails": validation_report.get("invalid_emails", 0),
            "negative_purchase_amounts": validation_report.get("negative_purchase_amounts", 0),
            "future_signup_dates": validation_report.get("future_signup_dates", 0)
        },
        "artifacts_generated": export_results
    }
    
    try:
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)
        logger.info(f"Run summary metadata written to: {summary_path}")
        return str(summary_path)
    except Exception as e:
        logger.error(f"Failed to write run summary metadata: {e}")
        return ""
