"""MCP Auth configuration and protected-resource metadata for company tools."""

from __future__ import annotations

import os
from typing import Any

import jwt
from mcpauth import AuthInfo, AuthServerConfig, MCPAuth
from mcpauth.config import AuthServerType, AuthorizationServerMetadata
from starlette.requests import Request
from starlette.responses import JSONResponse


MCP_SCOPES = (
    "incidents:read",
    "incidents:write",
    "inventory:read",
)


def _issuer() -> str:
    return os.getenv("MCP_AUTH_ISSUER", "http://localhost:8001").rstrip("/")


def _metadata() -> AuthorizationServerMetadata:
    issuer = _issuer()
    jwks_uri = os.getenv("MCP_AUTH_JWKS_URI", "").strip() or None
    return AuthorizationServerMetadata(
        issuer=issuer,
        authorization_endpoint=os.getenv(
            "MCP_AUTHORIZATION_ENDPOINT", f"{issuer}/authorize"
        ),
        token_endpoint=os.getenv("MCP_TOKEN_ENDPOINT", f"{issuer}/token"),
        jwks_uri=jwks_uri,
        scope_supported=list(MCP_SCOPES),
        response_types_supported=["code"],
        grant_types_supported=["authorization_code"],
        token_endpoint_auth_methods_supported=["client_secret_basic"],
        code_challenge_methods_supported=["S256"],
    )


MCP_AUTH = MCPAuth(
    server=AuthServerConfig(
        metadata=_metadata(),
        type=AuthServerType.OIDC,
    )
)


def protected_resource_metadata(request: Request) -> JSONResponse:
    """Advertise the OAuth issuer and scopes required by the MCP resource."""

    resource = os.getenv("MCP_RESOURCE_URL", "http://localhost:8001/mcp")
    return JSONResponse(
        {
            "resource": resource,
            "authorization_servers": [_issuer()],
            "scopes_supported": list(MCP_SCOPES),
        }
    )


def _verify_local_jwt(token: str) -> AuthInfo:
    """Validate a local-development JWT when no remote JWKS URI is configured."""

    secret = os.getenv("MCP_JWT_SECRET", "").strip()
    if not secret:
        raise ValueError("MCP_JWT_SECRET is not configured")

    algorithm = os.getenv("MCP_JWT_ALGORITHM", "HS256")
    claims: dict[str, Any] = jwt.decode(
        token,
        secret,
        algorithms=[algorithm],
        options={"verify_aud": False, "verify_iss": False},
    )
    expected_issuer = _issuer()
    if claims.get("iss") != expected_issuer:
        raise ValueError("token issuer does not match MCP_AUTH_ISSUER")

    audience = os.getenv("MCP_AUDIENCE", "").strip()
    token_audience = claims.get("aud")
    audience_matches = token_audience == audience or (
        isinstance(token_audience, list) and audience in token_audience
    )
    if audience and not audience_matches:
        raise ValueError("token audience does not match MCP_AUDIENCE")

    raw_scopes = claims.get("scope", claims.get("scopes", []))
    scopes = raw_scopes.split() if isinstance(raw_scopes, str) else list(raw_scopes or [])
    return AuthInfo(
        token=token,
        issuer=expected_issuer,
        client_id=claims.get("client_id") or claims.get("azp"),
        subject=str(claims.get("sub", "unknown")),
        audience=token_audience,
        scopes=scopes,
        claims=claims,
    )


def bearer_auth_middleware() -> type:
    """Create MCP Auth middleware for remote JWKS or local signed JWTs."""

    audience = os.getenv("MCP_AUDIENCE", "").strip() or None
    required_scopes = None
    if os.getenv("MCP_AUTH_JWKS_URI", "").strip():
        return MCP_AUTH.bearer_auth_middleware(
            "jwt",
            audience=audience,
            required_scopes=required_scopes,
            show_error_details=False,
        )
    return MCP_AUTH.bearer_auth_middleware(
        _verify_local_jwt,
        audience=audience,
        required_scopes=required_scopes,
        show_error_details=False,
    )


def authenticated_client_id() -> str:
    auth_info = current_auth_info()
    if auth_info is None:
        return "anonymous"
    return auth_info.client_id or auth_info.subject


def current_auth_info() -> AuthInfo | None:
    """Read request auth, or validate the explicit token used by local stdio."""

    auth_info = MCP_AUTH.auth_info
    if auth_info is not None or os.getenv("MCP_TRANSPORT") != "stdio":
        return auth_info
    token = os.getenv("MCP_ACCESS_TOKEN", "").strip()
    if not token:
        return None
    try:
        auth_info = _verify_local_jwt(token)
    except Exception:
        return None
    MCP_AUTH._context_var.set(auth_info)
    return auth_info


def require_scope(scope: str) -> None:
    """Enforce a tool-specific scope after MCP Auth validates the bearer token."""

    auth_info = current_auth_info()
    if auth_info is None:
        raise PermissionError("AUTH_MISSING_TOKEN: a valid OAuth access token is required")
    if scope not in auth_info.scopes:
        raise PermissionError(f"AUTH_SCOPE_REQUIRED: missing required scope {scope}")
