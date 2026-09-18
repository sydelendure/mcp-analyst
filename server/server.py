"""
Autonomous Data Analyst MCP Server.
Built from scratch using custom MCP JSON-RPC 2.0 protocol and HTTP/SSE transport.
"""
import sys
from pathlib import Path
import uvicorn

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.protocol.registry import ToolRegistry, ResourceRegistry, MCPDispatcher
from server.transport.sse_server import create_mcp_app
from server.tools.analyst_tools import (
    list_available_datasets,
    preview_dataset,
    fetch_live_fx_rates,
    detect_anomalies,
    generate_segment_matrix,
    dispatch_slack_alert,
    export_audit_summary,
    resolve_dataset_path,
)

# Initialize registries
tool_registry = ToolRegistry()
resource_registry = ResourceRegistry()

# Register Resources
resource_registry.register(
    uri="data://available-datasets",
    fn=list_available_datasets,
    name="available_datasets",
    description="Lists all CSV files in the data directory.",
    mime_type="application/json"
)

# Register Tools
tool_registry.register(
    fn=preview_dataset,
    name="preview_dataset",
    description="Inspects dataset dimensions, columns, and missing values."
)

tool_registry.register(
    fn=fetch_live_fx_rates,
    name="fetch_live_fx_rates",
    description="Calls Frankfurter API to fetch live currency exchange rates."
)

tool_registry.register(
    fn=detect_anomalies,
    name="detect_anomalies",
    description="Scans for negative revenue violations and Z-score outlier spikes."
)

tool_registry.register(
    fn=generate_segment_matrix,
    name="generate_segment_matrix",
    description="Computes a cross-tabulated segmentation matrix (Cohort/Pivot) of aggregated metrics across two dimensions."
)

tool_registry.register(
    fn=dispatch_slack_alert,
    name="dispatch_slack_alert",
    description="Dispatches a structured, plain-text alert payload to the configured Slack webhook channel."
)

tool_registry.register(
    fn=export_audit_summary,
    name="export_audit_summary",
    description="Exports structured audit findings into a Markdown file and formal executive PDF on disk."
)

# Initialize Dispatcher and ASGI App
dispatcher = MCPDispatcher(
    server_name="Autonomous-Data-Analyst-Copilot",
    server_version="1.0.0",
    tool_registry=tool_registry,
    resource_registry=resource_registry,
)

app = create_mcp_app(dispatcher)

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 CUSTOM MODEL CONTEXT PROTOCOL (MCP) SERVER")
    print("=" * 60)
    print("Protocol Version: 2024-11-05 (JSON-RPC 2.0)")
    print("Transport:        HTTP / Server-Sent Events (SSE)")
    print("Listening on:     http://127.0.0.1:8000")
    print("SSE Stream:       http://127.0.0.1:8000/sse")
    print("Messages:         http://127.0.0.1:8000/messages?sessionId=...")
    print(f"Registered Tools: {len(tool_registry.list_tools())}")
    for t in tool_registry.list_tools():
        print(f"  • {t.name}: {t.description}")
    print("=" * 60 + "\n")
    
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
