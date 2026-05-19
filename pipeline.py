import sys
import argparse
import logging
from datetime import datetime
import config
import ingest
import clean
import deduplicate
import validate
import visualize
import export

def setup_pipeline_logging():
    """Initializes standard file and console logging based on config values."""
    log_format = logging.Formatter(config.LOGGING_CONFIG["format"])
    
    # Root logger
    logger = logging.getLogger()
    logger.setLevel(config.LOGGING_CONFIG["level"])
    
    # Clear any existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
        
    # File handler
    file_handler = logging.FileHandler(config.LOGGING_CONFIG["filename"], encoding="utf-8")
    file_handler.setFormatter(log_format)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    logger.addHandler(console_handler)

def parse_pipeline_arguments():
    """Defines and parses command line arguments."""
    parser = argparse.ArgumentParser(
        description="ShopStream Customer Data Engineering Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        default=None,
        help="Path to the raw input customer dataset (CSV/Excel/JSON)"
    )
    parser.add_argument(
        "-f", "--formats",
        nargs="+",
        default=["csv", "parquet", "json"],
        choices=["csv", "parquet", "json"],
        help="Target output format(s) for the cleaned consolidated register"
    )
    parser.add_argument(
        "--no-fuzzy",
        action="store_true",
        help="Disable fuzzy string similarity matching in the deduplication step"
    )
    parser.add_argument(
        "--skip-viz",
        action="store_true",
        help="Skip creation of visual plots and compilation of HTML EDA dashboard"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute all steps (ingestion, cleaning, validation, deduplication) but bypass file exporting"
    )
    return parser.parse_args()

def main():
    """Core pipeline orchestration script."""
    # Capture start time
    start_time = datetime.now()
    
    # Setup logger
    setup_pipeline_logging()
    logger = logging.getLogger("pipeline.main")
    
    logger.info("==================================================================")
    logger.info("Starting ShopStream Customer Data Pipeline execution.")
    logger.info("==================================================================")
    
    try:
        # Parse arguments
        args = parse_pipeline_arguments()
        
        # 1. Ingestion Phase
        logger.info("[PHASE 1] Ingesting customer data...")
        raw_df = ingest.load_data(args.input)
        raw_count = len(raw_df)
        
        # 2. Cleaning Phase
        logger.info("[PHASE 2] Cleaning customer records...")
        cleaned_df = clean.clean_dataframe(raw_df)
        
        # 3. Validation Phase
        logger.info("[PHASE 3] Validating and auditing data quality...")
        validated_df, validation_report = validate.validate_dataframe(cleaned_df)
        fatal_count = validation_report["fatal_records_removed"]
        
        # 4. Deduplication Phase
        logger.info("[PHASE 4] Resolving profile duplicates...")
        deduplicated_df = deduplicate.deduplicate_dataframe(
            validated_df, 
            use_fuzzy=not args.no_fuzzy
        )
        final_count = len(deduplicated_df)
        duplicates_resolved = (raw_count - fatal_count) - final_count
        
        # 5. Visualization and Reporting Phase
        if not args.skip_viz:
            logger.info("[PHASE 5] Compiling premium HTML dashboard...")
            if not args.dry_run:
                visualize.build_html_report(deduplicated_df, validation_report)
            else:
                logger.info("Dry-run active. Bypassing HTML report compilation.")
        else:
            logger.info("[PHASE 5] Skipping visualization and reporting (user flag).")
            
        # 6. Exporting Phase
        export_results = {}
        if not args.dry_run:
            logger.info("[PHASE 6] Saving consolidated records...")
            export_results = export.export_data(deduplicated_df, args.formats)
            
            # Write operational execution summary
            export.generate_run_summary(
                raw_count=raw_count,
                cleaned_count=final_count,
                duplicates_resolved=duplicates_resolved,
                validation_report=validation_report,
                export_results=export_results,
                start_time=start_time
            )
        else:
            logger.info("[PHASE 6] Dry-run active. Bypassing record saving.")
            
        # Summary reporting
        duration = (datetime.now() - start_time).total_seconds()
        logger.info("==================================================================")
        logger.info("ShopStream Customer Pipeline completed successfully!")
        logger.info(f"Total time elapsed: {duration:.3f} seconds")
        logger.info(f"Raw records ingested: {raw_count}")
        logger.info(f"Fatal records removed: {fatal_count}")
        logger.info(f"Duplicate records consolidated: {duplicates_resolved}")
        logger.info(f"Final clean database size: {final_count}")
        logger.info(f"Data quality health index: {validation_report['overall_health_score_pct']}%")
        if not args.dry_run and export_results:
            logger.info("Artifacts saved:")
            for fmt, path in export_results.items():
                logger.info(f"  - [{fmt.upper()}]: {path}")
            if not args.skip_viz:
                logger.info(f"  - [HTML DASHBOARD]: {config.OUTPUT_EDA_REPORT}")
        logger.info("==================================================================")
        
    except Exception as e:
        logger.exception("Pipeline execution failed due to an unhandled exception:")
        sys.exit(1)

if __name__ == "__main__":
    main()
