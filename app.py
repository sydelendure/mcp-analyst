import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import httpx
import pandas as pd
import plotly.express as px
import streamlit as st
from client.mcp_client import CustomMCPClient as Client
from google import genai
from google.genai import types
from utils.pdf_generator import generate_formal_pdf

load_dotenv()

st.set_page_config(
    page_title="Enterprise DataOps Analyst",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Claude & Anthropic Executive Theme ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;0,6..72,700;1,6..72,400;1,6..72,600&family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400;1,600&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --font-serif: 'Newsreader', 'Lora', Georgia, 'Times New Roman', serif;
        --font-sans: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        --color-primary: #0284C7;
        --color-primary-light: #0EA5E9;
        --color-primary-subtle: #E0F2FE;
        --color-primary-bg: #F0F9FF;
        --color-border: #E2E8F0;
        --color-border-subtle: #F1F5F9;
        --color-surface: #FFFFFF;
        --color-bg: #F8FAFC;
        --color-text-main: #0F172A;
        --color-text-muted: #64748B;
        --color-text-subtle: #94A3B8;
    }

    html, body, [class*="css"], .stApp {
        font-family: var(--font-sans) !important;
        background-color: var(--color-bg) !important;
        color: var(--color-text-main) !important;
    }

    /* Claude Signature Serif for All Headings, Titles & Bold Fonts */
    h1, h2, h3, h4, h5, h6,
    .header-title,
    .prompt-bar-title,
    .kpi-value,
    .empty-state-title,
    .prompt-suggestion-title,
    .artifact-label,
    .tool-step-name,
    strong, b,
    [data-testid="stMarkdownContainer"] strong,
    [data-testid="stMarkdownContainer"] b,
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4 {
        font-family: var(--font-serif) !important;
        font-weight: 600 !important;
        letter-spacing: -0.015em !important;
    }

    /* Top Executive Header */
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        padding: 1.25rem 0 1rem 0;
        border-bottom: 1px solid var(--color-border);
        margin-bottom: 1.25rem;
    }
    .header-title {
        font-family: var(--font-serif) !important;
        font-size: 2.25rem !important;
        font-weight: 500 !important;
        letter-spacing: -0.025em !important;
        color: #0F172A !important;
        margin: 0;
        line-height: 1.2;
    }
    .header-subtitle {
        font-family: var(--font-sans);
        color: var(--color-text-muted);
        font-size: 0.9rem;
        margin-top: 0.35rem;
        font-weight: 400;
    }
    .system-status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: var(--color-primary-bg);
        border: 1px solid var(--color-primary-subtle);
        color: var(--color-primary);
        padding: 5px 12px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .status-indicator-dot {
        width: 6px;
        height: 6px;
        background-color: var(--color-primary-light);
        border-radius: 50%;
    }

    /* Live Currency Ticker Bar */
    .fx-ticker-container {
        background: #FFFFFF;
        border: 1px solid var(--color-border);
        border-radius: 8px;
        padding: 10px 16px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.02);
    }
    .fx-ticker-title {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--color-primary);
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .fx-ticker-rates {
        display: flex;
        gap: 16px;
        flex-wrap: wrap;
    }
    .fx-pill {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-family: 'JetBrains Mono', monospace;
        color: #334155;
    }
    .fx-pill strong {
        color: var(--color-primary);
    }

    /* Metric KPI Cards */
    .kpi-card {
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-radius: 8px;
        padding: 1rem 1.15rem;
        box-shadow: 0 1px 3px rgba(15, 23, 42, 0.03);
    }
    .kpi-label {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--color-text-muted);
        margin-bottom: 0.25rem;
    }
    .kpi-value {
        font-size: 1.45rem;
        font-weight: 700;
        color: var(--color-text-main);
        font-feature-settings: "tnum";
    }

    /* Tool Step Card */
    .tool-step-card {
        background: var(--color-surface);
        border: 1px solid var(--color-border);
        border-left: 3px solid var(--color-primary);
        border-radius: 8px;
        padding: 11px 14px;
        margin-bottom: 9px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.02);
    }
    .tool-step-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 5px;
    }
    .tool-step-name {
        font-size: 0.86rem;
        font-weight: 600;
        color: var(--color-text-main);
    }
    .tool-step-status {
        background-color: var(--color-primary-bg);
        border: 1px solid var(--color-primary-subtle);
        color: var(--color-primary);
        font-size: 0.68rem;
        font-weight: 700;
        padding: 2px 7px;
        border-radius: 4px;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .tool-step-human-desc {
        font-size: 0.80rem;
        color: #334155;
        line-height: 1.45;
    }
    .tool-step-desc {
        font-size: 0.78rem;
        color: var(--color-text-muted);
        margin-top: 3px;
        line-height: 1.4;
    }

    /* Incident Card */
    .incident-feed-card {
        background: #FFFFFF;
        border: 1px solid var(--color-border);
        border-left: 3px solid var(--color-primary);
        border-radius: 6px;
        padding: 12px 14px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.02);
    }
    .incident-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
        font-size: 0.78rem;
    }
    .incident-channel {
        font-weight: 600;
        color: var(--color-primary);
    }
    .incident-time {
        color: var(--color-text-subtle);
        font-size: 0.72rem;
    }
    .incident-body {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 4px;
        padding: 8px 10px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        line-height: 1.5;
        color: #1E293B;
        white-space: pre-wrap;
    }
    .incident-footer {
        margin-top: 6px;
        font-size: 0.72rem;
        color: var(--color-text-muted);
    }

    /* Empty State Cards */
    .empty-state-card {
        background: #FFFFFF;
        border: 1px dashed var(--color-border);
        border-radius: 8px;
        padding: 16px 14px;
        text-align: center;
        color: var(--color-text-muted);
        font-size: 0.82rem;
        line-height: 1.5;
        margin-bottom: 12px;
    }
    .empty-state-title {
        font-weight: 600;
        color: var(--color-text-main);
        margin-bottom: 4px;
        font-size: 0.85rem;
    }

    /* Artifact Container */
    .artifact-container {
        background: #FFFFFF;
        border: 1px solid var(--color-border);
        border-radius: 8px;
        overflow: hidden;
        margin-top: 1.5rem;
        box-shadow: 0 1px 4px rgba(15, 23, 42, 0.04);
    }
    .artifact-topbar {
        background: var(--color-primary-bg);
        border-bottom: 1px solid var(--color-primary-subtle);
        padding: 10px 16px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .artifact-label {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--color-primary);
    }

    /* Button Styling */
    .stButton > button[kind="primary"] {
        background-color: var(--color-primary) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 0.55rem 1.25rem !important;
        box-shadow: 0 1px 2px rgba(2, 132, 199, 0.2) !important;
        transition: background-color 0.15s ease !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #0369A1 !important;
    }

    /* Centered Copilot Hero & Prompt Bar */
    .copilot-hero-card {
        background: #FFFFFF;
        border: 1px solid var(--color-border);
        border-radius: 12px;
        padding: 1.25rem 1.5rem 1rem 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px -2px rgba(15, 23, 42, 0.04), 0 2px 6px -1px rgba(15, 23, 42, 0.02);
        position: relative;
    }
    .prompt-bar-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;
    }
    .prompt-bar-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: var(--color-text-main);
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .prompt-bar-badge {
        background: var(--color-primary-bg);
        border: 1px solid var(--color-primary-subtle);
        color: var(--color-primary);
        font-size: 0.72rem;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 6px;
    }
    .preset-chips-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--color-text-muted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.4rem;
    }

    /* Suggested Prompts Cards */
    .prompt-suggestion-box {
        background: #F8FAFC;
        border: 1px solid var(--color-border);
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 8px;
        transition: all 0.15s ease;
    }
    .prompt-suggestion-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 4px;
    }
    .prompt-suggestion-tag {
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 2px 6px;
        border-radius: 4px;
        background: var(--color-primary-bg);
        color: var(--color-primary);
        border: 1px solid var(--color-primary-subtle);
    }
    .prompt-suggestion-title {
        font-size: 0.82rem;
        font-weight: 600;
        color: var(--color-text-main);
    }
    .prompt-suggestion-desc {
        font-size: 0.76rem;
        color: var(--color-text-muted);
        line-height: 1.4;
        margin-top: 2px;
    }

    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid var(--color-border) !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Header Bar
