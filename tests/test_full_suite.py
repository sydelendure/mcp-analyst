import asyncio
import os
import sys
import unittest
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add root directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.protocol.jsonrpc import (
    JSONRPCRequest,
    JSONRPCResponse,
    JSONRPCError,
    METHOD_NOT_FOUND,
)
from server.protocol.registry import (
    ToolRegistry,
    ResourceRegistry,
    MCPDispatcher,
    extract_function_schema,
)
from server.tools.analyst_tools import (
    list_available_datasets,
    preview_dataset,
    fetch_live_fx_rates,
    detect_anomalies,
    generate_segment_matrix,
    export_audit_summary,
    resolve_dataset_path,
)
from client.client_runner import sanitize_schema
from client.mcp_client import CustomMCPClient
from utils.pdf_generator import generate_formal_pdf


class TestServerCoreTools(unittest.TestCase):
    """Test suite for business analyst tools directly (Unit Tests)."""

    def test_01_list_datasets(self):
        datasets = list_available_datasets()
        self.assertIsInstance(datasets, list)
        self.assertIn("global_sales.csv", datasets)
        self.assertIn("apac_retail_q3.csv", datasets)
        print("PASS: list_available_datasets correctly discovered all CSVs.")

    def test_02_resolve_dataset_path(self):
        # Test with bare filename
        p1 = resolve_dataset_path("global_sales.csv")
        self.assertTrue(p1.exists())
        
        # Test with data/ prefix
        p2 = resolve_dataset_path("data/global_sales.csv")
        self.assertTrue(p2.exists())
        
        # Test non-existent file
        p3 = resolve_dataset_path("non_existent_file.csv")
        self.assertFalse(p3.exists())
        print("PASS: resolve_dataset_path correctly resolved paths with and without data/ prefix.")

    def test_03_preview_dataset_all_files(self):
        datasets = list_available_datasets()
        for ds in datasets:
            res = preview_dataset(ds)
            self.assertNotIn("error", res, f"Failed previewing {ds}: {res.get('error')}")
            self.assertIn("total_rows", res)
            self.assertIn("columns", res)
            self.assertIn("missing_values", res)
            self.assertIn("sample", res)
            self.assertGreater(res["total_rows"], 0)
        print(f"PASS: preview_dataset successfully previewed all {len(datasets)} datasets.")

    def test_04_fetch_live_fx_rates(self):
        # Same currency test
        res_same = fetch_live_fx_rates("USD", "USD")
        self.assertEqual(res_same["rate"], 1.0)
        
        # Real API test
        res_eur_usd = fetch_live_fx_rates("EUR", "USD")
        self.assertIn("rate", res_eur_usd)
        self.assertIsInstance(res_eur_usd["rate"], (int, float))
        self.assertGreater(res_eur_usd["rate"], 0)
        print(f"PASS: fetch_live_fx_rates returned live EUR/USD rate: {res_eur_usd['rate']}.")

    def test_05_detect_anomalies_global_sales(self):
        res = detect_anomalies("global_sales.csv", metric_col="Revenue", z_threshold=2.0)
        self.assertNotIn("error", res)
        self.assertIn("anomalies", res)
        self.assertGreaterEqual(res["anomaly_count"], 1)
        
        # Verify negative revenue violation is caught
        types_found = [a["type"] for a in res["anomalies"]]
        self.assertIn("BUSINESS_RULE_VIOLATION", types_found)
        print(f"PASS: detect_anomalies caught {res['anomaly_count']} anomalies including rule violations.")

    def test_06_generate_segment_matrix(self):
        res = generate_segment_matrix("global_sales.csv", index_col="Country", column_col="Category", val_col="Revenue")
        self.assertNotIn("error", res)
        self.assertIn("pivot_data", res)
        self.assertIn("top_performing_segment", res)
        self.assertGreater(len(res["pivot_data"]), 0)
        print("PASS: generate_segment_matrix calculated cross-tabulation matrix successfully.")

    def test_07_export_audit_summary(self):
        test_findings = [
            "Anomaly Detection: Negative revenue of -450.0 detected in DE.",
            "FX Check: EUR/USD rate is active.",
            "Segmentation: Consumer electronics drove top revenue."
        ]
        res = export_audit_summary("Vigorous Test Audit", test_findings, "test_vigorous_audit.md")
        self.assertIn("Report successfully written", res)
        
        md_file = Path("outputs/reports/test_vigorous_audit.md")
        pdf_file = Path("outputs/reports/test_vigorous_audit.pdf")
        self.assertTrue(md_file.exists())
        self.assertTrue(pdf_file.exists())
        self.assertGreater(pdf_file.stat().st_size, 500)
        print("PASS: export_audit_summary wrote both .md and .pdf reports to disk.")


