from datetime import datetime
from venv import logger

from clean import clean_dataframe
from config import CONFIG
from deduplicate import deduplicate_customers
from ingest import ingest_all_sources
from validate import run_quality_checks
from visualize import generate_eda_report


def run_pipeline():
    """
    Main pipeline entry point.
    Orchestrates: Ingest -> Clean -> Deduplicate -> Validate -> Visualize -> Export
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("SHOPSTREAM CUSTOMER DATA QUALITY PIPELINE")
    logger.info(f"Run started: {start_time.isoformat()}")
    logger.info("=" * 60)

    # Step 1: Ingest
    combined = ingest_all_sources()
    input_count = len(combined)

    # Step 2: Clean
    cleaned = clean_dataframe(combined)

    # Step 3: Deduplicate
    deduped = deduplicate_customers(cleaned)
    if "opt_out" in deduped.columns:
        deduped["opt_out"] = deduped["opt_out"].astype("boolean")

    # Step 4: AI Region Inference (optional — comment out if no API key)
    # deduped = infer_region_with_llm(deduped)

    # Step 5: Quality Validation
    logger.info("STEP 4: Quality Validation")
    quality_report = run_quality_checks(deduped)

    # Step 6: Visualize
    generate_eda_report(deduped, CONFIG["output_dir"])

    # Step 7: Export
    logger.info("STEP 6: Exporting Results")

    parquet_path = CONFIG["output_dir"] / "golden_customers.parquet"
    deduped.to_parquet(parquet_path, index=False, engine="pyarrow", compression="gzip")
    logger.info(f"  Parquet export: {parquet_path} ({parquet_path.stat().st_size / 1024:.1f} KB)")

    csv_path = CONFIG["output_dir"] / "golden_customers.csv"
    deduped.to_csv(csv_path, index=False, encoding="utf-8-sig")   # BOM for Excel compatibility
    logger.info(f"  CSV export: {csv_path}")

    report_path = CONFIG["output_dir"] / "quality_report.csv"
    quality_report.to_csv(report_path, index=False)
    logger.info(f"  Quality report: {report_path}")

    # Summary
    duration = (datetime.now() - start_time).total_seconds()
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info(f"  Input records:          {input_count:,}")
    logger.info(f"  Output (golden) records:{len(deduped):,}")
    logger.info(f"  Duplicates removed:     {input_count - len(deduped):,}")
    logger.info(f"  Quality checks passed:  {(quality_report['status'] == 'PASS').sum()}/{len(quality_report)}")
    logger.info(f"  Duration:               {duration:.1f}s")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_pipeline()