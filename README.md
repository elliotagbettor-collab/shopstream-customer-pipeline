# Data Cleaning and Transformation Pipeline

This repository contains a Python-based data pipeline for cleaning, validating, and transforming raw customer data.

## Features

- **Robust Cleaning**: Handles missing values, duplicates, and invalid data formats.
- **Schema Validation**: Ensures data conforms to the expected structure.
- **Flexible Output**: Supports exporting cleaned data to CSV, Parquet, and JSON formats.
- **Logging**: Comprehensive logging of pipeline execution and issues.

## Setup

### 1. Create a Virtual Environment

```bash
py -m venv .venv
```

### 2. Activate the Virtual Environment

```bash
source .venv/Scripts/activate
.venv/Scripts/python.exe ingest.py
```

### 3. Install Dependencies

Ensure all required packages are installed:

```bash
pip install -r requirements.txt
```