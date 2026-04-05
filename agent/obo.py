# =============================================================================
# STEP 4 — OBO (On-Behalf-Of) Token Exchange
#
# The Agent holds the user's incoming Bearer token (aud = agentpoc1-agent).
# OBO exchanges it for a new token scoped to the MCP Server (aud = agentpoc1-mcp)
# so the MCP Server can verify the original user's identity.
#
# OBO grant type: urn:ietf:params:oauth:grant-type:jwt-bearer
#
# Entra ID endpoint:
#   POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
#
# Required env vars (set in .env — see ENTRA_OBO_SETUP.md):
#   TENANT_ID            — Entra tenant ID
#   AGENT_CLIENT_ID      — agentpoc1-agent application (client) ID
#   AGENT_CLIENT_SECRET  — client secret added to agentpoc1-agent
#   MCP_APP_ID           — agentpoc1-mcp application (client) ID
#
# LOCAL DEV: if AGENT_CLIENT_SECRET is not set, OBO is skipped and the
# original token is passed through — so the app still works without Entra
# config (mock / echo mode).
#
# OWASP LLM08/AA05 — the client secret is short-lived and stored only in .env.
# In Azure production, replace with Managed Identity + certificate (no secret).
# =============================================================================

import os
import logging
from pathlib import Path
import httpx
from dotenv import load_dotenv
from jose import jwt as jose_jwt

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)


def _log_token_claims(label: str, token: str) -> None:
    """Decode (without verification) and log key claims for debugging."""
    try:
        claims = jose_jwt.decode(
            token, "", options={"verify_signature": False, "verify_aud": False, "verify_exp": False}
        )
        logger.info(
            "\n--- %s ---\n  aud : %s\n  scp : %s\n  sub : %s\n  exp : %s\n---",
            label,
            claims.get("aud", "?"),
            claims.get("scp", "?"),
            claims.get("sub", "?"),
            claims.get("exp", "?"),
        )
    except Exception:
        logger.info("--- %s --- (not a JWT or could not decode)", label)

# Entra ID token endpoint (v2.0)
_TOKEN_ENDPOINT = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"

# OBO grant type as defined in RFC 7523
_OBO_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"


async def exchange_obo_token(user_token: str) -> str:
    """
    STEP 4 — Exchange the user's Bearer token for an OBO token scoped
    to the MCP Server (agentpoc1-mcp).

    Returns the OBO access token string on success.
    Returns the original user_token unchanged if OBO is not configured
    (AGENT_CLIENT_SECRET missing) so local dev / mock mode still works.

    Raises RuntimeError if the exchange call fails with an error response.
    """
    tenant_id     = os.getenv("TENANT_ID")
    client_id     = os.getenv("AGENT_CLIENT_ID")
    client_secret = os.getenv("AGENT_CLIENT_SECRET")
    mcp_app_id    = os.getenv("MCP_APP_ID")

    # ── Local dev bypass ──────────────────────────────────────────────────
    # If OBO env vars are not configured, skip the exchange and pass the
    # original token through. The MCP Server accepts it in local dev mode.
    if not all([tenant_id, client_id, client_secret, mcp_app_id]):
        logger.warning(
            "STEP 4 — OBO not configured (missing env vars). "
            "Passing original token to MCP Server. "
            "Set TENANT_ID, AGENT_CLIENT_ID, AGENT_CLIENT_SECRET, MCP_APP_ID to enable OBO."
        )
        return user_token

    # ── OBO token exchange ────────────────────────────────────────────────
    # Scope: api://<MCP_APP_ID>/mcp.call — the MCP Server's exposed scope
    scope = f"api://{mcp_app_id}/mcp.call offline_access"

    token_url = _TOKEN_ENDPOINT.format(tenant=tenant_id)

    # Form-encoded body as required by the OBO grant spec
    body = {
        "grant_type":           _OBO_GRANT_TYPE,
        "client_id":            client_id,
        "client_secret":        client_secret,
        "assertion":            user_token,      # the incoming user Bearer token
        "scope":                scope,
        "requested_token_use":  "on_behalf_of",
    }

    logger.info("\n========== OBO: USER → MCP SERVER ==========")
    _log_token_claims("User token (incoming)", user_token)
    logger.info("  scope : %s", scope)

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            token_url,
            data=body,                           # form-encoded, not JSON
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != 200:
        error = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        raise RuntimeError(f"STEP 4 — OBO exchange failed ({response.status_code}): {error}")

    obo_token = response.json()["access_token"]
    _log_token_claims("OBO token (MCP Server)", obo_token)
    logger.info("========== OBO: USER → MCP SERVER — DONE ==========\n")
    return obo_token


async def exchange_obo_token_for_llm(user_token: str) -> str | None:
    """
    OBO for AI — Exchange the user's Bearer token for a token scoped to
    Azure Cognitive Services (Azure OpenAI).

    Returns the OBO access token string on success.
    Returns None if OBO env vars are not configured — caller falls back to API key.

    Raises RuntimeError if the exchange call fails with an error response.
    """
    tenant_id     = os.getenv("TENANT_ID")
    client_id     = os.getenv("AGENT_CLIENT_ID")
    client_secret = os.getenv("AGENT_CLIENT_SECRET")

    if not all([tenant_id, client_id, client_secret]):
        logger.warning(
            "OBO for AI — not configured (missing env vars). "
            "LLM will fall back to API key auth."
        )
        return None

    scope = "https://cognitiveservices.azure.com/.default"
    token_url = _TOKEN_ENDPOINT.format(tenant=tenant_id)

    body = {
        "grant_type":           _OBO_GRANT_TYPE,
        "client_id":            client_id,
        "client_secret":        client_secret,
        "assertion":            user_token,
        "scope":                scope,
        "requested_token_use":  "on_behalf_of",
    }

    logger.info("\n========== OBO FOR AI: USER → AZURE OPENAI ==========")
    _log_token_claims("User token (incoming)", user_token)
    logger.info("  scope : %s", scope)

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            token_url,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != 200:
        error = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
        raise RuntimeError(f"OBO for AI — exchange failed ({response.status_code}): {error}")

    llm_token = response.json()["access_token"]
    _log_token_claims("LLM token (Azure OpenAI)", llm_token)
    logger.info("========== OBO FOR AI: USER → AZURE OPENAI — DONE ==========\n")
    return llm_token
