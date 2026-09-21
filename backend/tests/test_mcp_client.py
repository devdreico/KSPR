from unittest.mock import AsyncMock, MagicMock

import pytest
from kspr_engine.mcp_client import MCPClient, MCPManager
from kspr_engine.models import MCPServerConfig, MCPTool, MCPToolResult


class TestMCPClient:
    def test_tool_schema_generation(self):
        """MCPClient should generate OpenAI function schema from MCPTool."""
        client = MCPClient(name="test-server", config=MCPServerConfig(type="remote", url="http://localhost:8080", enabled=True))
        tool = MCPTool(name="read_file", server="test-server", description="Read a file", input_schema={"type": "object", "properties": {"path": {"type": "string"}}})
        client._tools = [tool]
        schemas = client.get_tool_schemas()
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        assert schemas[0]["function"]["name"] == "test-server:read_file"
        assert schemas[0]["function"]["description"] == "Read a file"

    def test_empty_tools(self):
        client = MCPClient(name="empty", config=MCPServerConfig(type="remote", url="http://localhost:8080", enabled=True))
        assert client.get_tool_schemas() == []


class TestMCPManager:
    def test_get_tool_schemas_aggregates(self):
        """MCPManager.get_tool_schemas() should aggregate from all clients."""
        mgr = MCPManager({})
        mock_client1 = MagicMock(spec=MCPClient)
        mock_client1._tools = [MCPTool(name="tool_a", server="s1", description="A")]
        mock_client1.get_tool_schemas = MagicMock(return_value=[{"type": "function", "function": {"name": "s1:tool_a", "description": "A", "parameters": {}}}])
        mock_client2 = MagicMock(spec=MCPClient)
        mock_client2._tools = [MCPTool(name="tool_b", server="s2", description="B")]
        mock_client2.get_tool_schemas = MagicMock(return_value=[{"type": "function", "function": {"name": "s2:tool_b", "description": "B", "parameters": {}}}])
        mgr.clients = {"s1": mock_client1, "s2": mock_client2}
        schemas = mgr.get_tool_schemas()
        assert len(schemas) == 2
        names = [s["function"]["name"] for s in schemas]
        assert "s1:tool_a" in names
        assert "s2:tool_b" in names

    def test_get_tools_sync(self):
        mgr = MCPManager({})
        mock_client = MagicMock(spec=MCPClient)
        mock_client._tools = [MCPTool(name="x", server="s", description="X")]
        mgr.clients = {"s": mock_client}
        tools = mgr.get_tools_sync()
        assert len(tools) == 1
        assert tools[0].name == "x"

    def test_get_tools_sync_empty(self):
        mgr = MCPManager({})
        assert mgr.get_tools_sync() == []

    @pytest.mark.asyncio
    async def test_execute_tool_delegates(self):
        mgr = MCPManager({})
        mock_client = AsyncMock(spec=MCPClient)
        mock_client.call_tool = AsyncMock(return_value=MCPToolResult(tool_name="do_thing", result="result-data"))
        mgr.clients = {"srv": mock_client}
        result = await mgr.execute_tool("srv:do_thing", {"arg1": "val"})
        assert result == "result-data"
        mock_client.call_tool.assert_awaited_once_with("do_thing", {"arg1": "val"})

    @pytest.mark.asyncio
    async def test_execute_tool_fallback_search(self):
        """If server prefix not found, should search all clients."""
        mgr = MCPManager({})
        mock_client = AsyncMock(spec=MCPClient)
        mock_client._tools = [MCPTool(name="find_me", server="other", description="")]
        mock_client.call_tool = AsyncMock(return_value=MCPToolResult(tool_name="find_me", result="found-it"))
        mgr.clients = {"other": mock_client}
        result = await mgr.execute_tool("find_me", {})
        assert result == "found-it"

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        mgr = MCPManager({})
        mgr.clients = {}
        result = await mgr.execute_tool("nonexistent", {})
        assert "not found" in result.lower() or "no clients" in result.lower()
