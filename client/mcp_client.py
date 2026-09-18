"""
Custom Model Context Protocol (MCP) Client.
Implements the MCP Client Specification (2024-11-05) with zero third-party framework lock-in.
"""
from typing import Any, Dict, List, Optional
from client.transport.sse_client import SSEClientTransport


class ToolInfo:
    def __init__(self, name: str, description: str, input_schema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.inputSchema = input_schema  # alias for compatibility

    def __repr__(self):
        return f"ToolInfo(name='{self.name}', description='{self.description[:40]}...')"


class ToolCallResult:
    def __init__(self, raw_result: Dict[str, Any]):
        self.raw = raw_result
        self.content = raw_result.get("content", [])
        self.is_error = raw_result.get("isError", False)

    @property
    def data(self) -> str:
        """Returns the concatenated text content of the result."""
        if not self.content:
            return ""
        return "\n".join(
            item.get("text", "") if isinstance(item, dict) else getattr(item, "text", "")
            for item in self.content
        )

    def __str__(self):
        return self.data

    def __repr__(self):
        return f"ToolCallResult(is_error={self.is_error}, data='{self.data[:50]}...')"


class CustomMCPClient:
    """Standard Model Context Protocol client over SSE transport."""

    def __init__(self, server_url: str = "http://127.0.0.1:8000/sse", client_name: str = "CustomMCPClient", client_version: str = "1.0.0"):
        self.server_url = server_url
        self.client_name = client_name
        self.client_version = client_version
        self.transport = SSEClientTransport(sse_url=server_url)
        self.server_info: Dict[str, Any] = {}
        self.protocol_version: str = ""

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self):
        """Establishes connection and performs standard MCP initialization handshake."""
        await self.transport.connect()

        # Step 1: Send 'initialize' request
        init_response = await self.transport.send_request(
            method="initialize",
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": False}
                },
                "clientInfo": {
                    "name": self.client_name,
                    "version": self.client_version
                }
            }
        )

        self.server_info = init_response.get("serverInfo", {})
        self.protocol_version = init_response.get("protocolVersion", "2024-11-05")

        # Step 2: Send 'notifications/initialized' acknowledgement
        await self.transport.send_notification(method="notifications/initialized", params={})

    async def list_tools(self) -> List[ToolInfo]:
        """Discovers tools exposed by the MCP server."""
        resp = await self.transport.send_request(method="tools/list", params={})
        tools_data = resp.get("tools", [])
        return [
            ToolInfo(
                name=t.get("name"),
                description=t.get("description", ""),
                input_schema=t.get("inputSchema", {})
            )
            for t in tools_data
        ]

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> ToolCallResult:
        """Executes a tool on the remote MCP server."""
        resp = await self.transport.send_request(
            method="tools/call",
            params={
                "name": name,
                "arguments": arguments or {}
            }
        )
        return ToolCallResult(resp)

    async def list_resources(self) -> List[Dict[str, Any]]:
        """Lists resources exposed by the MCP server."""
        resp = await self.transport.send_request(method="resources/list", params={})
        return resp.get("resources", [])

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Reads a resource content from the MCP server."""
        resp = await self.transport.send_request(
            method="resources/read",
            params={"uri": uri}
        )
        return resp

    async def ping(self) -> bool:
        """Sends a ping request to verify server liveness."""
        try:
            await self.transport.send_request(method="ping", params={})
            return True
        except Exception:
            return False

    async def close(self):
        """Closes transport connection."""
        await self.transport.close()


if __name__ == "__main__":
    import asyncio
    import json

    async def main():
        print("\n" + "=" * 60)
        print("🔗 CUSTOM MCP CLIENT - STANDALONE RUNNER")
        print("=" * 60)
        server_url = "http://127.0.0.1:8000/sse"
        print(f"Connecting to Custom MCP Server at {server_url}...")
        try:
            async with CustomMCPClient(server_url) as client:
                print("Connected successfully!")
                print(f"Server Name:       {client.server_info.get('name')}")
                print(f"Protocol Version:  {client.protocol_version}")
                
                # Ping test
                ping_ok = await client.ping()
                print(f"Ping Status:       {'OK' if ping_ok else 'FAILED'}")
                
                # Discover tools
                tools = await client.list_tools()
                print(f"\nDiscovered {len(tools)} Custom MCP Tools:")
                for t in tools:
                    print(f"  • {t.name}: {t.description}")
                
                # Test calling a tool
                print("\n" + "-" * 60)
                print("Executing Custom MCP Tool: preview_dataset('global_sales.csv')...")
                res = await client.call_tool("preview_dataset", {"filename": "global_sales.csv"})
                print(f"Result (is_error={res.is_error}):")
                try:
                    parsed = json.loads(res.data)
                    print(json.dumps(parsed, indent=2))
                except Exception:
                    print(res.data)
                print("=" * 60 + "\n")
        except Exception as e:
            print(f"\nCould not connect to {server_url}: {e}")
            print("Tip: Make sure the Custom MCP Server is running with: python server/server.py")
            print("Or run the automated integration test: python -m unittest tests/test_custom_mcp_network.py\n")

    asyncio.run(main())
