"""KSPR MCP Client — connects to MCP servers and exposes their tools."""

from __future__ import annotations

from typing import Any

import httpx

from .models import MCPServerConfig, MCPTool, MCPToolResult


class MCPClientError(RuntimeError):
    """Error communicating with an MCP server."""


class MCPClient:
    """Connects to a single MCP server (remote HTTP or local stdio)."""

    def __init__(self, name: str, config: MCPServerConfig):
        self.name = name
        self.config = config
        self.connected = False
        self._tools: list[MCPTool] = []

    async def connect(self) -> bool:
        if not self.config.enabled:
            return False
        try:
            if self.config.type == "remote" and self.config.url:
                self.connected = await self._connect_remote()
            elif self.config.type == "local" and self.config.command:
                self.connected = True
            return self.connected
        except Exception:
            self.connected = False
            return False

    async def _connect_remote(self) -> bool:
        url = self.config.url.rstrip("/")
        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)
            data = response.json()
            if "result" in data:
                raw_tools = data["result"].get("tools", [])
                self._tools = [
                    MCPTool(
                        name=t.get("name", ""),
                        description=t.get("description", ""),
                        input_schema=t.get("inputSchema", t.get("parameters", {})),
                        server=self.name,
                    )
                    for t in raw_tools
                ]
                return True
        return False

    async def list_tools(self) -> list[MCPTool]:
        if not self.connected:
            await self.connect()
        return self._tools

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": f"{self.name}:{tool.name}",
                    "description": tool.description,
                    "parameters": tool.input_schema,
                }
            }
            for tool in self._tools
        ]

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        if self.config.type == "remote" and self.config.url:
            return await self._call_remote(tool_name, arguments)
        return MCPToolResult(
            tool_name=tool_name,
            error=f"Local MCP execution not yet supported for server '{self.name}'"
        )

    async def _call_remote(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        url = self.config.url.rstrip("/")
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, json=payload)
            data = response.json()
            if "result" in data:
                return MCPToolResult(tool_name=tool_name, result=data["result"])
            error_msg = data.get("error", {}).get("message", "Unknown error")
            return MCPToolResult(tool_name=tool_name, error=error_msg)

    async def health_check(self) -> bool:
        return await self.connect()


class MCPManager:
    """Manages multiple MCP server connections and consolidates tools."""

    def __init__(self, servers_config: dict[str, MCPServerConfig]):
        self.clients: dict[str, MCPClient] = {}
        for name, config in servers_config.items():
            self.clients[name] = MCPClient(name, config)

    async def connect_all(self) -> int:
        count = 0
        for client in self.clients.values():
            if await client.connect():
                count += 1
        return count

    async def get_all_tools(self) -> list[MCPTool]:
        tools: list[MCPTool] = []
        for client in self.clients.values():
            client_tools = await client.list_tools()
            tools.extend(client_tools)
        return tools

    def get_tools_sync(self) -> list[MCPTool]:
        tools: list[MCPTool] = []
        for client in self.clients.values():
            tools.extend(client._tools)
        return tools

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        schemas: list[dict[str, Any]] = []
        for tool in self.get_tools_sync():
            schemas.append({
                "type": "function",
                "function": {
                    "name": f"{tool.server}:{tool.name}",
                    "description": tool.description,
                    "parameters": tool.input_schema,
                }
            })
        return schemas

    async def execute_tool(self, full_name: str, arguments: dict[str, Any]) -> str:
        result = await self.call_tool(full_name, arguments)
        if result.error:
            return f"Tool error: {result.error}"
        return str(result.result) if result.result is not None else f"Tool '{full_name}' returned no content."

    async def call_tool(self, full_tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        if ":" in full_tool_name:
            server_name, tool_name = full_tool_name.split(":", 1)
        else:
            server_name = None
            tool_name = full_tool_name

        if server_name and server_name in self.clients:
            return await self.clients[server_name].call_tool(tool_name, arguments)

        for client in self.clients.values():
            for t in client._tools:
                if t.name == tool_name:
                    return await client.call_tool(tool_name, arguments)

        return MCPToolResult(tool_name=full_tool_name, error=f"Tool '{full_tool_name}' not found in any connected MCP server")

    def get_connected_servers(self) -> list[dict[str, Any]]:
        result = []
        for name, client in self.clients.items():
            result.append({
                "name": name,
                "type": client.config.type,
                "url": client.config.url,
                "command": client.config.command,
                "enabled": client.config.enabled,
                "connected": client.connected,
                "tools_count": len(client._tools),
            })
        return result

    def remove_server(self, name: str) -> bool:
        if name in self.clients:
            del self.clients[name]
            return True
        return False

    def add_server(self, name: str, config: MCPServerConfig) -> MCPClient:
        client = MCPClient(name, config)
        self.clients[name] = client
        return client
