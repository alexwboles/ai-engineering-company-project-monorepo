"""Authenticated Streamable HTTP MCP server for HealthCore company tools."""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Mount, Route
from starlette.responses import PlainTextResponse

from .auth import MCP_AUTH, bearer_auth_middleware, protected_resource_metadata
from .tools.incidents import INCIDENT_OUTPUT_SCHEMA, manage_incident_ticket
from .tools.inventory import INVENTORY_OUTPUT_SCHEMA, query_inventory


logging.basicConfig(level=logging.INFO)

mcp = FastMCP(
    "HealthCore Company Tools",
    instructions=(
        "Authenticated HealthCore operational tools. Use manage_incident_ticket "
        "for incident lifecycle operations and query_inventory for read-only stock. "
        "Inventory modifications are forbidden."
    ),
)
mcp.add_tool(
    mcp.tool(output_schema=INCIDENT_OUTPUT_SCHEMA)(manage_incident_ticket)
)
mcp.add_tool(
    mcp.tool(output_schema=INVENTORY_OUTPUT_SCHEMA)(query_inventory)
)


def create_app() -> Starlette:
    """Build the HTTP app with public metadata and an authenticated MCP mount."""

    mcp_transport = mcp.http_app(
        path="/",
        transport="streamable-http",
        json_response=True,
        stateless_http=True,
    )
    protected_mcp = Starlette(
        routes=[Mount("/", app=mcp_transport)],
        middleware=[Middleware(bearer_auth_middleware())],
    )
    return Starlette(
        routes=[
            MCP_AUTH.metadata_route(),
            Route(
                "/.well-known/oauth-protected-resource",
                protected_resource_metadata,
                methods=["GET"],
            ),
            Route("/health", lambda request: PlainTextResponse("ok"), methods=["GET"]),
            Mount("/mcp", app=protected_mcp),
        ]
    )


app = create_app()


if __name__ == "__main__":
    mcp.run(transport="stdio")