st.markdown(
    """
    <div class="header-container">
        <div>
            <h1 class="header-title">Autonomous Data Analyst</h1>
            <div class="header-subtitle">Enterprise Protocol for Automated Financial Audits and Cohort Intelligence</div>
        </div>
        <div class="system-status-badge">
            <span class="status-indicator-dot"></span>
            Custom MCP Server Active | SSE (2024-11-05)
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Live Currency API Fetcher ---
@st.cache_data(ttl=60)
def fetch_live_market_rates():
    url = "https://api.frankfurter.dev/v1/latest?base=EUR&symbols=USD,GBP,INR,JPY,CHF,CAD,SGD,AUD"
    try:
        resp = httpx.get(url, timeout=5.0)
        data = resp.json()
        return {
            "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
            "rates": data.get("rates", {})
        }
    except Exception:
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "rates": {"USD": 1.1622, "GBP": 0.8540, "INR": 91.24, "JPY": 162.80, "CHF": 0.9450, "CAD": 1.5210, "SGD": 1.4820, "AUD": 1.6840}
        }

fx_data = fetch_live_market_rates()
rates = fx_data.get("rates", {})

# Render Live Currency Ticker
st.markdown(
    f"""
    <div class="fx-ticker-container">
        <div class="fx-ticker-title">
            <span class="status-indicator-dot"></span>
            Live FX Rates (Base: EUR | {fx_data.get('date')})
        </div>
        <div class="fx-ticker-rates">
            <div class="fx-pill">EUR/USD <strong>{rates.get('USD', 1.1622):.4f}</strong></div>
            <div class="fx-pill">EUR/GBP <strong>{rates.get('GBP', 0.8540):.4f}</strong></div>
            <div class="fx-pill">EUR/INR <strong>{rates.get('INR', 91.24):.2f}</strong></div>
            <div class="fx-pill">EUR/JPY <strong>{rates.get('JPY', 162.80):.2f}</strong></div>
            <div class="fx-pill">EUR/CHF <strong>{rates.get('CHF', 0.9450):.4f}</strong></div>
            <div class="fx-pill">EUR/CAD <strong>{rates.get('CAD', 1.5210):.4f}</strong></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Session state initialization
if "slack_messages" not in st.session_state:
    st.session_state.slack_messages = []
if "tool_logs" not in st.session_state:
    st.session_state.tool_logs = []
if "prompt_input" not in st.session_state:
    st.session_state.prompt_input = (
        "Perform a full autonomous audit of data/global_sales.csv: "
        "1) Preview the dataset structure, 2) Fetch live FX rates, "
        "3) Generate a segmentation cohort matrix by Country and Category, "
        "4) Detect anomalies and rule violations, 5) Dispatch a Slack alert summarizing findings, "
        "and 6) Export the audit summary report to disk."
    )
if "trigger_run" not in st.session_state:
    st.session_state.trigger_run = False

@st.cache_data(ttl=5)
def fetch_server_tools(server_url="http://127.0.0.1:8000/sse"):
    async def _get_tools():
        try:
            async with Client(server_url) as session:
                tools = await session.list_tools()
                return [
                    {
                        "name": t.name,
                        "description": (t.description or "No description provided").strip()
                    }
                    for t in tools
                ]
        except Exception:
            return []
    try:
        return asyncio.run(_get_tools())
    except Exception:
        return []

discovered_tools = fetch_server_tools()

def sanitize_schema(schema):
    if not isinstance(schema, dict):
        return schema
    cleaned = {}
    forbidden = {"additionalProperties", "additional_properties", "$schema"}
    for k, v in schema.items():
        if k in forbidden:
            continue
        if isinstance(v, dict):
            cleaned[k] = sanitize_schema(v)
        elif isinstance(v, list):
            cleaned[k] = [sanitize_schema(item) if isinstance(item, dict) else item for item in v]
        else:
            cleaned[k] = v
    return cleaned

import re

def send_message_safely(chat, message):
    retries = 0
    max_retries = 10
    while True:
        try:
            return chat.send_message(message)
        except Exception as e:
            err_str = str(e)
            retries += 1
            if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and retries <= max_retries:
                match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str) or re.search(r"retryDelay': '(\d+)s'", err_str)
                delay = int(float(match.group(1))) + 2 if match else 20
                with st.spinner(f"API Rate limit reached. Waiting {delay}s for quota window to reset (Attempt {retries}/{max_retries})..."):
                    time.sleep(delay)
            elif ("503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str.lower() or "overloaded" in err_str.lower() or "500" in err_str or "502" in err_str or "504" in err_str) and retries <= max_retries:
                backoff = min(2 ** retries + 2, 20)
                with st.spinner(f"Gemini API is experiencing temporary high demand (503). Retrying in {backoff}s (Attempt {retries}/{max_retries})..."):
                    time.sleep(backoff)
            elif ("Connection reset" in err_str or "ReadError" in err_str or "RemoteProtocolError" in err_str or "BrokenResourceError" in err_str) and retries <= max_retries:
                with st.spinner(f"Network interruption detected. Reconnecting ({retries}/{max_retries})..."):
                    time.sleep(3)
            else:
                raise e

def format_tool_activity(tool_name: str, args: dict) -> tuple[str, str]:
    if not isinstance(args, dict):
        args = {}
    
    if tool_name == "preview_dataset":
        filename = args.get("filename", "dataset")
        title = "Dataset Structure Inspection"
        desc = f"Inspecting column dimensions, data types, and completeness for '{filename}'."
    elif tool_name == "fetch_live_fx_rates":
        from_cur = args.get("from_currency", "USD")
        to_cur = args.get("to_currency", "EUR")
        title = "Live Currency FX Benchmark"
        desc = f"Retrieving real-time market exchange rate benchmark ({from_cur} to {to_cur}) via Frankfurter API."
    elif tool_name == "generate_segment_matrix":
        val_col = args.get("val_col", "Revenue")
        idx_col = args.get("index_col", "Country")
        col_col = args.get("column_col", "Category")
        title = "Cohort Segmentation Matrix"
        desc = f"Aggregating {val_col} in a 2D cross-tabulation grouped by {idx_col} and {col_col}."
    elif tool_name == "detect_anomalies":
        metric = args.get("metric_col", "Revenue")
        z_thresh = args.get("z_threshold", 2.0)
        filename = args.get("filename", "dataset")
        title = "Anomaly & Integrity Scan"
        desc = f"Scanning {filename} for negative {metric} violations and statistical outlier spikes (Z-score >= {z_thresh})."
    elif tool_name == "dispatch_slack_alert":
        title = "Real-time Incident Notification"
        desc = "Broadcasting structured executive compliance findings directly to Slack channel #all-mcp-analyst."
    elif tool_name == "export_audit_summary":
        report_title = args.get("title", "Executive Audit Report")
        clean_title = re.sub(r"[^\x00-\x7F]+", "", report_title).strip()
        title = "Executive Audit Report Generation"
        desc = f"Compiling structured audit report '{clean_title}' and generating formal PDF and Markdown files."
    else:
        title = tool_name.replace("_", " ").title()
        desc = "Executing tool on Custom MCP server."
    
    return title, desc

async def run_mcp_agent(prompt_text, status_placeholder, slack_placeholder, api_key_override=None, model_name="gemini-flash-latest"):
    api_key = api_key_override or os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("GEMINI_API_KEY is missing. Configure it in .env or the sidebar.")
        return None

    gemini_client = genai.Client(api_key=api_key)
    server_url = "http://127.0.0.1:8000/sse"

    async with Client(server_url) as session:
        tools_list = await session.list_tools()
        gemini_declarations = []
        for t in tools_list:
            raw_schema = t.input_schema if hasattr(t, "input_schema") else getattr(t, "inputSchema", {})
            gemini_declarations.append(
                types.FunctionDeclaration(
                    name=t.name,
                    description=t.description or "",
                    parameters=sanitize_schema(raw_schema)
                )
            )

        system_instruction = (
            "You are an autonomous enterprise data analyst copilot. "
            "When given an audit request, you must execute the complete end-to-end audit pipeline by calling all relevant tools in sequence:\n"
            "1. Call `preview_dataset` to inspect columns and dimensions.\n"
            "2. Call `fetch_live_fx_rates` for currency conversion rates.\n"
            "3. Call `generate_segment_matrix` to generate cohort aggregation data.\n"
            "4. Call `detect_anomalies` to identify business rule violations and statistical spikes.\n"
            "5. Call `dispatch_slack_alert` with a clean, concise, highly readable summary.\n"
            "6. Call `export_audit_summary` to save the full audit report to disk.\n"
            "Execute each tool call until all required steps are completed, then provide a final concise executive briefing.\n\n"
            "SLACK ALERT FORMATTING RULES:\n"
            "- When calling dispatch_slack_alert, format the message cleanly and simply as follows:\n"
            "  AUDIT SUMMARY: <dataset name>\n"
            "  Status: <Clean | Action Required>\n"
            "  Records Scanned: <number>\n\n"
            "  Key Findings:\n"
            "  - Anomalies: <list order violations concisely or 'None'>\n"
            "  - Top Market Segment: <Country> - <Category> (<Revenue>)\n"
            "  - Live FX Benchmark: <from/to rate>\n\n"
            "  Next Steps: Executive report exported to disk.\n"
            "- Keep spacing clean and easy for an executive to read in seconds.\n"
            "- CRITICAL: Do NOT use ANY emojis or emoji shortcodes (no :rotating_light:, no icons) anywhere in your tool calls, Slack messages, findings, or executive reports."
        )

        chat = gemini_client.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[types.Tool(function_declarations=gemini_declarations)]
            )
        )

        response = send_message_safely(chat, prompt_text)

        while response.function_calls:
            response_parts = []
            for call in response.function_calls:
                call_args = dict(call.args)
                st.session_state.tool_logs.append({"tool": call.name, "args": call_args})
                
                with status_placeholder.container():
                    for log in st.session_state.tool_logs:
                        title, desc = format_tool_activity(log['tool'], log.get('args', {}))
                        st.markdown(
                            f"""
                            <div class="tool-step-card">
                                <div class="tool-step-header">
                                    <span class="tool-step-name">{title}</span>
                                    <span class="tool-step-status">COMPLETED</span>
                                </div>
                                <div class="tool-step-human-desc">{desc}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                result = await session.call_tool(call.name, call_args)
                result_text = str(result.data if hasattr(result, "data") else result)

                if call.name == "dispatch_slack_alert":
                    raw_msg = call_args.get("message", "")
                    clean_msg = re.sub(r"[^\x00-\x7F]+", "", raw_msg).strip()
                    dispatch_time = datetime.now().strftime("%H:%M:%S")
                    st.toast("Alert dispatched to Slack #all-mcp-analyst")
                    st.session_state.slack_messages.append({
                        "text": clean_msg,
                        "time": dispatch_time,
                        "server_status": result_text
                    })
                    with slack_placeholder.container():
                        for entry in st.session_state.slack_messages:
                            st.markdown(
                                f"""
                                <div class="incident-feed-card">
                                    <div class="incident-meta">
                                        <span class="incident-channel">#all-mcp-analyst</span>
                                        <span class="incident-time">{entry['time']}</span>
                                    </div>
                                    <div class="incident-body">{entry['text']}</div>
                                    <div class="incident-footer">Status: {entry['server_status']}</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                response_parts.append(
                    types.Part.from_function_response(name=call.name, response={"result": result_text})
                )

            time.sleep(1)
            response = send_message_safely(chat, response_parts)

        # Strip any remaining emojis from the final output
        clean_final = re.sub(r"[^\x00-\x7F]+", "", response.text).strip()
        return clean_final

# --- Sidebar Configuration ---
st.sidebar.markdown("#### System Configuration")
env_key = os.getenv("GEMINI_API_KEY", "")
gemini_api_key = st.sidebar.text_input(
    "Gemini API Key",
    value=env_key,
    type="password",
    help="Loaded from .env or entered directly"
)
if gemini_api_key:
    os.environ["GEMINI_API_KEY"] = gemini_api_key
    st.sidebar.caption("API Key Active")
else:
    st.sidebar.warning("API Key not found. Set GEMINI_API_KEY in .env.")

model_choice = st.sidebar.selectbox(
    "Model Engine",
    options=["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.7-flash"],
    index=0
)

default_webhook = os.getenv("SLACK_WEBHOOK_URL", "")
slack_webhook = st.sidebar.text_input("Slack Webhook URL", value=default_webhook, placeholder="https://hooks.slack.com/services/...")
if slack_webhook:
    os.environ["SLACK_WEBHOOK_URL"] = slack_webhook

st.sidebar.markdown("---")
st.sidebar.markdown("#### Dataset Management")

# Scan all datasets in data directory
data_dir = Path("data")
data_dir.mkdir(exist_ok=True)
available_files = sorted([f.name for f in data_dir.glob("*.csv")])

if not available_files:
    available_files = ["global_sales.csv"]

selected_dataset = st.sidebar.selectbox(
    "Active Dataset",
    options=available_files,
    index=0,
    help="Select an enterprise dataset from data/ directory to inspect"
)

# Upload New Dataset Option
uploaded_file = st.sidebar.file_uploader("Upload New Dataset (CSV)", type=["csv"])
if uploaded_file is not None:
    upload_path = data_dir / uploaded_file.name
    upload_path.write_bytes(uploaded_file.getbuffer())
    st.sidebar.success(f"Uploaded `{uploaded_file.name}` to `data/`")
    if uploaded_file.name not in available_files:
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("#### MCP Server Status")
st.sidebar.code("http://127.0.0.1:8000/sse", language="text")

if discovered_tools:
    st.sidebar.success(f"Connected: {len(discovered_tools)} tools discovered")
    with st.sidebar.expander("View Server Tools", expanded=False):
        for tool in discovered_tools:
            st.markdown(f"**`{tool['name']}`**\n\n*{tool['description']}*")
else:
    st.sidebar.error("MCP Server Offline. Start via `python server/server.py`")

# --- Centered AI Copilot Prompt Studio (Main Feature Area) ---
st.markdown(
    f"""
    <div class="copilot-hero-card">
        <div class="prompt-bar-header">
            <div class="prompt-bar-title">
                <span>Autonomous Copilot Studio</span>
            </div>
            <span class="prompt-bar-badge">Engine: {model_choice} | Active: {selected_dataset}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Preset Prompt Chips
st.markdown('<div class="preset-chips-label">Quick Execution Presets</div>', unsafe_allow_html=True)
p_col1, p_col2, p_col3, p_col4 = st.columns(4)

with p_col1:
    if st.button("Full Pipeline Audit", use_container_width=True, help="Executes the complete 6-stage autonomous audit"):
        st.session_state.prompt_input = (
            f"Perform a full autonomous audit of data/{selected_dataset}: 1) Preview dataset structure, "
            f"2) Fetch live FX rates, 3) Generate a segmentation cohort matrix by Country and Category, "
            f"4) Detect anomalies and rule violations, 5) Dispatch a Slack alert summarizing findings, and 6) Export the audit summary report to disk."
        )
        st.session_state.trigger_run = True
        st.rerun()

with p_col2:
    if st.button("Outlier & Rule Scan", use_container_width=True, help="Scans for negative revenue and Z-score anomalies"):
        st.session_state.prompt_input = (
            f"Audit data/{selected_dataset} specifically for data integrity violations: scan for negative monetary amounts and statistical spikes with Z-score >= 2.0, alert Slack, and export findings."
        )
        st.session_state.trigger_run = True
        st.rerun()

with p_col3:
    if st.button("FX & Cohort Matrix", use_container_width=True, help="Fetches live exchange rates and computes pivot matrix"):
        st.session_state.prompt_input = (
            f"Inspect data/{selected_dataset}, fetch live currency exchange rates from the Frankfurter API, and compute the cross-tabulated revenue segmentation matrix across Country and Category."
        )
        st.session_state.trigger_run = True
        st.rerun()

with p_col4:
    if st.button("Slack Alert & Export", use_container_width=True, help="Summarizes dataset and exports formal PDF & Markdown"):
        st.session_state.prompt_input = (
            f"Perform an executive compliance check on data/{selected_dataset}, dispatch a summary alert to Slack #all-mcp-analyst, and export the formal audit report to disk."
        )
        st.session_state.trigger_run = True
        st.rerun()

# Centered Typing Bar & Action Buttons
user_query = st.text_area(
    "Prompt the Autonomous MCP Copilot:",
    value=st.session_state.prompt_input,
    height=95,
    help="Type any instruction in natural language. The agent will autonomously invoke MCP server tools to compute results."
)

btn_c1, btn_c2 = st.columns([4, 1])
with btn_c1:
    run_btn = st.button("Run Autonomous Copilot", type="primary", use_container_width=True)
with btn_c2:
    if st.button("Reset Prompt", use_container_width=True):
        st.session_state.prompt_input = (
            f"Perform a full autonomous audit of data/{selected_dataset}: 1) Preview the dataset structure, "
            f"2) Fetch live FX rates, 3) Generate a segmentation cohort matrix by Country and Category, "
            f"4) Detect anomalies and rule violations, 5) Dispatch a Slack alert summarizing findings, and 6) Export the audit summary report to disk."
        )
        st.session_state.trigger_run = False
        st.rerun()

# --- Suggested Prompts Library (Categorized & Interactive) ---
with st.expander("Explore Suggested Prompts Library", expanded=False):
    st.markdown("<div style='font-size: 0.82rem; color: #64748B; margin-bottom: 10px;'>Select any suggested enterprise audit prompt to load it into the copilot bar:</div>", unsafe_allow_html=True)
    
    suggested_prompts = [
        {
            "tag": "End-to-End Pipeline",
            "title": "Full Autonomous Lifecycle Audit",
            "desc": "Inspects dataset, fetches live FX rates, calculates cohort matrix, identifies statistical anomalies, alerts Slack, and compiles an executive report.",
            "prompt": f"Perform a full autonomous audit of data/{selected_dataset}: 1) Preview dataset structure, 2) Fetch live FX rates, 3) Generate a segmentation cohort matrix by Country and Category, 4) Detect anomalies and rule violations, 5) Dispatch a Slack alert summarizing findings, and 6) Export the audit summary report to disk."
        },
        {
            "tag": "Anomaly & Fraud",
            "title": "Negative Revenue & Outlier Spike Scan",
            "desc": "Scans for negative revenue rule violations and Z-score outlier orders (threshold >= 2.0), returning exact order IDs and severity levels.",
            "prompt": f"Audit data/{selected_dataset} specifically for data integrity violations: scan for negative monetary amounts and statistical spikes with Z-score >= 2.0, summarize anomalous Order IDs, and alert Slack."
        },
        {
            "tag": "Currency & Valuation",
            "title": "Live FX Multi-Currency Normalization",
            "desc": "Connects to Frankfurter API for real-time EUR, USD, GBP, and JPY rates, calculating foreign sales adjustments and converted revenue totals.",
            "prompt": f"Inspect data/{selected_dataset}, fetch live currency exchange rates from the Frankfurter API for EUR/USD and EUR/GBP, and compute normalized transaction values across international markets."
        },
        {
            "tag": "Cohort Segmentation",
            "title": "Country x Category Revenue Matrix",
            "desc": "Constructs a 2D cross-tabulation pivot matrix to discover top revenue drivers and underperforming market categories.",
            "prompt": f"Generate a cross-tabulated revenue segmentation cohort matrix for data/{selected_dataset} grouped by Country and Category, and report the top-performing business segment."
        },
        {
            "tag": "Real-time Alerting",
            "title": "Instant Slack Incident Broadcast",
            "desc": "Scans data and immediately dispatches a structured Slack webhook payload to #all-mcp-analyst with executive findings.",
            "prompt": f"Inspect data/{selected_dataset}, detect all rule violations and revenue anomalies, and immediately dispatch a formatted incident alert with high-risk order numbers to Slack #all-mcp-analyst."
        },
        {
            "tag": "Governance & PDF",
            "title": "Executive Compliance Audit & Certified PDF",
            "desc": "Evaluates transactional risk, drafts governance remediation steps, and writes both Markdown and formal PDF audit reports to disk.",
            "prompt": f"Perform an executive compliance check on data/{selected_dataset}, compile strategic risk remediation recommendations, and export both Markdown and certified executive PDF reports."
        }
    ]

    sp_col1, sp_col2 = st.columns(2)
    for idx, sp in enumerate(suggested_prompts):
        target_col = sp_col1 if idx % 2 == 0 else sp_col2
        with target_col:
            st.markdown(
                f"""
                <div class="prompt-suggestion-box">
                    <div class="prompt-suggestion-header">
                        <span class="prompt-suggestion-title">{sp['title']}</span>
                        <span class="prompt-suggestion-tag">{sp['tag']}</span>
                    </div>
                    <div class="prompt-suggestion-desc">{sp['desc']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            sc1, sc2 = st.columns([1, 1])
            with sc1:
                if st.button(f"Load Prompt", key=f"load_sp_{idx}", use_container_width=True):
                    st.session_state.prompt_input = sp["prompt"]
                    st.session_state.trigger_run = False
                    st.rerun()
            with sc2:
                if st.button(f"Run Now", key=f"run_sp_{idx}", type="primary", use_container_width=True):
                    st.session_state.prompt_input = sp["prompt"]
                    st.session_state.trigger_run = True
                    st.rerun()

# Conversational Chat Input Bar
chat_input_val = st.chat_input("Or type a custom prompt here and press Enter...")
if chat_input_val:
    user_query = chat_input_val
    st.session_state.prompt_input = chat_input_val
    run_btn = True

if st.session_state.trigger_run:
    st.session_state.trigger_run = False
    run_btn = True

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

# --- Main Analytics & Dashboard Layout ---
col_left, col_right = st.columns([1.25, 1], gap="large")

with col_left:
    st.markdown(f"#### Active Dataset: `{selected_dataset}`")
    csv_path = data_dir / selected_dataset
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        
        # Professional Metric Cards
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-label">Total Records</div>
                    <div class="kpi-value">{len(df):,}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with m2:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-label">Categories</div>
                    <div class="kpi-value">{df['Category'].nunique() if 'Category' in df.columns else 'N/A'}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with m3:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-label">Currencies Handled</div>
                    <div class="kpi-value" style="font-size: 1.05rem; padding-top: 4px;">{', '.join(df['Currency'].unique()) if 'Currency' in df.columns else 'N/A'}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # 1. Bar Chart (Anthropic Light Theme)
        if "Order_ID" in df.columns and "Revenue" in df.columns:
            fig_bar = px.bar(
                df,
                x="Order_ID",
                y="Revenue",
                color="Country" if "Country" in df.columns else None,
                color_discrete_sequence=["#0284C7", "#38BDF8", "#7DD3FC", "#0369A1", "#BAE6FD"],
                title="Recorded Revenue per Order ID (Negative Outlier Detection)",
                text="Revenue"
            )
            fig_bar.update_layout(
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#F8FAFC",
                font=dict(family="Inter", color="#334155", size=11),
                title_font=dict(family="Inter", size=13, color="#0F172A"),
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis=dict(gridcolor="#E2E8F0"),
                yaxis=dict(gridcolor="#E2E8F0")
            )
            fig_bar.add_hline(y=0, line_dash="dash", line_color="#DC2626", annotation_text="Break-even Threshold")
            st.plotly_chart(fig_bar, use_container_width=True)

        # 2. Cohort Matrix Heatmap
        if "Country" in df.columns and "Category" in df.columns and "Revenue" in df.columns:
            st.markdown("#### Segmentation Matrix (Country vs. Category Revenue)")
            pivot_df = pd.pivot_table(
                df, 
                index="Country", 
                columns="Category", 
                values="Revenue", 
                aggfunc="sum", 
                fill_value=0
            )
            fig_heat = px.imshow(
                pivot_df,
                labels=dict(x="Category", y="Country", color="Revenue"),
                text_auto=True,
                aspect="auto",
                color_continuous_scale=[
                    [0, "#F0F9FF"],
                    [0.25, "#BAE6FD"],
                    [0.5, "#38BDF8"],
                    [0.75, "#0284C7"],
                    [1, "#0369A1"]
                ],
                title="Revenue Aggregation Matrix"
            )
            fig_heat.update_layout(
                paper_bgcolor="#FFFFFF",
                plot_bgcolor="#FFFFFF",
                font=dict(family="Inter", color="#334155", size=11),
                title_font=dict(family="Inter", size=13, color="#0F172A"),
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_heat, use_container_width=True)

        with st.expander("Dataset Records Table", expanded=False):
            st.dataframe(df, use_container_width=True)
    else:
        st.warning(f"data/{selected_dataset} not found.")

with col_right:
    st.markdown("#### Real-time Incident Feed")
    slack_placeholder = st.empty()
    
    if st.session_state.slack_messages:
        with slack_placeholder.container():
            for entry in st.session_state.slack_messages:
                st.markdown(
                    f"""
                    <div class="incident-feed-card">
                        <div class="incident-meta">
                            <span class="incident-channel">#all-mcp-analyst</span>
                            <span class="incident-time">{entry['time']}</span>
                        </div>
                        <div class="incident-body">{entry['text']}</div>
                        <div class="incident-footer">Status: {entry['server_status']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        slack_placeholder.markdown(
            """
            <div class="empty-state-card">
                <div class="empty-state-title">No Incident Alerts Dispatched</div>
                Dispatched Slack alerts from the Custom MCP server will appear here during execution.
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("#### Custom MCP Tool Executions")
    status_placeholder = st.empty()

    if st.session_state.tool_logs:
        with status_placeholder.container():
            for log in st.session_state.tool_logs:
                title, desc = format_tool_activity(log['tool'], log.get('args', {}))
                st.markdown(
                    f"""
                    <div class="tool-step-card">
                        <div class="tool-step-header">
                            <span class="tool-step-name">{title}</span>
                            <span class="tool-step-status">COMPLETED</span>
                        </div>
                        <div class="tool-step-human-desc">{desc}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    elif discovered_tools:
        with status_placeholder.container():
            st.markdown(
                """
                <div style="background:#F0F9FF; border:1px solid #BAE6FD; border-radius:6px; padding:8px 12px; margin-bottom:10px; font-size:0.78rem; color:#0369A1;">
                    <strong>Custom MCP Server Connected:</strong> 6 tools discovered and ready for autonomous invocation. Click <strong>Execute Pipeline</strong> in the sidebar to run.
                </div>
                """,
                unsafe_allow_html=True
            )
            for tool in discovered_tools:
                st.markdown(
                    f"""
                    <div class="tool-step-card">
                        <div class="tool-step-header">
                            <span class="tool-step-name">{tool['name']}</span>
                            <span class="tool-step-status" style="background:#F1F5F9; border-color:#CBD5E1; color:#475569;">READY ON SERVER</span>
                        </div>
                        <div class="tool-step-desc">{tool['description']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        status_placeholder.markdown(
            """
            <div class="empty-state-card">
                <div class="empty-state-title">Awaiting Agent Tool Calls</div>
                Remote MCP tool invocations will stream here in real-time when the pipeline runs.
            </div>
            """,
            unsafe_allow_html=True
        )

if run_btn:
    st.session_state.slack_messages = []
    st.session_state.tool_logs = []
    slack_placeholder.empty()
    status_placeholder.empty()
    final_summary = None
    try:
        with st.spinner("Executing pipeline across MCP server..."):
            final_summary = asyncio.run(
                run_mcp_agent(
                    user_query,
                    status_placeholder,
                    slack_placeholder,
                    api_key_override=gemini_api_key,
                    model_name=model_choice
                )
            )
    except Exception as err:
        err_msg = str(err)
        if "503" in err_msg or "UNAVAILABLE" in err_msg or "high demand" in err_msg.lower():
            st.error(
                f"The model '{model_choice}' is currently experiencing high demand on Google servers. "
                "Recommendation: In the left sidebar, switch the 'Model Engine' to 'gemini-3.6-flash' or 'gemini-3.5-flash-lite' and click 'Run Autonomous Copilot' again."
            )
        else:
            st.error(f"Pipeline execution encountered an error: {err_msg}")

    if final_summary:
        st.markdown(
            f"""
            <div class="artifact-container">
                <div class="artifact-topbar">
                    <span class="artifact-label">Executive Briefing & Audit Findings</span>
                    <span style="font-size: 0.72rem; color: #0284C7; font-weight: 600;">COMPLETED</span>
                </div>
                <div class="artifact-content">
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(final_summary)

# --- Persistent Report Artifact & PDF Download Section ---
reports_dir = Path("outputs/reports")
if reports_dir.exists():
    all_reports = sorted(reports_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if all_reports:
        # Prefer report matching active dataset if available
        matching = [p for p in all_reports if Path(selected_dataset).stem in p.stem]
        report_file = matching[0] if matching else all_reports[0]
        report_text = report_file.read_text()
        
        # Generate formal executive PDF
        pdf_bytes = generate_formal_pdf(
            report_title=f"Autonomous Audit: {selected_dataset}",
            markdown_content=report_text,
            dataset_name=selected_dataset
        )

        st.markdown(
            f"""
            <div class="artifact-container" style="margin-top: 1.5rem;">
                <div class="artifact-topbar">
                    <span class="artifact-label">Generated Artifact: {report_file.name}</span>
                    <span style="font-size: 0.72rem; color: #0284C7; font-weight: 600;">OFFICIAL EXECUTIVE AUDIT</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Action bar with Formal PDF & Markdown Download buttons
        btn_col1, btn_col2 = st.columns([1, 1])
        with btn_col1:
            st.download_button(
                label="Download Formal Executive PDF",
                data=pdf_bytes,
                file_name=f"{report_file.stem}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                help="Download executive-ready, audit-certified PDF report with governance recommendations."
            )
        with btn_col2:
            st.download_button(
                label="Download Markdown (.md)",
                data=report_text,
                file_name=report_file.name,
                mime="text/markdown",
                use_container_width=True,
                help="Download raw Markdown audit report file."
            )

        with st.expander(f"View Report Content ({report_file.name})", expanded=True):
            st.markdown(report_text)
