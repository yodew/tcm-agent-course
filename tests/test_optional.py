import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from examples.graph_workflow import exercise


@pytest.mark.anyio
async def test_graph_when_branch_risky_uses_handoff() -> None:
    # Given / When
    result = await exercise("我有胸痛")
    # Then
    assert result.action == "handoff"
    assert result.steps == 0


@pytest.mark.anyio
async def test_graph_when_knowledge_requested_completes_tool_loop() -> None:
    # Given / When
    result = await exercise("什么是四诊")
    # Then
    assert result.action == "knowledge"
    assert result.citations[0].entry_id == "tcm-four-examinations"


@pytest.mark.anyio
async def test_mcp_when_real_subprocess_started_discovers_and_calls_tool() -> None:
    # Given
    parameters = StdioServerParameters(command=sys.executable, args=["examples/mcp_server.py"])
    async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        # When
        listed = await session.list_tools()
        result = await session.call_tool("search_public_knowledge", {"query": "四诊"})
    # Then
    assert {tool.name for tool in listed.tools} == {
        "search_public_knowledge",
        "search_clinical_references",
        "get_clinical_document",
    }
    assert result.isError is False
    assert result.content
