"""
Model Context Protocol (MCP) Specification Types (2024-11-05).
"""
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

LATEST_PROTOCOL_VERSION = "2024-11-05"

class Implementation(BaseModel):
    name: str
    version: str

class ToolsCapability(BaseModel):
    listChanged: Optional[bool] = False

class ResourcesCapability(BaseModel):
    subscribe: Optional[bool] = False
    listChanged: Optional[bool] = False

class ServerCapabilities(BaseModel):
    tools: Optional[ToolsCapability] = Field(default_factory=ToolsCapability)
    resources: Optional[ResourcesCapability] = Field(default_factory=ResourcesCapability)
    logging: Optional[Dict[str, Any]] = None

class ClientCapabilities(BaseModel):
    roots: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None

class InitializeParams(BaseModel):
    protocolVersion: str
    capabilities: Optional[ClientCapabilities] = None
    clientInfo: Optional[Implementation] = None

class InitializeResult(BaseModel):
    protocolVersion: str = LATEST_PROTOCOL_VERSION
    capabilities: ServerCapabilities = Field(default_factory=ServerCapabilities)
    serverInfo: Implementation

class ToolDefinition(BaseModel):
    name: str
    description: Optional[str] = ""
    inputSchema: Dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})

class TextContent(BaseModel):
    type: str = "text"
    text: str

class CallToolResult(BaseModel):
    content: List[TextContent] = Field(default_factory=list)
    isError: bool = False

class ResourceDefinition(BaseModel):
    uri: str
    name: str
    description: Optional[str] = ""
    mimeType: Optional[str] = "text/plain"

class ResourceContent(BaseModel):
    uri: str
    mimeType: Optional[str] = "text/plain"
    text: Optional[str] = None
    blob: Optional[str] = None

class ReadResourceResult(BaseModel):
    contents: List[ResourceContent] = Field(default_factory=list)
