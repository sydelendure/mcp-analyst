"""
Tool & Resource Registries and MCP JSON-RPC Dispatcher.
Performs reflection on Python functions to generate JSON Schema definitions.
"""
import inspect
import json
import traceback
from typing import Any, Callable, Dict, List, Optional, Union, get_args, get_origin
from pydantic import BaseModel

from .jsonrpc import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
)
from .types import (
    LATEST_PROTOCOL_VERSION,
    CallToolResult,
    Implementation,
    InitializeResult,
    ReadResourceResult,
    ResourceContent,
    ResourceDefinition,
    ServerCapabilities,
    TextContent,
    ToolDefinition,
    ToolsCapability,
    ResourcesCapability,
)


def python_type_to_json_type(py_type: Any) -> Dict[str, Any]:
    """Converts a Python type annotation to JSON Schema property spec."""
    origin = get_origin(py_type)
    args = get_args(py_type)

    # Handle Union / Optional (e.g., Optional[str] or Union[str, None])
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return python_type_to_json_type(non_none[0])
        return {"anyOf": [python_type_to_json_type(a) for a in non_none]}

    if py_type in (str, Optional[str]):
        return {"type": "string"}
    elif py_type in (int, Optional[int]):
        return {"type": "integer"}
    elif py_type in (float, Optional[float]):
        return {"type": "number"}
    elif py_type in (bool, Optional[bool]):
        return {"type": "boolean"}
    elif py_type in (list, List) or origin in (list, List):
        item_type = args[0] if args else Any
        if item_type is not Any:
            return {"type": "array", "items": python_type_to_json_type(item_type)}
        return {"type": "array"}
    elif py_type in (dict, Dict) or origin in (dict, Dict):
        return {"type": "object"}
    elif py_type is inspect._empty:
        return {"type": "string"}
    
    return {"type": "string"}


def extract_function_schema(fn: Callable) -> Dict[str, Any]:
    """Introspects function signature and generates JSON Schema Draft 7 object."""
    sig = inspect.signature(fn)
    properties: Dict[str, Any] = {}
    required: List[str] = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue

        prop_schema = python_type_to_json_type(param.annotation)

        if param.default is not inspect._empty:
            prop_schema["default"] = param.default
        else:
            required.append(param_name)

        properties[param_name] = prop_schema

    schema: Dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required

    return schema


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._definitions: Dict[str, ToolDefinition] = {}

    def register(self, fn: Callable, name: Optional[str] = None, description: Optional[str] = None):
        tool_name = name or fn.__name__
        tool_desc = description or inspect.getdoc(fn) or ""
        input_schema = extract_function_schema(fn)

        definition = ToolDefinition(
            name=tool_name,
            description=tool_desc.strip(),
            inputSchema=input_schema
        )
        self._tools[tool_name] = fn
        self._definitions[tool_name] = definition
        return fn

    def tool(self, name: Optional[str] = None, description: Optional[str] = None):
        def decorator(fn: Callable):
            return self.register(fn, name, description)
        return decorator

    def list_tools(self) -> List[ToolDefinition]:
        return list(self._definitions.values())

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> CallToolResult:
        if name not in self._tools:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: Tool '{name}' not found.")],
                isError=True
            )

        fn = self._tools[name]
        args = arguments or {}

        try:
            if inspect.iscoroutinefunction(fn):
                res = await fn(**args)
            else:
                res = fn(**args)

            if isinstance(res, (dict, list)):
                text_out = json.dumps(res, indent=2, default=str)
            else:
                text_out = str(res)

            return CallToolResult(
                content=[TextContent(type="text", text=text_out)],
                isError=False
            )
        except Exception as e:
            err_msg = f"Error executing tool '{name}': {str(e)}\n{traceback.format_exc()}"
            return CallToolResult(
                content=[TextContent(type="text", text=err_msg)],
                isError=True
            )


