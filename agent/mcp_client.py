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
import httpx

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

    Falls back to in-process mock if MCP_SERVER_URL is not set or call fails.
    """
    mcp_url = os.getenv("MCP_SERVER_URL")

    if not mcp_url:
        logger.warning("MCP_SERVER_URL not set — using in-process mock for: %s", tool_name)
        return _mock_response(tool_name, args)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{mcp_url}/mcp/call",
                json={"tool": tool_name, "arguments": args},
                headers={
                    # Token forwarded directly — MCP Server verifies it
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.warning("MCP Server call failed (%s) — falling back to mock: %s", tool_name, e)
        return _mock_response(tool_name, args)
