# =============================================================================
# STEP 8 — Okta Token Acquisition (private_key_jwt / client_credentials)
#
# The MCP Server authenticates to Okta using private_key_jwt:
#   1. Build a short-lived client_assertion JWT signed with the local private key
#   2. POST to /oauth2/v1/token with client_credentials grant
#   3. Cache the resulting Okta access token until it expires
#
# Why private_key_jwt?
#   Okta's Org Authorization Server (the only AS that can issue okta.* management
#   scopes) requires private_key_jwt — client_secret is not accepted there.
#
# Local key files (POC):
#   okta_private.pem — signs the client_assertion JWT
#   okta_public.pem  — uploaded to the Okta app registration (public key store)
#
# Production upgrade: replace local .pem with Azure Key Vault + Managed Identity.
#
# Required env vars:
#   OKTA_DOMAIN           — https://oie-8764513.oktapreview.com
#   OKTA_CLIENT_ID        — agentpoc1-mcp-service app client ID
#   OKTA_PRIVATE_KEY_PATH — path to okta_private.pem (relative to mcp_server/)
#   OKTA_PRIVATE_KEY_KID  — Key ID assigned by Okta when the public key was uploaded
# =============================================================================

import os
import time
import uuid
import logging
import httpx
from jose import jwt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Okta management API scopes requested by this service
# ---------------------------------------------------------------------------
_OKTA_SCOPES = " ".join([
    "okta.users.read",
    "okta.users.manage",
    "okta.groups.read",
    "okta.apps.manage",
    "okta.factors.manage",
])

# ---------------------------------------------------------------------------
# In-memory token cache
# Java analogy: a static volatile field updated by a synchronized refresh method
# ---------------------------------------------------------------------------
_cached_token: str | None = None
_token_expires_at: float = 0.0          # monotonic clock seconds
_TOKEN_EXPIRY_BUFFER = 60               # refresh 60 s before actual expiry
_last_token_info: dict = {}             # debug: last acquired token's key fields


def _token_endpoint(okta_domain: str) -> str:
    # STEP 8 — Org Authorization Server token endpoint (issues okta.* scopes)
    return f"{okta_domain}/oauth2/v1/token"


def _build_client_assertion(okta_domain: str, client_id: str, kid: str, private_key_pem: str) -> str:
    """
    STEP 8 — Build and sign a client_assertion JWT.

    Okta verifies this JWT against the public key uploaded to the app registration.
    The assertion is valid for 5 minutes — enough for one token exchange.

    Java analogy: like building a signed SAML assertion in Spring Security SAML,
    but simpler — just a JSON payload signed with RS256.
    """
    now = int(time.time())
    payload = {
        "iss": client_id,                        # issuer = our client ID
        "sub": client_id,                        # subject = our client ID
        "aud": _token_endpoint(okta_domain),     # audience = Okta token endpoint
        "iat": now,                              # issued at
        "exp": now + 300,                        # expires in 5 minutes
        "jti": str(uuid.uuid4()),               # unique ID — prevents replay
    }
    headers = {
        "alg": "RS256",
        "kid": kid,                              # key ID Okta uses to look up the public key
    }
    return jwt.encode(payload, private_key_pem, algorithm="RS256", headers=headers)


async def get_okta_token() -> str:
    """
    STEP 8 — Return a valid Okta access token, fetching a new one if the cache
    has expired. Raises RuntimeError if configuration is missing or Okta rejects
    the request.

    Called by okta_tools.py before every Okta Management API call.
    """
    global _cached_token, _token_expires_at

    # ── Return cached token if still fresh ───────────────────────────────────
    if _cached_token and time.monotonic() < _token_expires_at:
        return _cached_token

    # ── Read configuration ────────────────────────────────────────────────────
    okta_domain  = os.getenv("OKTA_DOMAIN")
    client_id    = os.getenv("OKTA_CLIENT_ID")
    key_path     = os.getenv("OKTA_PRIVATE_KEY_PATH", "./okta_private.pem")
    kid          = os.getenv("OKTA_PRIVATE_KEY_KID")

    if not all([okta_domain, client_id, kid]):
        raise RuntimeError(
            "STEP 8 — Okta config incomplete. "
            "Set OKTA_DOMAIN, OKTA_CLIENT_ID, OKTA_PRIVATE_KEY_KID in .env"
        )

    # ── Load private key ──────────────────────────────────────────────────────
    try:
        with open(key_path, "r") as f:
            private_key_pem = f.read()
    except FileNotFoundError:
        raise RuntimeError(
            f"STEP 8 — Private key not found at '{key_path}'. "
            "Run: openssl genrsa -out okta_private.pem 2048  (see OKTA_SETUP.md)"
        )

    # ── Build signed client_assertion ─────────────────────────────────────────
    client_assertion = _build_client_assertion(okta_domain, client_id, kid, private_key_pem)

    # ── Call Okta token endpoint ──────────────────────────────────────────────
    logger.info("STEP 8 — Acquiring Okta token (client_credentials + private_key_jwt)")

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            _token_endpoint(okta_domain),
            data={
                "grant_type":            "client_credentials",
                "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
                "client_assertion":      client_assertion,
                "scope":                 _OKTA_SCOPES,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if response.status_code != 200:
        error = response.json() if "application/json" in response.headers.get("content-type", "") else response.text
        raise RuntimeError(f"STEP 8 — Okta token request failed ({response.status_code}): {error}")

    data = response.json()
    _cached_token    = data["access_token"]
    expires_in       = data.get("expires_in", 3600)
    _token_expires_at = time.monotonic() + expires_in - _TOKEN_EXPIRY_BUFFER

    _last_token_info.update({
        "sub":    client_id,
        "scope":  data.get("scope", _OKTA_SCOPES),
        "aud":    _token_endpoint(okta_domain),
        "cached": False,
        "expires_in": expires_in,
    })

    logger.info("STEP 8 — Okta token acquired (expires_in=%ds)", expires_in)
    return _cached_token


def get_last_token_info() -> dict:
    """Return key fields of the last acquired Okta token (debug only)."""
    if not _last_token_info:
        return {"status": "not yet acquired (no tool call made yet)"}
    return _last_token_info


def is_configured() -> bool:
    """Return True if all Okta env vars are present — used by okta_tools.py to
    decide whether to call the real API or fall back to mock data."""
    return all([
        os.getenv("OKTA_DOMAIN"),
        os.getenv("OKTA_CLIENT_ID"),
        os.getenv("OKTA_PRIVATE_KEY_KID"),
    ])
