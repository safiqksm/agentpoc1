# =============================================================================
# XAA (Cross App Access / Identity Assertion Authorization Grant) Token Exchange
#
# Based on: https://developer.okta.com/blog/2026/02/10/xaa-client
#
# Two-step flow — Okta acts as the identity broker:
#
#   Step 1: POST /oauth2/v1/token  (Okta Org Authorization Server)
#     grant_type            = urn:ietf:params:oauth:grant-type:token-exchange
#     subject_token         = <Okta ID token from the user's OIDC login>
#     subject_token_type    = urn:ietf:params:oauth:token-type:id_token
#     requested_token_type  = urn:ietf:params:oauth:token-type:id-jag
#     audience              = <Custom AS issuer URL>
#     resource              = <Resource server URL>
#     scope                 = hr.read
#     client_id             = OKTA_AGENT_CLIENT_ID
#     client_secret         = OKTA_AGENT_CLIENT_SECRET
#     → returns: ID-JAG (Identity Assertion JWT)
#
#   Step 2: POST /oauth2/{RESOURCE_AS_ID}/v1/token  (Okta Custom AS)
#     grant_type            = urn:ietf:params:oauth:grant-type:jwt-bearer
#     assertion             = <ID-JAG from step 1>
#     scope                 = hr.read
#     client_id             = OKTA_AGENT_CLIENT_ID
#     client_secret         = OKTA_AGENT_CLIENT_SECRET
#     → returns: access token scoped to the HR Resource Server
#
# Client authentication: client_secret (simpler than private_key_jwt).
# In Okta admin, agentpoc1-agent-service must use "Client Secret" auth method.
#
# Required env vars:
#   OKTA_DOMAIN              — https://oie-8764513.oktapreview.com
#   OKTA_AGENT_CLIENT_ID     — agentpoc1-agent-service app client ID
#   OKTA_AGENT_CLIENT_SECRET — client secret from agentpoc1-agent-service app
#   OKTA_RESOURCE_AS_ID      — Custom AS ID (from issuer URI in Okta admin)
#   RESOURCE_SERVER_URL      — http://localhost:8100
# =============================================================================

import os
import logging
import httpx
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")
logger = logging.getLogger(__name__)

_TOKEN_LOG = Path(__file__).parent / "xaa_debug.txt"


def _xaa_log(section: str, detail: str) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] {section}\n{detail}\n{'-' * 72}\n"
    logger.debug("%s | %s", section, detail)
    with _TOKEN_LOG.open("a") as f:
        f.write(line)

# OAuth 2.0 grant type and token type URNs (RFC 8693 / Okta XAA)
_TOKEN_EXCHANGE_GRANT = "urn:ietf:params:oauth:grant-type:token-exchange"
_JWT_BEARER_GRANT     = "urn:ietf:params:oauth:grant-type:jwt-bearer"
_ID_TOKEN_TYPE        = "urn:ietf:params:oauth:token-type:id_token"
_ID_JAG_TYPE          = "urn:ietf:params:oauth:token-type:id-jag"


async def exchange_xaa_token(okta_id_token: str) -> str:
    """
    Perform the two-step XAA token exchange:
      1. Okta ID token  →  ID-JAG  (Org AS validates XAA trust policy)
      2. ID-JAG         →  resource server access token  (Custom AS issues hr.read token)

    Client authentication uses client_secret (not private_key_jwt).

    Returns the access token string for the HR Resource Server.
    Raises RuntimeError if config is missing or if either step fails.
    """
    okta_domain    = os.getenv("OKTA_DOMAIN", "").rstrip("/")
    client_id      = os.getenv("OKTA_AGENT_CLIENT_ID")
    client_secret  = os.getenv("OKTA_AGENT_CLIENT_SECRET")
    resource_as_id = os.getenv("OKTA_RESOURCE_AS_ID")
    resource_url   = os.getenv("RESOURCE_SERVER_URL", "http://localhost:8100")

    if not all([okta_domain, client_id, client_secret, resource_as_id]):
        raise RuntimeError(
            "XAA not fully configured. Set OKTA_DOMAIN, OKTA_AGENT_CLIENT_ID, "
            "OKTA_AGENT_CLIENT_SECRET, OKTA_RESOURCE_AS_ID in agent/.env"
        )

    org_token_endpoint    = f"{okta_domain}/oauth2/v1/token"
    custom_as_endpoint    = f"{okta_domain}/oauth2/{resource_as_id}/v1/token"
    custom_as_issuer      = f"{okta_domain}/oauth2/{resource_as_id}"

    # ── Step 1: ID token → ID-JAG ─────────────────────────────────────────────
    logger.info("XAA Step 1: exchanging Okta ID token for ID-JAG")

    step1_payload = {
        "grant_type":           _TOKEN_EXCHANGE_GRANT,
        "client_id":            client_id,
        "client_secret":        client_secret,
        "subject_token":        okta_id_token,
        "subject_token_type":   _ID_TOKEN_TYPE,
        "requested_token_type": _ID_JAG_TYPE,
        "audience":             custom_as_issuer,
        "scope":                "hr.read",
    }

    _xaa_log("=" * 72, "NEW XAA ATTEMPT")
    _xaa_log(
        "XAA Step 1 — FULL REQUEST BODY",
        f"url={org_token_endpoint}\n"
        f"grant_type={step1_payload['grant_type']}\n"
        f"client_id={step1_payload['client_id']}\n"
        f"subject_token_type={step1_payload['subject_token_type']}\n"
        f"requested_token_type={step1_payload['requested_token_type']}\n"
        f"audience={step1_payload['audience']}\n"
        f"scope={step1_payload['scope']}\n"
        f"subject_token (full):\n{okta_id_token}",
    )

    async with httpx.AsyncClient(timeout=10.0) as http:
        r1 = await http.post(
            org_token_endpoint,
            data=step1_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    _xaa_log(
        f"XAA Step 1 — RESPONSE HTTP {r1.status_code}",
        r1.text,
    )

    if r1.status_code != 200:
        raise RuntimeError(f"XAA Step 1 failed (HTTP {r1.status_code}): {r1.text}")

    step1_data = r1.json()
    id_jag = step1_data.get("access_token") or step1_data.get("issued_token")
    if not id_jag:
        raise RuntimeError(f"XAA Step 1: no token in response: {step1_data}")

    logger.info("XAA Step 1 complete — ID-JAG acquired")

    # ── Step 2: ID-JAG → resource server access token ─────────────────────────
    logger.info("XAA Step 2: exchanging ID-JAG for HR resource server token")
    _xaa_log(
        "XAA Step 2 — REQUEST to Custom AS",
        f"url={custom_as_endpoint}\n"
        f"client_id={client_id}\n"
        f"id_jag_prefix={id_jag[:40]}...  len={len(id_jag)}",
    )

    async with httpx.AsyncClient(timeout=10.0) as http:
        r2 = await http.post(
            custom_as_endpoint,
            data={
                "grant_type":    _JWT_BEARER_GRANT,
                "client_id":     client_id,
                "client_secret": client_secret,
                "assertion":     id_jag,
                "scope":         "hr.read",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    _xaa_log(
        f"XAA Step 2 — RESPONSE HTTP {r2.status_code}",
        r2.text,
    )

    if r2.status_code != 200:
        raise RuntimeError(f"XAA Step 2 failed (HTTP {r2.status_code}): {r2.text}")

    access_token = r2.json().get("access_token")
    if not access_token:
        raise RuntimeError(f"XAA Step 2: no access_token in response: {r2.json()}")

    logger.info("XAA Step 2 complete — HR resource server access token acquired")
    return access_token
