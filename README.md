# Autonomous Data Analyst Copilot (Custom MCP Architecture)

An enterprise business intelligence and data auditing platform built entirely from scratch with a **Custom Model Context Protocol (MCP)** implementation conforming to **Specification `2024-11-05`** over **JSON-RPC 2.0** and **HTTP / Server-Sent Events (SSE)**.

---

## 🏗️ Architecture Overview

The system is decoupled into two independent, networked processes:

```text
                    USER / ANALYST
                          │
                          ▼
               ┌──────────────────────┐
               │    AI ORCHESTRATOR   │
               │ Google Gemini Agent  │
               └──────────┬───────────┘
                          │
                          ▼
               ┌──────────────────────┐
               │  CUSTOM MCP CLIENT   │
               │  - Tool Discovery    │
               │  - JSON-RPC Client   │
               │  - SSE Transport     │
               └──────────┬───────────┘
                          │
                 MCP Protocol Wire
                  (JSON-RPC 2.0)
                 HTTP / SSE Stream
                          │
                          ▼
        ┌──────────────────────────────────┐
        │        CUSTOM MCP SERVER         │
        │                                  │
        │  • Starlette ASGI SSE Router     │
        │  • MCP Dispatcher (2024-11-05)   │
        │  • Tool & Resource Registries    │
        │  • Python Type Reflection Engine │
        └─────────────────┬────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
   Dataset Storage   Frankfurter FX   Slack Webhook /
    (CSV Files)        Live API       PDF Audit Engine
```

---

## 📁 Repository Structure

```text
mcp-analyst/
├── server/
│   ├── protocol/
│   │   ├── jsonrpc.py          # JSON-RPC 2.0 models (Requests, Responses, Errors, Notifications)
│   │   ├── types.py            # MCP schema definitions (Initialize, ToolDefinition, CallToolResult)
│   │   └── registry.py         # ToolRegistry & ResourceRegistry with automatic schema reflection
│   ├── transport/
│   │   └── sse_server.py       # Starlette ASGI SSE (GET /sse) & HTTP POST (POST /messages)
│   ├── tools/
│   │   └── analyst_tools.py    # Business analytical tools & dataset resources
│   └── server.py               # Standalone MCP Server entry point (Terminal 1)
│
├── client/
│   ├── transport/
│   │   └── sse_client.py       # Custom async SSE listener & JSON-RPC request dispatcher
│   ├── mcp_client.py           # High-level CustomMCPClient interface (handshake, list_tools, call_tool)
│   └── client_runner.py        # Gemini Autonomous Copilot agent (Terminal 2)
│
├── data/                       # CSV financial and retail datasets
├── outputs/reports/            # Generated Markdown & Executive PDF audit reports
├── tests/
│   ├── test_full_suite.py      # Core unit, reflection, and protocol tests
│   └── test_custom_mcp_network.py # End-to-end SSE network integration tests
│
└── app.py                      # Executive Streamlit Dashboard powered by CustomMCPClient
```

---

## 🚀 Running the Project

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root folder:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
SLACK_WEBHOOK_URL=your_slack_webhook_url_here
```

### 3. Run Automated Tests
```bash
python -m unittest discover -s tests
```

### 4. Start the Standalone Custom MCP Server (Terminal 1)
```bash
python server/server.py
```
*The server will start listening on `http://127.0.0.1:8000` with SSE stream at `http://127.0.0.1:8000/sse`.*

### 5. Run the Autonomous AI Client (Terminal 2)
```bash
python client/client_runner.py
```

### 6. Launch the Executive Web Dashboard (Optional)
```bash
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.