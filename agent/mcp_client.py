# =============================================================================
# MCP Client — Agent calls MCP Server directly (no APIM).
#
# The agent forwards the Bearer token as-is. Token verification
# (signature, audience, scope claims) is done inside the MCP Server.
#
# Three modes (controlled by MCP_SERVER_URL in .env):
#   1. MCP_SERVER_URL not set   → in-process mock (no network call)
#   2. MCP_SERVER_URL=http://localhost:9000 → local MCP Server (mcp_server/)
#   3. MCP_SERVER_URL=https://...           → remote MCP Server
#
# When APIM is added (Step 5), only MCP_SERVER_URL changes to the APIM
# endpoint — this file requires no code changes.
# =============================================================================

import os
import logging
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-process mock — used when MCP_SERVER_URL is not set.
# Lets the full agent loop run locally without any MCP Server process.
# ---------------------------------------------------------------------------
MOCK_RESPONSES = {
    "list_users": [
        {"id": "00u1abc", "login": "alice@example.com", "status": "ACTIVE"},
        {"id": "00u2def", "login": "bob@example.com",   "status": "ACTIVE"},
        {"id": "00u3ghi", "login": "carol@example.com", "status": "INACTIVE"},
    ],
    "get_user":       lambda a: {"id": a.get("user_id", "00u1abc"), "login": "alice@example.com",          "firstName": "Alice", "lastName": "Smith",          "status": "ACTIVE"},
    "create_user":    lambda a: {"id": "00u4new",                   "login": a.get("email", "new@example.com"), "firstName": a.get("first_name", ""), "lastName": a.get("last_name", ""), "status": "STAGED"},
    "deactivate_user":lambda a: {"id": a.get("user_id"),            "status": "DEPROVISIONED"},
    "get_group":      lambda a: {"id": a.get("group_id", "00g1grp"),"profile": {"name": "Engineering", "description": "Engineering team"}},
    "assign_app":     lambda a: {"id": "00a1assign",                "user_id": a.get("user_id"), "app_id": a.get("app_id"), "status": "ACTIVE"},
    "reset_mfa":      lambda a: {"user_id": a.get("user_id"),       "factors_reset": True},
}


def _mock_response(tool_name: str, args: dict) -> dict:
    mock = MOCK_RESPONSES.get(tool_name)
    if mock is None:
        return {"error": f"Unknown tool: {tool_name}"}
    return mock(args) if callable(mock) else mock


# ---------------------------------------------------------------------------
# MCP tool call — direct HTTP to MCP Server, token forwarded as-is.
# ---------------------------------------------------------------------------
async def call_tool(tool_name: str, args: dict, token: str) -> dict:
    """
    POST /mcp/call to the MCP Server with the Bearer token.
    The MCP Server is responsible for verifying the token.

    Uses in-process mock only if MCP_SERVER_URL is not set.
    If MCP_SERVER_URL is set, errors are raised (not silently swallowed)
    so auth/connectivity failures are visible in caller logs.
    """
    mcp_url = os.getenv("MCP_SERVER_URL")

    if not mcp_url:
        logger.warning("MCP_SERVER_URL not set — using in-process mock for: %s", tool_name)
        return _mock_response(tool_name, args)

    # XAA path: orchestrator sets token="local-dev" because there is no Entra OBO
    # token available. Sending "local-dev" to the real MCP server would fail JWT
    # validation. Fall back to mock so the real MCP server is not affected.
    if token == "local-dev":
        logger.info("XAA path — using in-process mock for Okta tool (no Entra token): %s", tool_name)
        return _mock_response(tool_name, args)

    logger.info("MCP Server — initiating connection to %s/mcp/call  tool=%s  args=%s", mcp_url, tool_name, args)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{mcp_url}/mcp/call",
                json={"tool": tool_name, "arguments": args},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
    except httpx.ConnectError as e:
        raise RuntimeError(
            f"Cannot reach MCP Server at {mcp_url} — is it running? ({e})"
        )
    except Exception as e:
        raise RuntimeError(f"MCP Server request failed for tool '{tool_name}': {e}")

    if not response.is_success:
        logger.error(
            "MCP Server returned HTTP %d for tool '%s': %s",
            response.status_code, tool_name, response.text,
        )
        raise RuntimeError(
            f"MCP Server rejected '{tool_name}' with HTTP {response.status_code}: {response.text}"
        )

    result = response.json()
    logger.info("MCP call ← tool=%s  status=ok", tool_name)
    return result
