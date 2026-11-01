"""A local, read-only MCP server with the synthetic business data of the examples.

Two examples can work with live data from other systems through MCP: the supplier comparison reads supplier
scorecards from an ERP system, the customer service looks up orders in the shop system. Without a connection
both run in their labelled offline mode with the same data as a sample file. This server lets a person try the
real MCP path without an ERP or shop system: it serves exactly the data of those sample files, in one language,
over Streamable HTTP on the loopback interface.

    python -m nodestro_examples.demo_mcp --language de          # http://127.0.0.1:8765/mcp

Then, in Nodestro (desktop): Tools → Connected services → connect ``http://127.0.0.1:8765/mcp`` with the consent for
a local development server, check the server, approve its tools as **read** and copy the example with this server
as its connection. Every tool only reads; none changes anything, and the server keeps no state. It is a test
implementation: the answers are synthetic and marked as such, never real company data. A real ERP or shop
system can take its place when its MCP server offers tools with the same names (``list_suppliers``,
``supplier_scorecard``, ``get_order``) and an administrator approves them as read-only.

Needs the ``mcp`` package (Python 3.11 or later), which Nodestro's runtime installs.
"""

from __future__ import annotations

import argparse
from typing import Any

from nodestro_runtime.schemas import LANGUAGES

from . import language_of, texts

#: Where the data comes from: the sample files of the examples that use the server.
SUPPLIERS = ("supplier-comparison", "history")
ORDERS = ("customer-service", "orders")
#: The tools the server offers (the integrations of the examples name them).
TOOLS = ("list_suppliers", "supplier_scorecard", "get_order")
NOTICE = "SYNTHETIC DEMO DATA from the Nodestro example library (not a real system)"
DEFAULT_PORT = 8765


def _rows(template_id: str, sample_id: str, language: str) -> list[dict[str, Any]]:
    content = texts(template_id, language).samples[sample_id].content
    if isinstance(content, dict):  # an Excel file: the first sheet, header row first
        rows = next(iter(content.values()))
        header = [str(cell) for cell in rows[0]]
        return [dict(zip(header, row, strict=True)) for row in rows[1:]]
    return list(content)


def suppliers(language: str) -> list[dict[str, Any]]:
    """The supplier scorecards of the ERP export, as records with the column names of the language."""
    return _rows(*SUPPLIERS, language_of(language))


def orders(language: str) -> list[dict[str, Any]]:
    """The orders of the shop system's export."""
    return _rows(*ORDERS, language_of(language))


def _key(record: dict[str, Any], position: int) -> str:
    return str(list(record.values())[position])


def find_supplier(language: str, supplier: str) -> dict[str, Any] | None:
    """A supplier's scorecard by id (first column) or by a part of its name (second column), ignoring case."""
    wanted = supplier.strip().casefold()
    if not wanted:
        return None
    for record in suppliers(language):
        if _key(record, 0).casefold() == wanted or wanted in _key(record, 1).casefold():
            return record
    return None


def find_order(language: str, order_number: str) -> dict[str, Any] | None:
    wanted = "".join(char for char in order_number if char.isdigit())
    return next((record for record in orders(language) if str(record.get("order")) == wanted), None)


def build_server(language: str = "en") -> Any:
    """The MCP server for one language (official MCP SDK)."""
    from mcp.server.mcpserver import MCPServer
    from mcp_types import ToolAnnotations

    language = language_of(language)
    read_only = ToolAnnotations(
        read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
    )
    server = MCPServer(
        "nodestro-demo-data",
        instructions=f"{NOTICE}. Read-only lookups in a fictional ERP and shop system.",
    )

    @server.tool(annotations=read_only)
    def list_suppliers() -> dict[str, Any]:
        """List the suppliers in the ERP system with their supplier id and name."""
        records = suppliers(language)
        return {"notice": NOTICE, "suppliers": [{"id": _key(item, 0), "name": _key(item, 1)} for item in records]}

    @server.tool(annotations=read_only)
    def supplier_scorecard(supplier: str) -> dict[str, Any]:
        """The supplier's scorecard of the last 12 months from the ERP system: on-time delivery, quality (ppm),
        complaints, open 8D reports, last audit and notes. ``supplier`` is the supplier id or a part of its name."""
        record = find_supplier(language, supplier)
        if record is None:
            return {"notice": NOTICE, "found": False, "supplier": supplier}
        return {"notice": NOTICE, "found": True, "scorecard": record}

    @server.tool(annotations=read_only)
    def get_order(order_number: str) -> dict[str, Any]:
        """An order from the shop system: order and delivery dates, status, items and the carrier's latest note."""
        record = find_order(language, order_number)
        if record is None:
            return {"notice": NOTICE, "found": False, "order_number": order_number}
        return {"notice": NOTICE, "found": True, "order": record}

    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m nodestro_examples.demo_mcp", description=__doc__.splitlines()[0])
    parser.add_argument("--language", choices=LANGUAGES, default="en", help="the language of the data")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    import uvicorn

    app = build_server(args.language).streamable_http_app()
    print(f"Nodestro demo MCP server ({NOTICE}): http://127.0.0.1:{args.port}/mcp")
    # Loopback only: the server is meant for the person's own Nodestro on the same computer.
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
