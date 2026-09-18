"""
Custom HTTP / SSE Transport for MCP Client.
Connects to MCP SSE server, parses SSE events, and handles JSON-RPC request-response matching.
"""
import asyncio
import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import urljoin
import httpx

logger = logging.getLogger("mcp_client.sse")


class SSEClientTransport:
    """Manages SSE downstream connection and HTTP POST upstream requests."""

    def __init__(self, sse_url: str = "http://127.0.0.1:8000/sse", timeout: float = 30.0):
        self.sse_url = sse_url
        self.timeout = timeout
        self.message_url: Optional[str] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.pending_requests: Dict[Any, asyncio.Future] = {}
        self._next_id = 1
        self._connected_event = asyncio.Event()
        self._connect_error: Optional[Exception] = None
        self._read_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def connect(self):
        """Establishes connection to the SSE stream and discovers message endpoint."""
        self.http_client = httpx.AsyncClient(timeout=self.timeout)
        self._is_running = True
        self._connect_error = None
        self._read_task = asyncio.create_task(self._listen_sse())

        # Wait until the endpoint event is received or connection fails
        try:
            await asyncio.wait_for(self._connected_event.wait(), timeout=10.0)
            if self._connect_error is not None:
                await self.close()
                raise ConnectionError(
                    f"Failed to connect to Custom MCP Server at {self.sse_url}: {self._connect_error}\n"
                    f"👉 Please make sure the Custom MCP Server is running in a separate terminal: python server/server.py"
                )
        except asyncio.TimeoutError:
            await self.close()
            raise ConnectionError(
                f"Timed out waiting for SSE endpoint initialization from {self.sse_url}.\n"
                f"👉 Please make sure the Custom MCP Server is running in a separate terminal: python server/server.py"
            )

    async def _listen_sse(self):
        """Background task that parses SSE stream."""
        try:
            async with self.http_client.stream("GET", self.sse_url, headers={"Accept": "text/event-stream"}) as response:
                if response.status_code != 200:
                    raise ConnectionError(f"SSE connection failed with status code {response.status_code}")

                current_event = "message"
                current_data = []

                async for line in response.aiter_lines():
                    if not self._is_running:
                        break

                    line = line.strip()
                    if not line:
                        # Empty line signals dispatch of the accumulated event
                        if current_data:
                            data_str = "\n".join(current_data)
                            await self._handle_event(current_event, data_str)
                            current_data = []
                            current_event = "message"
                        continue

                    if line.startswith("event:"):
                        current_event = line[len("event:"):].strip()
                    elif line.startswith("data:"):
                        current_data.append(line[len("data:"):].strip())
                    elif line.startswith(":"):
                        # Comment / keep-alive ping
                        continue

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in SSE reader stream: {str(e)}")
            self._connect_error = e
            self._connected_event.set()
            # Fail all pending futures
            for fut in self.pending_requests.values():
                if not fut.done():
                    fut.set_exception(ConnectionError(f"SSE connection lost: {str(e)}"))

    async def _handle_event(self, event_type: str, data: str):
        if event_type == "endpoint":
            # Server announced the upstream message endpoint
            endpoint = data.strip()
            self.message_url = urljoin(self.sse_url, endpoint)
            logger.info(f"Discovered MCP message endpoint: {self.message_url}")
            self._connected_event.set()

        elif event_type == "message":
            try:
                msg = json.loads(data)
                req_id = msg.get("id")
                if req_id is not None and req_id in self.pending_requests:
                    fut = self.pending_requests.pop(req_id)
                    if not fut.done():
                        fut.set_result(msg)
            except Exception as e:
                logger.error(f"Failed to parse SSE message payload: {str(e)}")

    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Sends a JSON-RPC request and awaits the matching response."""
        if not self.message_url or not self.http_client:
            raise RuntimeError("Client is not connected to MCP Server.")

        req_id = self._next_id
        self._next_id += 1

        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self.pending_requests[req_id] = fut

        try:
            resp = await self.http_client.post(self.message_url, json=payload)
            if resp.status_code not in (200, 202):
                self.pending_requests.pop(req_id, None)
                raise RuntimeError(f"Server rejected message with HTTP {resp.status_code}: {resp.text}")

            result_msg = await asyncio.wait_for(fut, timeout=self.timeout)

            if "error" in result_msg and result_msg["error"]:
                err = result_msg["error"]
                raise RuntimeError(f"MCP JSON-RPC Error {err.get('code')}: {err.get('message')}")

            return result_msg.get("result", {})

        except Exception:
            self.pending_requests.pop(req_id, None)
            raise

    async def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Sends a JSON-RPC notification (no response expected)."""
        if not self.message_url or not self.http_client:
            raise RuntimeError("Client is not connected to MCP Server.")

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        await self.http_client.post(self.message_url, json=payload)

    async def close(self):
        self._is_running = False
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()
        if self.http_client:
            await self.http_client.aclose()
