"""
JSON-RPC 2.0 Protocol Specifications and Data Models.
Standard: https://www.jsonrpc.org/specification
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

# Standard JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None

class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    method: str
    params: Optional[Union[Dict[str, Any], List[Any]]] = None

class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[Union[str, int]] = None
    result: Optional[Any] = None
    error: Optional[JSONRPCError] = None

class JSONRPCNotification(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Union[Dict[str, Any], List[Any]]] = None
