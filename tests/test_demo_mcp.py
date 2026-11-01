"""The optional MCP integrations of the examples against the local demo server (official MCP SDK).

The server runs on the loopback interface in this process; nothing outside is contacted. The tests go
through the real path: the server is registered and checked in a workspace, an administrator approves
its tools as read-only, the template is copied with the connection, and the agent's tool call reaches
the server during a run. The model is a deterministic double: it decides to call the tool, the data
comes from the server. What a real model does with the data is not tested here.
"""

from __future__ import annotations

from collections.abc import Iterator
import socket
import threading
import time
from typing import Any

import pytest

pytest.importorskip("mcp")

from conftest import Scenario, finish, instantiate, start_request
from nodestro_runtime.mcp.models import McpServerIn, ToolAccess
from nodestro_runtime.schemas import LANGUAGES
from nodestro_runtime.workspace import Workspace

import nodestro_examples as library
from nodestro_examples import demo_mcp


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def demo_url() -> Iterator[str]:
    import uvicorn

    port = _free_port()
    app = demo_mcp.build_server("en").streamable_http_app()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error", lifespan="on"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline:  # pragma: no cover
            raise RuntimeError("the demo server did not start")
        time.sleep(0.02)
    yield f"http://127.0.0.1:{port}/mcp"
    server.should_exit = True
    thread.join(timeout=5)


def register(workspace: Workspace, url: str, *, approve: dict[str, ToolAccess]) -> str:
    """Add and check the server; approve the named tools with the given access (as an administrator)."""
    added = workspace.mcp.add(McpServerIn(name="Demo data", url=url, allow_loopback=True), actor="admin")
    workspace.mcp.discover(added.id)
    for name, access in approve.items():
        tool = workspace.mcp.tool(added.id, name)
        workspace.mcp.decide(added.id, name, approve=True, expected_hash=tool.hash, access=access, actor="admin")
    return added.id


def offered(workspace: Workspace, server_id: str) -> dict[str, library.ServerTool]:
    """The server's tools as the copy path sees them (what the API's copy route passes to ``connect``)."""
    return {
        tool.name: library.ServerTool(agent_name=tool.tool_name, approved=tool.status == "approved", access=tool.access)
        for tool in workspace.mcp.tools(server_id)
    }


# ---- the data ----------------------------------------------------------------------------


@pytest.mark.parametrize("language", LANGUAGES)
def test_the_demo_data_is_the_sample_data_of_the_examples(language: str) -> None:
    suppliers = demo_mcp.suppliers(language)
    assert [demo_mcp._key(item, 0) for item in suppliers] == ["S-1001", "S-1027", "S-1033"]
    assert demo_mcp.find_supplier(language, "s-1027") == suppliers[1]
    name = demo_mcp._key(suppliers[1], 1)
    assert demo_mcp.find_supplier(language, name.split()[1].upper()) == suppliers[1]
    # The new supplier of offer B has no history in the ERP system (three known suppliers only).
    assert demo_mcp.find_supplier(language, "S-1099") is None
    assert demo_mcp.find_supplier(language, " ") is None
    order = demo_mcp.find_order(language, "Order #10603")
    assert order is not None and "2026-03-23" in str(order)
    assert demo_mcp.find_order(language, "99999") is None
    assert {record["order"] for record in demo_mcp.orders(language)} == {"10442", "10518", "10603"}


async def test_every_tool_is_read_only_and_marked_synthetic() -> None:
    server = demo_mcp.build_server("de")
    tools = await server.list_tools()
    assert sorted(tool.name for tool in tools) == sorted(demo_mcp.TOOLS)
    assert all(tool.annotations.read_only_hint and not tool.annotations.destructive_hint for tool in tools)
    integrations = {item.id: item.tools for t in library.template_ids() for item in library.structure(t).integrations}
    assert integrations == {"erp": ["list_suppliers", "supplier_scorecard"], "shop": ["get_order"]}


# ---- the copy path -----------------------------------------------------------------------


async def test_a_connected_copy_reads_live_data_from_the_server(make_workspace: Any, demo_url: str) -> None:
    scenario = Scenario(tool_calls={"risk": [("supplier_scorecard", {"supplier": "S-1027"})]})
    workspace = make_workspace(scenario)
    server_id = register(workspace, demo_url, approve={"list_suppliers": "read", "supplier_scorecard": "read"})
    connection = library.connect("supplier-comparison", "erp", offered(workspace, server_id))
    workflow, made = instantiate(workspace, "supplier-comparison", "en", connections={"erp": connection})
    assert made.connected == ["erp"] and made.offline == []
    risk = next(node.agent for node in workflow.nodes if node.id == "risk")
    assert risk is not None and set(connection.values()) <= set(risk.tools)
    done = await finish(workspace, await workspace.run(workflow, start_request(workflow)))
    assert done.status == "succeeded", done.error
    [call] = done.nodes["risk"].tool_calls
    assert call.name == connection["supplier_scorecard"] and not call.is_error
    # The answer comes from the server (the ERP export's figures), marked as synthetic demo data.
    assert demo_mcp.NOTICE in (call.output or "") and "84" in (call.output or "")
    assert call.provenance["source"] == "mcp"


async def test_tools_that_may_change_data_are_never_connected(make_workspace: Any, demo_url: str) -> None:
    workspace = make_workspace(Scenario())
    server_id = register(workspace, demo_url, approve={"list_suppliers": "read", "supplier_scorecard": "write"})
    with pytest.raises(library.IntegrationProblem) as problem:
        library.connect("supplier-comparison", "erp", offered(workspace, server_id))
    assert problem.value.not_read_only == ["supplier_scorecard"]
    # A tool nobody approved is just as unavailable.
    other = register(workspace, demo_url, approve={"get_order": "read"})
    with pytest.raises(library.IntegrationProblem) as missing:
        library.connect("supplier-comparison", "erp", offered(workspace, other))
    assert missing.value.missing == ["list_suppliers", "supplier_scorecard"]


async def test_an_offline_copy_never_calls_the_server(make_workspace: Any, demo_url: str) -> None:
    workspace = make_workspace(Scenario(tool_calls={"policy": [("get_order", {"order_number": "10603"})]}))
    register(workspace, demo_url, approve={"get_order": "read"})
    workflow, made = instantiate(workspace, "customer-service", "en")
    assert made.offline == ["shop"]
    policy = next(node.agent for node in workflow.nodes if node.id == "policy")
    assert policy is not None and not any(tool.startswith("mcp__") for tool in policy.tools)
    assert library.texts("customer-service", "en").agents["policy"].offline.strip() in policy.system_prompt
    done = await finish(workspace, await workspace.run(workflow, start_request(workflow)))
    assert done.status == "succeeded", done.error
    assert not any(call.name.startswith("mcp__") for call in done.nodes["policy"].tool_calls)


async def test_unattended_runs_of_a_connected_copy_are_refused(
    make_workspace: Any, demo_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("NODESTRO_MCP_UNATTENDED", raising=False)
    workspace = make_workspace(Scenario(tool_calls={"policy": [("get_order", {"order_number": "10603"})]}))
    server_id = register(workspace, demo_url, approve={"get_order": "read"})
    connection = library.connect("customer-service", "shop", offered(workspace, server_id))
    workflow, _made = instantiate(workspace, "customer-service", "en", connections={"shop": connection})
    run = await workspace.run(workflow, start_request(workflow), trigger="schedule")
    done = await workspace.wait(run.id, timeout=60)
    assert done.status == "failed"
    assert done.nodes["policy"].error_code == "mcp.unattended_not_enabled"
