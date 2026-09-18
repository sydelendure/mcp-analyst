"""
Integration tests for Custom MCP Server and Client over real network SSE transport.
"""
import asyncio
import os
import sys
import threading
import time
import unittest
from pathlib import Path
import uvicorn

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.server import app
from client.mcp_client import CustomMCPClient


class ServerThread(threading.Thread):
    def __init__(self, app, port=8001):
        super().__init__(daemon=True)
        self.port = port
        self.config = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="error")
        self.server = uvicorn.Server(self.config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


class TestCustomMCPNetwork(unittest.IsolatedAsyncioTestCase):
    """Starts Custom MCP Server in background thread and tests CustomMCPClient over SSE."""

    @classmethod
    def setUpClass(cls):
        cls.server_thread = ServerThread(app, port=8001)
        cls.server_thread.start()
        time.sleep(0.5)  # Wait for server to bind

    @classmethod
    def tearDownClass(cls):
        cls.server_thread.stop()

    async def test_01_handshake_and_tool_discovery(self):
        server_url = "http://127.0.0.1:8001/sse"
        async with CustomMCPClient(server_url) as client:
            # Verify protocol version and server info
            self.assertEqual(client.protocol_version, "2024-11-05")
            self.assertEqual(client.server_info.get("name"), "Autonomous-Data-Analyst-Copilot")
            
            # Verify ping
            ping_ok = await client.ping()
            self.assertTrue(ping_ok)

            # Discover tools
            tools = await client.list_tools()
            self.assertEqual(len(tools), 6)
            tool_names = [t.name for t in tools]
            expected = [
                "preview_dataset",
                "fetch_live_fx_rates",
                "detect_anomalies",
                "generate_segment_matrix",
                "dispatch_slack_alert",
                "export_audit_summary"
            ]
            for exp in expected:
                self.assertIn(exp, tool_names)
            print("\nPASS: Handshake, ping, and tool discovery over custom SSE transport succeeded.")

    async def test_02_remote_tool_execution(self):
        server_url = "http://127.0.0.1:8001/sse"
        async with CustomMCPClient(server_url) as client:
            # 1. preview_dataset
            res_prev = await client.call_tool("preview_dataset", {"filename": "global_sales.csv"})
            self.assertFalse(res_prev.is_error)
            self.assertIn("total_rows", res_prev.data)

            # 2. fetch_live_fx_rates
            res_fx = await client.call_tool("fetch_live_fx_rates", {"from_currency": "EUR", "to_currency": "USD"})
            self.assertFalse(res_fx.is_error)
            self.assertIn("rate", res_fx.data)

            # 3. detect_anomalies
            res_anom = await client.call_tool("detect_anomalies", {"filename": "global_sales.csv"})
            self.assertFalse(res_anom.is_error)
            self.assertIn("BUSINESS_RULE_VIOLATION", res_anom.data)

            # 4. generate_segment_matrix
            res_seg = await client.call_tool("generate_segment_matrix", {"filename": "global_sales.csv"})
            self.assertFalse(res_seg.is_error)
            self.assertIn("top_performing_segment", res_seg.data)

            # 5. export_audit_summary
            res_exp = await client.call_tool(
                "export_audit_summary",
                {"title": "E2E Test Report", "findings": ["Finding 1", "Finding 2"], "output_filename": "e2e_test_report.md"}
            )
            self.assertFalse(res_exp.is_error)
            self.assertIn("Report successfully written", res_exp.data)

            print("PASS: Remote execution of all 5 core analytical tools over custom MCP network passed.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