class ResourceRegistry:
    def __init__(self):
        self._resources: Dict[str, Callable] = {}
        self._definitions: Dict[str, ResourceDefinition] = {}

    def register(self, uri: str, fn: Callable, name: Optional[str] = None, description: Optional[str] = None, mime_type: str = "text/plain"):
        res_name = name or fn.__name__
        res_desc = description or inspect.getdoc(fn) or ""

        definition = ResourceDefinition(
            uri=uri,
            name=res_name,
            description=res_desc.strip(),
            mimeType=mime_type
        )
        self._resources[uri] = fn
        self._definitions[uri] = definition
        return fn

    def resource(self, uri: str, name: Optional[str] = None, description: Optional[str] = None, mime_type: str = "text/plain"):
        def decorator(fn: Callable):
            return self.register(uri, fn, name, description, mime_type)
        return decorator

    def list_resources(self) -> List[ResourceDefinition]:
        return list(self._definitions.values())

    async def read_resource(self, uri: str) -> ReadResourceResult:
        if uri not in self._resources:
            return ReadResourceResult(contents=[])

        fn = self._resources[uri]
        mime_type = self._definitions[uri].mimeType or "text/plain"

        try:
            if inspect.iscoroutinefunction(fn):
                res = await fn()
            else:
                res = fn()

            if isinstance(res, (dict, list)):
                text_content = json.dumps(res, indent=2)
            else:
                text_content = str(res)

            return ReadResourceResult(
                contents=[ResourceContent(uri=uri, mimeType=mime_type, text=text_content)]
            )
        except Exception as e:
            return ReadResourceResult(
                contents=[ResourceContent(uri=uri, mimeType=mime_type, text=f"Error reading resource: {str(e)}")]
            )


class MCPDispatcher:
    """Dispatches JSON-RPC 2.0 requests to the appropriate MCP handlers."""

    def __init__(
        self,
        server_name: str = "Custom-MCP-Server",
        server_version: str = "1.0.0",
        tool_registry: Optional[ToolRegistry] = None,
        resource_registry: Optional[ResourceRegistry] = None,
    ):
        self.server_info = Implementation(name=server_name, version=server_version)
        self.tool_registry = tool_registry or ToolRegistry()
        self.resource_registry = resource_registry or ResourceRegistry()

    async def dispatch(self, req: JSONRPCRequest) -> Optional[JSONRPCResponse]:
        method = req.method
        req_id = req.id
        params = req.params if isinstance(req.params, dict) else {}

        # Handle notifications (requests without id)
        is_notification = req_id is None

        try:
            if method == "initialize":
                result = InitializeResult(
                    protocolVersion=LATEST_PROTOCOL_VERSION,
                    capabilities=ServerCapabilities(
                        tools=ToolsCapability(listChanged=False),
                        resources=ResourcesCapability(subscribe=False, listChanged=False),
                    ),
                    serverInfo=self.server_info,
                )
                return JSONRPCResponse(id=req_id, result=result.model_dump())

            elif method in ("notifications/initialized", "initialized"):
                # Acknowledged initialization notification
                return None

            elif method == "ping":
                return JSONRPCResponse(id=req_id, result={})

            elif method == "tools/list":
                tools = self.tool_registry.list_tools()
                return JSONRPCResponse(
                    id=req_id,
                    result={"tools": [t.model_dump() for t in tools]}
                )

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                if not tool_name:
                    return JSONRPCResponse(
                        id=req_id,
                        error=JSONRPCError(code=INVALID_PARAMS, message="Missing 'name' in tools/call parameters.")
                    )
                call_result = await self.tool_registry.call_tool(tool_name, arguments)
                return JSONRPCResponse(id=req_id, result=call_result.model_dump())

            elif method == "resources/list":
                resources = self.resource_registry.list_resources()
                return JSONRPCResponse(
                    id=req_id,
                    result={"resources": [r.model_dump() for r in resources]}
                )

            elif method == "resources/read":
                uri = params.get("uri")
                if not uri:
                    return JSONRPCResponse(
                        id=req_id,
                        error=JSONRPCError(code=INVALID_PARAMS, message="Missing 'uri' in resources/read parameters.")
                    )
                read_res = await self.resource_registry.read_resource(uri)
                return JSONRPCResponse(id=req_id, result=read_res.model_dump())

            else:
                if is_notification:
                    return None
                return JSONRPCResponse(
                    id=req_id,
                    error=JSONRPCError(
                        code=METHOD_NOT_FOUND,
                        message=f"Method '{method}' not found."
                    )
                )

        except Exception as e:
            if is_notification:
                return None
            return JSONRPCResponse(
                id=req_id,
                error=JSONRPCError(
                    code=INTERNAL_ERROR,
                    message=f"Internal Server Error: {str(e)}",
                    data=traceback.format_exc()
                )
            )
