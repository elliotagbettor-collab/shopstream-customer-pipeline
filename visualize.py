import os
import io
import base64
import logging
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import config

logger = logging.getLogger("pipeline.visualize")

# Apply modern aesthetic settings globally
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
    "figure.titlesize": 16,
    "axes.titlesize": 14,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.facecolor": "#ffffff",
    "axes.facecolor": "#f8f9fa",
})

def plot_to_base64() -> str:
    """Converts the current matplotlib figure to a Base64-encoded PNG string."""
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode("utf-8")
    plt.close()
    return img_str

def generate_eda_charts(df: pd.DataFrame) -> dict:
    """
    Generates exploratory charts from the cleaned customer dataset:
    1. Geographic breakdown (bar chart)
    2. Purchase value distribution (hist/kde)
    3. Signup dates trend (line chart)
    
    Returns a dictionary mapping chart names to their Base64-encoded PNG strings.
    """
    logger.info("Generating analytical charts for the dataset.")
    charts = {}
    
    # Check if empty
    if df.empty:
        logger.warning("Empty dataframe, skipping chart generation.")
        return charts
        
    # Chart 1: Country distribution
    try:
        plt.figure(figsize=(7, 4))
        country_counts = df["country"].value_counts().reset_index()
        country_counts.columns = ["Country", "Customers"]
        
        # Color palette
        palette = sns.color_palette("viridis", len(country_counts))
        sns.barplot(data=country_counts, x="Country", y="Customers", palette=palette, hue="Country", legend=False)
        plt.title("Customer Distribution by Country", fontweight="bold", pad=15)
        plt.ylabel("Number of Customers")
        plt.xlabel("Country")
        plt.gca().spines["top"].set_visible(False)
        plt.gca().spines["right"].set_visible(False)
        plt.tight_layout()
        charts["country_dist"] = plot_to_base64()
        logger.info("Geographic chart generated successfully.")
    except Exception as e:
        logger.error(f"Error generating country distribution chart: {e}")
        
    # Chart 2: Purchase amount distribution
    try:
        plt.figure(figsize=(7, 4))
        sns.histplot(data=df, x="purchase_amount", kde=True, color="#2a9d8f", bins=10)
        plt.title("Purchase Amount Distribution", fontweight="bold", pad=15)
        plt.ylabel("Frequency")
        plt.xlabel("Purchase Amount ($)")
        plt.gca().spines["top"].set_visible(False)
        plt.gca().spines["right"].set_visible(False)
        plt.tight_layout()
        charts["purchase_dist"] = plot_to_base64()
        logger.info("Purchase distribution chart generated successfully.")
    except Exception as e:
        logger.error(f"Error generating purchase amount distribution chart: {e}")
        
    # Chart 3: Signup trends
    try:
        plt.figure(figsize=(7, 4))
        df_dates = df.copy()
        
        # Handle cases where signup dates are null or not datetimes
        if pd.api.types.is_datetime64_any_dtype(df_dates["signup_date"]):
            df_dates = df_dates.dropna(subset=["signup_date"])
            # Group by year-month
            df_dates["signup_month"] = df_dates["signup_date"].dt.to_period("M")
            monthly_trend = df_dates.groupby("signup_month").size().reset_index(name="Signups")
            monthly_trend["signup_month"] = monthly_trend["signup_month"].dt.to_timestamp()
            
            sns.lineplot(data=monthly_trend, x="signup_month", y="Signups", marker="o", color="#4361ee", linewidth=2.5)
            plt.title("Customer Acquisition Trend", fontweight="bold", pad=15)
            plt.ylabel("New Signups")
            plt.xlabel("Month")
            plt.gca().spines["top"].set_visible(False)
            plt.gca().spines["right"].set_visible(False)
            plt.xticks(rotation=45)
            plt.tight_layout()
            charts["signup_trend"] = plot_to_base64()
            logger.info("Customer acquisition trend chart generated successfully.")
        else:
            logger.warning("signup_date is not datetime. Skipping trend chart.")
    except Exception as e:
        logger.error(f"Error generating signup trends chart: {e}")
        
    return charts

