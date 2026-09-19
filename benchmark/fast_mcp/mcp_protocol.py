#!/usr/bin/env python3
"""
Fast-MCP Model Context Protocol (MCP) JSON-RPC 2.0 Interface
Implements:
  - tools/list: Exposes declarative parameter schemas to foundation models at handshake.
  - tools/call: Dispatches validated arguments to Fast-MCP semantic primitives.
"""

import json
from typing import Dict, Any, List
try:
    from .semantic_tools import SemanticFastTools
except ImportError:
    from semantic_tools import SemanticFastTools

TOOL_DEFINITIONS = [
    {
        "name": "get_delayed_projects",
        "description": "Retrieve high-risk lagging projects exceeding remaining unspent budget threshold for a specific department.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dept_code": {"type": "string", "description": "Department code (e.g. '10010000')"},
                "fiscal_year": {"type": "integer", "default": 2026, "description": "Fiscal year"},
                "month": {"type": "integer", "default": 12, "description": "Accounting month (1-12)"},
                "min_remain": {"type": "number", "default": 50000.0, "description": "Remaining budget threshold"}
            },
            "required": ["dept_code"]
        }
    },
    {
        "name": "reconcile_staff_advances",
        "description": "Reconcile cash advances and expense forms for personnel within a department.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dept_code": {"type": "string", "description": "Department code"}
            },
            "required": ["dept_code"]
        }
    },
    {
        "name": "get_department_summary",
        "description": "Retrieve cross-departmental financial summary and burn rate comparison without Cartesian joins.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dept_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of department codes to compare"
                },
                "fiscal_year": {"type": "integer", "default": 2026},
                "month": {"type": "integer", "default": 12}
            },
            "required": ["dept_codes"]
        }
    }
]

class MCPProtocolHandler:
    def __init__(self, db_path: str):
        self.fast_tools = SemanticFastTools(db_path)

    def handle_request(self, request_json: str) -> str:
        req = json.loads(request_json)
        method = req.get("method")
        msg_id = req.get("id")

        if method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": TOOL_DEFINITIONS}
            }
        elif method == "tools/call":
            params = req.get("params", {})
            name = params.get("name")
            arguments = params.get("arguments", {})

            if name == "get_delayed_projects":
                res = self.fast_tools.get_delayed_projects(**arguments)
            elif name == "reconcile_staff_advances":
                res = self.fast_tools.reconcile_staff_advances(**arguments)
            elif name == "get_department_summary":
                res = self.fast_tools.get_department_summary(**arguments)
            else:
                return json.dumps({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Method {name} not found"}
                })

            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(res, indent=2)}]
                }
            }
        else:
            response = {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32600, "message": "Invalid Request"}
            }

        return json.dumps(response)

if __name__ == "__main__":
    db = "benchmark/data/enterprise_800k.db"
    handler = MCPProtocolHandler(db)
    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_delayed_projects",
            "arguments": {"dept_code": "10010000", "fiscal_year": 2026, "month": 12}
        }
    })
    resp = handler.handle_request(req)
    print(f"MCP Response:\n{resp[:200]}...")
