"""Protocol-level checks for the MCP SDK integration."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from unittest.mock import patch

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import pytest


def test_main_uses_stdio():
    from server import main

    with patch("server.mcp.run") as run:
        main()

    run.assert_called_once_with(transport="stdio")


@pytest.mark.asyncio
async def test_stdio_tool_discovery_and_call():
    script = """
import server

async def mock_get(path, params=None):
    assert path == "/document/7192477"
    return {"result": {"id": 7192477, "title": {"title": "Test document"}}}

server._get = mock_get
server.main()
"""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-c", script],
        cwd=str(Path(__file__).resolve().parents[1]),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            assert initialized.server_info.name == "zbmath"
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {
                "search_documents",
                "get_document",
                "structured_search",
                "get_author",
                "get_software",
            }
            document_tool = next(
                tool for tool in tools.tools if tool.name == "get_document"
            )
            assert document_tool.input_schema["required"] == ["zbmath_id"]
            assert (
                document_tool.input_schema["properties"]["zbmath_id"]["type"]
                == "integer"
            )
            result = await session.call_tool(
                "get_document", {"zbmath_id": 7192477}
            )
            assert not result.is_error
            assert len(result.content) == 1
            content = result.content[0]
            assert content.type == "text"
            assert json.loads(content.text) == {
                "id": 7192477,
                "title": {"title": "Test document"},
            }
