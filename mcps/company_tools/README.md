# HealthCore Company Tools MCP Server

This server exposes the existing HealthCore Incidents Manager and inventory API
through an authenticated Model Context Protocol service. It never stores a
second copy of incident or inventory data.

## Transport and authentication

The default transport is Streamable HTTP at `/mcp`. It is the right default
for an agent and external clients because multiple processes and teams can
connect to one independently deployed server. MCP Auth protects the MCP mount
with bearer JWT validation and publishes both OAuth authorization metadata and
Protected Resource Metadata. The `MCP_AUTH_JWKS_URI` setting enables validation
against a remote OIDC/OAuth 2.1 provider.

For local single-process development, set `MCP_TRANSPORT=stdio`; the agent
spawns `python -m mcps.company_tools.server`. The stdio path still carries the
same MCP Auth configuration for tool-level scope checks. For a local signed
JWT test, set `MCP_JWT_SECRET`; production clients should use the JWKS setting.

## Run

```powershell
uv run --project services/api uvicorn mcps.company_tools.server:app --host 0.0.0.0 --port 8001
```

Set `MCP_UPSTREAM_TOKEN` to a service JWT accepted by the existing API. The
server reads incident data from `GET /api/incidents/{id}`, creates incidents
with `POST /api/incidents`, updates only status with
`PATCH /api/incidents/{id}/status`, and reads inventory from
`GET /inventory/products` or its product-id variant.

## Discovery contract

| Tool | Scope | Purpose |
| --- | --- | --- |
| `manage_incident_ticket` | `incidents:read` or `incidents:write` | Create, update status, or query a HealthCore incident. |
| `query_inventory` | `inventory:read` | Query product name, SKU, and derived current stock. |

Inventory accepts `action=update` and optional `quantity` only so a client can
receive the explicit `INVENTORY_WRITE_FORBIDDEN` error. It never writes stock.
Other controlled codes include `AUTH_MISSING_TOKEN`,
`AUTH_SCOPE_REQUIRED`, `VALIDATION_ERROR`, `UPSTREAM_NOT_FOUND`,
`UPSTREAM_TIMEOUT`, and `UPSTREAM_HTTP_ERROR`.

Every successful or failed tool invocation emits a structured log containing
the timestamp, authenticated client, tool, safe input summary, result code,
and duration.

## External validation

From GitHub Codespaces, forward port `8001` with public visibility and paste
the forwarded `https` URL plus `/mcp` into MCP Playground. Verify discovery,
incident create/status/update, inventory query, and the explicit inventory
write rejection. A local `TestClient` suite covers the same auth, discovery,
scope, lifecycle-path, and write-rejection contracts in CI.
