"""
Core Business Analyst Tools for the MCP Analyst Server.
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import httpx
import numpy as np
import pandas as pd

load_dotenv()

DEFAULT_SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL", "")


def resolve_dataset_path(filename: str) -> Path:
    p = Path(filename)
    if p.exists():
        return p
    data_p = Path("data") / p.name
    if data_p.exists():
        return data_p
    return Path("data") / filename


def list_available_datasets() -> List[str]:
    """Lists all CSV files in the data directory."""
    data_dir = Path("data")
    return [f.name for f in data_dir.glob("*.csv")] if data_dir.exists() else []


def preview_dataset(filename: str = "global_sales.csv") -> Dict[str, Any]:
    """Inspects dataset dimensions, columns, and missing values."""
    path = resolve_dataset_path(filename)
    if not path.exists():
        return {"error": f"File '{filename}' not found."}
    
    df = pd.read_csv(path)
    return {
        "total_rows": len(df),
        "columns": list(df.columns),
        "missing_values": df.isnull().sum().to_dict(),
        "sample": df.head(3).to_dict(orient="records"),
    }


def fetch_live_fx_rates(from_currency: str = "EUR", to_currency: str = "USD") -> Dict[str, Any]:
    """Calls Frankfurter API to fetch live currency exchange rates."""
    if from_currency == to_currency:
        return {"base": from_currency, "target": to_currency, "rate": 1.0}
    
    url = f"https://api.frankfurter.dev/v1/latest?base={from_currency}&symbols={to_currency}"
    try:
        resp = httpx.get(url, timeout=5.0)
        data = resp.json()
        rate = data.get("rates", {}).get(to_currency, 1.0)
        return {"base": from_currency, "target": to_currency, "rate": rate}
    except Exception as e:
        return {"error": f"FX fetch failed: {str(e)}", "fallback_rate": 1.0}


def detect_anomalies(filename: str = "global_sales.csv", metric_col: str = "Revenue", z_threshold: float = 2.0) -> Dict[str, Any]:
    """Scans for negative revenue violations and Z-score outlier spikes."""
    path = resolve_dataset_path(filename)
    if not path.exists():
        return {"error": f"File '{filename}' not found."}
    
    df = pd.read_csv(path)
    anomalies = []
    
    negatives = df[df[metric_col] < 0]
    for _, row in negatives.iterrows():
        anomalies.append({
            "order_id": row.get("Order_ID", "N/A"),
            "country": row.get("Country", "N/A"),
            "value": float(row[metric_col]),
            "type": "BUSINESS_RULE_VIOLATION",
            "detail": "Negative monetary figure detected (invalid entry or unhandled return)"
        })
        
    positive_series = df[df[metric_col] >= 0][metric_col].dropna()
    if len(positive_series) > 3 and positive_series.std() > 0:
        mean = positive_series.mean()
        std = positive_series.std()
        z_scores = np.abs((positive_series - mean) / std)
        
        for idx in z_scores[z_scores >= z_threshold].index:
            row = df.loc[idx]
            anomalies.append({
                "order_id": row.get("Order_ID", "N/A"),
                "country": row.get("Country", "N/A"),
                "value": float(row[metric_col]),
                "type": "STATISTICAL_SPIKE",
                "detail": f"Value is {round(float(z_scores.loc[idx]), 2)} std deviations from mean"
            })
            
    return {
        "records_scanned": len(df),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies
    }


def generate_segment_matrix(filename: str = "global_sales.csv", index_col: str = "Country", column_col: str = "Category", val_col: str = "Revenue") -> Dict[str, Any]:
    """Computes a cross-tabulated segmentation matrix (Cohort/Pivot) of aggregated metrics across two dimensions."""
    path = resolve_dataset_path(filename)
    if not path.exists():
        return {"error": f"File '{filename}' not found."}
    
    df = pd.read_csv(path)
    if index_col not in df.columns or column_col not in df.columns:
        return {"error": f"Invalid grouping dimensions: '{index_col}' or '{column_col}' not in dataset."}
    
    pivot = pd.pivot_table(
        df,
        index=index_col,
        columns=column_col,
        values=val_col,
        aggfunc="sum",
        fill_value=0
    )
    
    records = []
    for idx_val in pivot.index:
        for col_val in pivot.columns:
            records.append({
                index_col: str(idx_val),
                column_col: str(col_val),
                val_col: float(pivot.loc[idx_val, col_val])
            })
            
    return {
        "index_dimension": index_col,
        "column_dimension": column_col,
        "metric": val_col,
        "pivot_data": records,
        "top_performing_segment": sorted(records, key=lambda x: x[val_col], reverse=True)[0] if records else {}
    }


def dispatch_slack_alert(message: str, webhook_url: str = "") -> str:
    """Dispatches a structured, plain-text alert payload to the configured Slack webhook channel."""
    target_url = webhook_url if webhook_url.strip() else DEFAULT_SLACK_WEBHOOK
    clean_msg = re.sub(r":[a-zA-Z0-9_+-]+:", "", message)
    clean_msg = re.sub(r"[^\x00-\x7F]+", "", clean_msg).strip()
    try:
        payload = {"text": f"*[Autonomous MCP Compliance Alert]*\n\n{clean_msg}"}
        resp = httpx.post(target_url, json=payload, timeout=8.0)
        if resp.status_code == 200:
            print(f"\n[LIVE SLACK NOTIFICATION SENT TO #all-mcp-analyst]:\n{clean_msg}\n")
            return "Alert posted to Slack #all-mcp-analyst successfully."
        else:
            return f"Slack returned HTTP {resp.status_code}: {resp.text}"
    except Exception as e:
        return f"Failed to post to Slack: {str(e)}"


def export_audit_summary(title: str, findings: List[str], output_filename: str = "audit_report.md") -> str:
    """Exports structured audit findings into a Markdown file and formal executive PDF on disk."""
    out_dir = Path("outputs/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / output_filename
    
    content = f"# {title}\n\n## Observations\n"
    for f in findings:
        content += f"- {f}\n"
    content += "\n---\n*Report generated via Custom MCP Server.*"
    
    report_path.write_text(content)
    
    # Compile formal PDF
    pdf_filename = report_path.stem + ".pdf"
    pdf_path = out_dir / pdf_filename
    try:
        from utils.pdf_generator import generate_formal_pdf
        pdf_bytes = generate_formal_pdf(report_title=title, markdown_content=content, findings=findings)
        pdf_path.write_bytes(pdf_bytes)
        return f"Report successfully written to {report_path.resolve()} and {pdf_path.resolve()}"
    except Exception:
        return f"Report successfully written to {report_path.resolve()}"
