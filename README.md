# ShopStream Customer Data Engineering Pipeline

A highly modular, professional Python-based data engineering pipeline designed to ingest, clean, deduplicate, validate, visualize, and export customer data for ShopStream. 

This pipeline handles customer profiles, corrects common data anomalies, aggregates duplicate profiles (using both exact fields and fuzzy string matching), calculates data quality health indexes, and automatically generates an interactive HTML reporting dashboard.

---

## 📂 Folder Structure

```text
├── pipeline.py          # Core orchestrator and CLI entry point
├── config.py            # Global paths, schema structures, and business rules
├── ingest.py            # Safety loading of CSV/Excel/JSON & mock generator
├── clean.py             # Case normalization, datatype conversions, and parsing
├── deduplicate.py       # Exact, grouped key merges, and custom fuzzy matching
├── validate.py          # Data validation schema and health metrics auditor
├── visualize.py         # Seaborn analytical plots and Base64 dashboard compiler
├── export.py            # Multi-format exports (CSV, Parquet, JSON) and runtime summaries
├── requirements.txt     # Third-party standard data tool versions
├── README.md            # Comprehensive documentation
├── .gitignore           # Python, logs, and data path exclusions
│
├── tests/               # Unit testing framework
│   ├── test_clean.py
│   ├── test_validate.py
│   └── test_deduplicate.py
│
├── data/
│   ├── raw/             # Raw ingestion sources (e.g., customer_raw.csv)
│   └── processed/       # Cleaned outputs, parquet DBs, and HTML reports
│
└── logs/                # Rolling runtime log files (e.g., pipeline.log)
```

---

## ⚙️ Core Architecture & Pipeline Phases

The pipeline processes customer data in six distinct phases:

1. **Ingest (`ingest.py`)**: Safely reads input files (CSV, Excel, JSON). If no raw dataset exists, it dynamically generates a synthetic, realistic "noisy" customer dataset in `data/raw/customer_raw.csv` containing formatting errors, nulls, duplicates, and business anomalies to allow immediate end-to-end execution.
2. **Clean (`clean.py`)**: Normalizes names (title case, space trimming), emails (lowercasing, trimming), phone numbers (formatting to standard `XXX-XXX-XXXX` or digits only), countries, datetimes, and ensures purchase amounts are numeric.
3. **Validate (`validate.py`)**: Audits data structures. Filters out critical records missing a `customer_id`. Performs schema regex checks for valid emails, alerts for negative purchase amounts, logs future signups, and issues an **Overall Data Quality Health Score**.
4. **Deduplicate (`deduplicate.py`)**: Consolidates profiles. It groups records by duplicate IDs, emails, or phone numbers, and merges them by summing total purchase amounts (Lifetime Value) and retaining the earliest `signup_date` and latest demographic info. Additionally, a native, dependency-free **Fuzzy Similarity algorithm (Levenshtein Distance)** matches customer names that share partial data but have slight typos (e.g., "Emma Davis" vs. "Emma Davies").
5. **Visualize (`visualize.py`)**: Plots customer distributions by country, LTV (purchase) spreads, and acquisition trend graphs. These charts are translated to Base64 strings and compiled into a standalone, portable, responsive **HTML Analytical Dashboard** (`eda_report.html`) containing modern CSS layouts, charts, and metrics.
6. **Export (`export.py`)**: Saves the finalized consolidated database in high-efficiency Parquet, portable JSON, and flat CSV formats. Outputs a runtime file metadata summary (`run_summary.json`).

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure Python 3.9 or higher is installed on your operating system.

### 2. Setup environment and install dependencies
Create a virtual environment and install the required modules:

```bash
# Create a virtual environment
python -m venv .venv

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Activate virtual environment (macOS/Linux)
source .venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

---

## 🖥️ Command Line Usage

Execute `pipeline.py` to trigger the end-to-end execution. If no custom arguments are provided, it automatically creates a mock customer dataset in `data/raw/` and runs all stages.

```bash
# Run with default settings (auto-generates noisy mock dataset and outputs all files)
python pipeline.py
```

### Advanced CLI Arguments

You can run the pipeline with custom inputs, format selections, and behavior flags:

| Argument | Shorthand | Description | Default |
|---|---|---|---|
| `--input` | `-i` | Specify a custom path to a raw dataset (CSV, Excel, JSON). | `data/raw/customer_raw.csv` |
| `--formats` | `-f` | Select one or more target export formats from `csv`, `parquet`, or `json`. | `csv parquet json` |
| `--no-fuzzy` | - | Disables fuzzy Levenshtein name-matching during deduplication. | `False` |
| `--skip-viz` | - | Skips plotting visual graphs and compiling the HTML dashboard. | `False` |
| `--dry-run` | - | Executes all parsing and auditing steps but does not write any outputs. | `False` |

#### CLI Examples

```bash
# Process a custom dataset and export only CSV and Parquet
python pipeline.py -i paths/to/my_data.xlsx -f csv parquet

# Run deduplication without fuzzy matching and skip report generation
python pipeline.py --no-fuzzy --skip-viz

# Perform a dry-run to audit input quality without writing outputs to disk
python pipeline.py -i data/raw/customer_raw.csv --dry-run
```

---

## 🧪 Testing

The codebase includes a comprehensive unit testing suite inside `tests/` powered by `pytest`. To run tests, execute:

```bash
# Run all unit tests
pytest

# Run tests with detailed verbose logging
pytest -v
```

Tests cover:
- **Cleaning logic (`tests/test_clean.py`)**: normalizations of names, emails, phone numbers, and countries.
- **Validation logic (`tests/test_validate.py`)**: email regex checks, health metric calculations, and error-handling.
- **Deduplication logic (`tests/test_deduplicate.py`)**: record mergers (LTV summing, signup date prioritizing) and fuzzy name matching.

---

## 📊 Outputs & Artifacts

Following a successful run, the following files are produced in the `data/processed/` and `logs/` folders:

- **`data/processed/customer_cleaned.csv`**: A clean, deduplicated tabular customer dataset.
- **`data/processed/customer_cleaned.parquet`**: High-performance, compressed columnar parquet database.
- **`data/processed/customer_cleaned.json`**: Structured JSON representation of the cleaned register.
- **`data/processed/eda_report.html`**: A portable, beautiful responsive HTML dashboard displaying KPIs, clean data previews, audit issues, and Base64-embedded Seaborn charts.
- **`data/processed/run_summary.json`**: Execution metadata including duration, records count, and file paths.
- **`logs/pipeline.log`**: Standard logging history capturing errors, warnings, merge stats, and execution steps.