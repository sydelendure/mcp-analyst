"""
Custom Starlette ASGI SSE Transport for MCP Server.
Implements the standard MCP HTTP/SSE transport (Specification 2024-11-05).
"""
import asyncio
import json
import logging
import uuid
from typing import Dict, Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from sse_starlette.sse import EventSourceResponse

from ..protocol.jsonrpc import (
    INTERNAL_ERROR,
    INVALID_REQUEST,
    PARSE_ERROR,
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
)
from ..protocol.registry import MCPDispatcher

logger = logging.getLogger("mcp_server.sse")


class MCPServerSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.queue: asyncio.Queue = asyncio.Queue()
        self.is_active = True

    async def send_message(self, message: dict):
        if self.is_active:
            await self.queue.put(message)

    def close(self):
        self.is_active = False


class SSEServerTransport:
    """Manages active SSE client sessions and message routing."""

    def __init__(self, dispatcher: MCPDispatcher):
        self.dispatcher = dispatcher
        self.sessions: Dict[str, MCPServerSession] = {}

    def get_session(self, session_id: str) -> Optional[MCPServerSession]:
        return self.sessions.get(session_id)

    def create_session(self) -> MCPServerSession:
        session_id = uuid.uuid4().hex
        session = MCPServerSession(session_id)
        self.sessions[session_id] = session
        return session

    def remove_session(self, session_id: str):
        if session_id in self.sessions:
            self.sessions[session_id].close()
            del self.sessions[session_id]

    async def handle_sse(self, request: Request):
        session = self.create_session()
        logger.info(f"New SSE connection established: session_id={session.session_id}")

        async def event_generator():
            try:
                # 1. Send the endpoint event containing the message target URL
                endpoint_url = f"/messages?sessionId={session.session_id}"
                yield {
                    "event": "endpoint",
                    "data": endpoint_url
                }

                # 2. Stream any outgoing JSON-RPC responses
                while session.is_active:
                    try:
                        # Wait for message with periodic ping check
                        msg = await asyncio.wait_for(session.queue.get(), timeout=15.0)
                        session.queue.task_done()
                        yield {
                            "event": "message",
                            "data": json.dumps(msg)
                        }
                    except asyncio.TimeoutError:
                        # Yield SSE comment / keep-alive to keep connection open
                        yield {"comment": "ping"}
                    except asyncio.CancelledError:
                        break
            finally:
                logger.info(f"SSE connection closed: session_id={session.session_id}")
                self.remove_session(session.session_id)

        return EventSourceResponse(event_generator())

    async def handle_messages(self, request: Request):
        session_id = request.query_params.get("sessionId")
        if not session_id or session_id not in self.sessions:
            return JSONResponse(
                {"error": f"Invalid or missing sessionId: '{session_id}'"},
                status_code=400
            )

        session = self.sessions[session_id]

        try:
            body = await request.json()
        except Exception as e:
            err_resp = JSONRPCResponse(
                error=JSONRPCError(code=PARSE_ERROR, message="Invalid JSON payload", data=str(e))
            )
            await session.send_message(err_resp.model_dump(exclude_none=True))
            return Response(status_code=400)

        # Parse request as JSONRPCRequest
        try:
            jsonrpc_req = JSONRPCRequest(**body)
        except Exception as e:
            err_resp = JSONRPCResponse(
                id=body.get("id") if isinstance(body, dict) else None,
                error=JSONRPCError(code=INVALID_REQUEST, message="Invalid JSON-RPC 2.0 request structure", data=str(e))
            )
            await session.send_message(err_resp.model_dump(exclude_none=True))
            return Response(status_code=400)

        # Dispatch request through MCP Protocol
        jsonrpc_resp = await self.dispatcher.dispatch(jsonrpc_req)

        # If response exists (not a notification), send it over the SSE stream
        if jsonrpc_resp is not None:
            await session.send_message(jsonrpc_resp.model_dump(exclude_none=True))

        return JSONResponse({"status": "accepted"}, status_code=202)


def create_mcp_app(dispatcher: MCPDispatcher) -> Starlette:
    """Creates a Starlette ASGI application with standard MCP routes."""
    transport = SSEServerTransport(dispatcher)

    routes = [
        Route("/sse", endpoint=transport.handle_sse, methods=["GET"]),
        Route("/messages", endpoint=transport.handle_messages, methods=["POST"]),
    ]

    app = Starlette(debug=True, routes=routes)
    return app