class TestProtocolAndRegistry(unittest.IsolatedAsyncioTestCase):
    """Test suite for custom JSON-RPC protocol models and function schema reflection."""

    def test_08_function_schema_reflection(self):
        def sample_tool(filename: str = "global_sales.csv", limit: int = 10, threshold: float = 2.5) -> dict:
            """Sample docstring."""
            return {}

        schema = extract_function_schema(sample_tool)
        self.assertEqual(schema["type"], "object")
        self.assertIn("filename", schema["properties"])
        self.assertEqual(schema["properties"]["filename"]["type"], "string")
        self.assertEqual(schema["properties"]["filename"]["default"], "global_sales.csv")
        self.assertEqual(schema["properties"]["limit"]["type"], "integer")
        self.assertEqual(schema["properties"]["threshold"]["type"], "number")
        print("PASS: extract_function_schema accurately reflected Python types into JSON Schema Draft 7.")

    async def test_09_dispatcher_tools_and_resources(self):
        reg = ToolRegistry()
        reg.register(fetch_live_fx_rates, name="fetch_live_fx_rates")
        
        dispatcher = MCPDispatcher(server_name="TestServer", tool_registry=reg)
        
        # Test initialize
        init_req = JSONRPCRequest(id=1, method="initialize", params={"protocolVersion": "2024-11-05"})
        init_resp = await dispatcher.dispatch(init_req)
        self.assertEqual(init_resp.id, 1)
        self.assertEqual(init_resp.result["protocolVersion"], "2024-11-05")
        
        # Test tools/list
        list_req = JSONRPCRequest(id=2, method="tools/list")
        list_resp = await dispatcher.dispatch(list_req)
        self.assertEqual(len(list_resp.result["tools"]), 1)
        self.assertEqual(list_resp.result["tools"][0]["name"], "fetch_live_fx_rates")
        
        # Test tools/call
        call_req = JSONRPCRequest(id=3, method="tools/call", params={"name": "fetch_live_fx_rates", "arguments": {"from_currency": "USD", "to_currency": "USD"}})
        call_resp = await dispatcher.dispatch(call_req)
        self.assertFalse(call_resp.result["isError"])
        self.assertIn("1.0", call_resp.result["content"][0]["text"])
        
        # Test unknown method
        bad_req = JSONRPCRequest(id=4, method="unknown_method")
        bad_resp = await dispatcher.dispatch(bad_req)
        self.assertEqual(bad_resp.error.code, METHOD_NOT_FOUND)
        print("PASS: MCPDispatcher correctly handled initialize, tools/list, tools/call and errors.")


class TestPDFGenerator(unittest.TestCase):
    """Test suite for PDF compilation engine."""

    def test_10_pdf_generation(self):
        markdown_sample = """# Executive Audit Report

## Observations
- Observation 1: Anomaly detected with Order ORD-999.
- Observation 2: Live currency parity verified.
"""
        pdf_bytes = generate_formal_pdf(
            report_title="Automated Test Report",
            markdown_content=markdown_sample,
            dataset_name="apac_retail_q3.csv"
        )
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"), "Output bytes do not have valid PDF magic number header")
        self.assertGreater(len(pdf_bytes), 1000)
        print(f"PASS: PDF Generator generated valid PDF ({len(pdf_bytes)} bytes).")


class TestSchemaSanitizer(unittest.TestCase):
    """Test suite for Gemini function declaration schema sanitization."""

    def test_11_schema_sanitization(self):
        raw_schema = {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "limit": {"type": "integer"}
            },
            "additionalProperties": False,
            "$schema": "http://json-schema.org/draft-07/schema#"
        }
        cleaned = sanitize_schema(raw_schema)
        self.assertNotIn("additionalProperties", cleaned)
        self.assertNotIn("$schema", cleaned)
        self.assertIn("filename", cleaned["properties"])
        print("PASS: sanitize_schema stripped forbidden Gemini OpenAPI properties.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
