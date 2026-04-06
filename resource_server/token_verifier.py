# =============================================================================
# HR Resource Server: XAA Token Validation
#
# Verifies the Bearer token sent by the Agent after the XAA two-step exchange.
# The token is issued by the Okta Custom Authorization Server (not Entra).
#
# Validation steps:
#   1. Fetch JWKS from Okta Custom AS (cached 1 hour)
#   2. Verify RS256 signature using the matching public key
#   3. Check claims: iss (Custom AS), aud (RESOURCE_AS_AUDIENCE), scp (hr.read), exp
#
# LOCAL DEV BYPASS:
#   If OKTA_DOMAIN or RESOURCE_AS_ID is not set, signature verification is
#   skipped so local curl tests work without Okta configuration.
#
# OWASP LLM08/AA05 mitigation — same as mcp_server/token_verifier.py:
#   - Signature check prevents token forgery
#   - aud check prevents tokens issued to other apps from being reused here
#   - scp check enforces delegated scope
#   - exp check prevents replay attacks with stale tokens
# =============================================================================

import os
import time
import logging
import httpx
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JWKS in-memory cache (same pattern as mcp_server/token_verifier.py)
# ---------------------------------------------------------------------------
_jwks_cache: dict | None = None
_jwks_fetched_at: float = 0.0
_JWKS_TTL_SECONDS = 3600


def _jwks_url() -> str:
    okta_domain   = os.getenv("OKTA_DOMAIN")
    resource_as_id = os.getenv("RESOURCE_AS_ID")
    # Okta Custom AS JWKS endpoint
    return f"{okta_domain}/oauth2/{resource_as_id}/v1/keys"


def _fetch_jwks() -> dict:
    """Fetch and cache the JWKS from the Okta Custom AS."""
    global _jwks_cache, _jwks_fetched_at

    now = time.monotonic()
    if _jwks_cache is not None and (now - _jwks_fetched_at) < _JWKS_TTL_SECONDS:
        return _jwks_cache

    url = _jwks_url()
    logger.info("Fetching JWKS from Okta Custom AS: %s", url)
    response = httpx.get(url, timeout=10.0)
    response.raise_for_status()

    _jwks_cache = response.json()
    _jwks_fetched_at = now
    logger.info("JWKS cache refreshed (%d keys)", len(_jwks_cache.get("keys", [])))
    return _jwks_cache


def verify_token(token: str) -> dict:
    """
    Verify the XAA access token forwarded by the Agent.

    Returns the decoded claims dict on success.
    Raises HTTPException(403) on any validation failure.

    LOCAL DEV BYPASS: if OKTA_DOMAIN or RESOURCE_AS_ID is not set,
    signature verification is skipped (same pattern as mcp_server).
    """
    okta_domain    = os.getenv("OKTA_DOMAIN")
    resource_as_id = os.getenv("RESOURCE_AS_ID")
    audience       = os.getenv("RESOURCE_AS_AUDIENCE", "http://localhost:8100")

    # ── Local dev bypass ──────────────────────────────────────────────────────
    if not all([okta_domain, resource_as_id]):
        logger.warning(
            "Token validation skipped (OKTA_DOMAIN or RESOURCE_AS_ID not set). "
            "Running in local dev mode — do NOT use this in production."
        )
        try:
            claims = jwt.decode(
                token,
                key="",
                options={"verify_signature": False, "verify_aud": False, "verify_exp": False},
            )
            logger.info(
                "[local-dev] Token claims — iss: %s  aud: %s  scp: %s",
                claims.get("iss", "?"), claims.get("aud", "?"), claims.get("scp", "?"),
            )
            return claims
        except Exception:
            return {"sub": "local-dev", "scp": "hr.read"}

    # ── Full JWT validation ───────────────────────────────────────────────────
    expected_issuer = f"{okta_domain}/oauth2/{resource_as_id}"

    try:
        jwks = _fetch_jwks()
        claims = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=audience,
            issuer=expected_issuer,
            options={"verify_exp": True},
        )

    except ExpiredSignatureError:
        logger.warning("Token rejected: expired")
        raise HTTPException(status_code=403, detail="Token has expired")

    except JWTError as exc:
        logger.warning("Token rejected: %s", exc)
        raise HTTPException(status_code=403, detail=f"Token validation failed: {exc}")

    except Exception as exc:
        logger.error("JWKS/token error: %s", exc)
        raise HTTPException(status_code=503, detail="Token validation service unavailable")

    # Verify scope — Okta may encode as space-separated string ("scp") or list ("scope")
    scp_str: str = claims.get("scp", "") or " ".join(claims.get("scope", []))
    if "hr.read" not in scp_str.split():
        logger.warning("Token rejected: missing hr.read scope (scp=%s)", scp_str)
        raise HTTPException(
            status_code=403,
            detail=f"Insufficient scope — required: hr.read, got: '{scp_str}'"
        )

    logger.info(
        "XAA token VALID:  sub=%s  scp=%s  aud=%s  iss=%s",
        claims.get("sub", "?"), scp_str, claims.get("aud", "?"), claims.get("iss", "?"),
    )
    return claims
