"""KSPR Autonomous Cognitive OS: Model Context Protocol (MCP) Native Server."""

from __future__ import annotations

import json
from pathlib import Path

from .memory import VectorMemory
from .sandbox import SafeSandbox


class MCPServer:
    """Servidor MCP para exponer recursos y herramientas de KSPR a clientes externos (Cursor, Claude Desktop, etc.)."""
    def __init__(self, workspace_root: Path | None = None):
        self.sandbox = SafeSandbox(workspace_root)
        self.memory = VectorMemory()

    def handle_request(self, request_json: str) -> str:
        try:
            req = json.loads(request_json)
            method = req.get("method")
            params = req.get("params", {})
            req_id = req.get("id", 1)

            if method == "resources/list":
                return json.dumps({
                    "jsonrpc": "2.0",
                    "result": {
                        "resources": [
                            {"uri": "kspr://workspace/files", "name": "Workspace Files"},
                            {"uri": "kspr://memory/index", "name": "Vector Memory Index"}
                        ]
                    },
                    "id": req_id
                })
            elif method == "tools/list":
                return json.dumps({
                    "jsonrpc": "2.0",
                    "result": {
                        "tools": [
                            {"name": "read_file", "description": "Lee un archivo del workspace"},
                            {"name": "write_file", "description": "Escribe un archivo en el workspace"},
                            {"name": "search_memory", "description": "Búsqueda semántica en la memoria vectorial"}
                        ]
                    },
                    "id": req_id
                })
            elif method == "tools/call":
                tool_name = params.get("name")
                args = params.get("arguments", {})
                if tool_name == "read_file":
                    content = self.sandbox.read_file(args.get("path", ""))
                    return json.dumps({"jsonrpc": "2.0", "result": {"content": content}, "id": req_id})
                elif tool_name == "write_file":
                    path = self.sandbox.write_file(args.get("path", ""), args.get("content", ""))
                    return json.dumps({"jsonrpc": "2.0", "result": {"success": True, "path": path}, "id": req_id})
                elif tool_name == "search_memory":
                    results = self.memory.search(args.get("query", ""))
                    return json.dumps({"jsonrpc": "2.0", "result": {"results": results}, "id": req_id})

            return json.dumps({"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": req_id})
        except Exception as e:
            return json.dumps({"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": 1})