def build_html_report(df: pd.DataFrame, validation_report: dict, output_path: str = None):
    """
    Compiles an elegant, standalone, highly styled HTML report for the user.
    Integrates metrics, validation outcomes, and charts in Base64 representation.
    """
    if output_path is None:
        output_path = config.OUTPUT_EDA_REPORT
        
    logger.info(f"Building premium HTML report at: {output_path}")
    
    # 1. Generate the charts
    charts = generate_eda_charts(df)
    
    # 2. Extract metrics
    total_customers = len(df)
    total_revenue = df["purchase_amount"].sum() if "purchase_amount" in df.columns else 0.0
    avg_purchase = df["purchase_amount"].mean() if "purchase_amount" in df.columns and total_customers > 0 else 0.0
    health_score = validation_report.get("overall_health_score_pct", 100.0)
    
    # Construct rows for tabular display of details
    df_preview_rows = ""
    for idx, row in df.head(10).iterrows():
        signup_str = row["signup_date"].strftime("%Y-%m-%d") if isinstance(row["signup_date"], pd.Timestamp) else str(row["signup_date"])
        df_preview_rows += f"""
        <tr>
            <td><strong>{row['customer_id']}</strong></td>
            <td>{row['first_name']} {row['last_name']}</td>
            <td>{row['email']}</td>
            <td>{row['phone']}</td>
            <td>{signup_str}</td>
            <td><span class="country-badge">{row['country']}</span></td>
            <td class="amount">${row['purchase_amount']:.2f}</td>
        </tr>
        """
        
    # Construct rows for validation metrics
    validation_rows = ""
    for key, val in validation_report.items():
        if key in ["total_records", "fatal_records_removed", "overall_health_score_pct", "missing_columns"]:
            continue
        # Format names nicely
        label = key.replace("_", " ").title()
        status_badge = '<span class="status-pass">PASS</span>' if val == 0 else f'<span class="status-fail">WARN ({val})</span>'
        validation_rows += f"""
        <tr>
            <td>{label}</td>
            <td>{val}</td>
            <td>{status_badge}</td>
        </tr>
        """
        
    # Embedded charts HTML
    charts_html = ""
    if "signup_trend" in charts:
        charts_html += f"""
        <div class="card chart-card">
            <h3>Customer Acquisition</h3>
            <img src="data:image/png;base64,{charts['signup_trend']}" alt="Acquisition Trend">
        </div>
        """
    if "country_dist" in charts:
        charts_html += f"""
        <div class="card chart-card">
            <h3>Geographic Breakdown</h3>
            <img src="data:image/png;base64,{charts['country_dist']}" alt="Geographic Distribution">
        </div>
        """
    if "purchase_dist" in charts:
        charts_html += f"""
        <div class="card chart-card">
            <h3>Revenue Spread</h3>
            <img src="data:image/png;base64,{charts['purchase_dist']}" alt="Purchase spread">
        </div>
        """

    # HTML Template
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShopStream Customer Data Pipeline Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #f8fafc;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --primary: #4361ee;
            --primary-gradient: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%);
            --accent: #2a9d8f;
            --accent-gradient: linear-gradient(135deg, #10b981 0%, #059669 100%);
            --card-bg: #ffffff;
            --border-color: #e2e8f0;
            --shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
            --radius: 16px;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-main);
            line-height: 1.6;
            padding: 2.5rem 1.5rem;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        header {{
            margin-bottom: 3rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 2rem;
        }}

        h1 {{
            font-family: 'Outfit', sans-serif;
            font-size: 2.25rem;
            font-weight: 800;
            background: var(--primary-gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }}

        .report-meta {{
            font-size: 0.875rem;
            color: var(--text-muted);
            text-align: right;
        }}

        .timestamp {{
            font-weight: 600;
            color: var(--text-main);
        }}

        /* KPI Dashboard Grid */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }}

        .kpi-card {{
            background: var(--card-bg);
            border-radius: var(--radius);
            padding: 1.75rem;
            box-shadow: var(--shadow);
            border: 1px solid var(--border-color);
            position: relative;
            overflow: hidden;
            transition: all 0.3s ease;
        }}

        .kpi-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }}

        .kpi-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: var(--primary-gradient);
        }}

        .kpi-card.accent::before {{
            background: var(--accent-gradient);
        }}

        .kpi-title {{
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
            font-weight: 600;
        }}

        .kpi-val {{
            font-family: 'Outfit', sans-serif;
            font-size: 2rem;
            font-weight: 800;
            color: var(--text-main);
        }}

        /* Main Section layout */
        .section-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
            margin-bottom: 3rem;
        }}

        @media (min-width: 992px) {{
            .section-grid {{
                grid-template-columns: 1.2fr 0.8fr;
            }}
        }}

        .card {{
            background: var(--card-bg);
            border-radius: var(--radius);
            padding: 2rem;
            box-shadow: var(--shadow);
            border: 1px solid var(--border-color);
            margin-bottom: 2rem;
        }}

        .card h2 {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            color: var(--text-main);
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 0.75rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        /* Charts Layout */
        .charts-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        .chart-card {{
            text-align: center;
            padding: 1.5rem;
            margin-bottom: 0;
        }}

        .chart-card h3 {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            color: var(--text-main);
        }}

        .chart-card img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
        }}

        /* Table custom styling */
        .table-responsive {{
            overflow-x: auto;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.875rem;
        }}

        th {{
            background-color: #f1f5f9;
            color: #475569;
            font-weight: 600;
            padding: 1rem;
            border-bottom: 2px solid var(--border-color);
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
        }}

        td {{
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            color: #334155;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover td {{
            background-color: #f8fafc;
        }}

        .amount {{
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            color: var(--text-main);
        }}

        .country-badge {{
            background: #eff6ff;
            color: #1e40af;
            padding: 0.25rem 0.5rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        .status-pass {{
            background: #ecfdf5;
            color: #065f46;
            padding: 0.25rem 0.5rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        .status-fail {{
            background: #fffbeb;
            color: #92400e;
            padding: 0.25rem 0.5rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        footer {{
            text-align: center;
            margin-top: 5rem;
            color: var(--text-muted);
            font-size: 0.875rem;
            border-top: 1px solid var(--border-color);
            padding-top: 2rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>ShopStream Customer Pipeline</h1>
                <p style="color: var(--text-muted);">Exploratory Data Analysis & Quality Dashboard</p>
            </div>
            <div class="report-meta">
                <p>Generated Report</p>
                <p class="timestamp">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            </div>
        </header>

        <!-- KPI dashboard cards -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <p class="kpi-title">Total Customers</p>
                <p class="kpi-val">{total_customers}</p>
            </div>
            <div class="kpi-card accent">
                <p class="kpi-title">Lifetime Value (LTV)</p>
                <p class="kpi-val">${total_revenue:,.2f}</p>
            </div>
            <div class="kpi-card">
                <p class="kpi-title">Avg Purchase Amount</p>
                <p class="kpi-val">${avg_purchase:,.2f}</p>
            </div>
            <div class="kpi-card accent">
                <p class="kpi-title">Data Quality Score</p>
                <p class="kpi-val">{health_score}%</p>
            </div>
        </div>

        <!-- Section grid containing visualisations and validation results -->
        <div class="section-grid">
            <div style="display: flex; flex-direction: column;">
                <div class="card">
                    <h2>Cleaned Customer Register (Top 10 rows)</h2>
                    <div class="table-responsive">
                        <table>
                            <thead>
                                <tr>
                                    <th>Cust ID</th>
                                    <th>Full Name</th>
                                    <th>Email</th>
                                    <th>Phone</th>
                                    <th>Signup Date</th>
                                    <th>Country</th>
                                    <th>LTV</th>
                                </tr>
                            </thead>
                            <tbody>
                                {df_preview_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div>
                <div class="card">
                    <h2>Validation Checks Report</h2>
                    <div class="table-responsive">
                        <table>
                            <thead>
                                <tr>
                                    <th>Data Audit Check</th>
                                    <th>Violations Count</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>Fatal Records Filtered (No Cust ID)</td>
                                    <td>{validation_report.get('fatal_records_removed', 0)}</td>
                                    <td>{'PASS' if validation_report.get('fatal_records_removed', 0) == 0 else '<span class="status-fail">REMOVED</span>'}</td>
                                </tr>
                                {validation_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Analytical Insights</h2>
            <div class="charts-container">
                {charts_html}
            </div>
        </div>

        <footer>
            <p>ShopStream Customer Ingest and In-Memory Cleaning Pipeline | Built with Python, Pandas & Seaborn</p>
        </footer>
    </div>
</body>
</html>
"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    logger.info(f"Dashboard successfully compiled and written to {output_path}.")
