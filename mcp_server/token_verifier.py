# =============================================================================
# STEP 5 — MCP Server: Full OBO Token Validation
#
# Verifies the Bearer token sent by the Agent after the OBO exchange (Step 4).
#
# Validation steps:
#   1. Fetch JWKS from Entra ID (cached 1 hour — not per-request)
#   2. Verify RS256 signature using the matching public key
#   3. Check claims: iss, aud (MCP_APP_ID), scp (mcp.call), exp
#
# LOCAL DEV BYPASS:
#   If MCP_APP_ID or TENANT_ID is not set, signature verification is skipped
#   so the mock / echo flow still works without Entra config.
#
# OWASP LLM08/AA05 mitigation:
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
# JWKS in-memory cache
# Analogous to a Java static field lazily initialised on first use.
# ---------------------------------------------------------------------------
_jwks_cache: dict | None = None       # cached JWKS key set
_jwks_fetched_at: float = 0.0         # epoch seconds when cache was last filled
_JWKS_TTL_SECONDS = 3600              # refresh JWKS once per hour


def _jwks_url(tenant_id: str) -> str:
    # STEP 5 — Entra ID JWKS endpoint for the tenant
    return f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"


def _expected_issuers(tenant_id: str) -> list[str]:
    # Entra issues v1.0 tokens (sts.windows.net) when the app manifest has
    # accessTokenAcceptedVersion=null/1, and v2.0 tokens (login.microsoftonline.com)
    # when accessTokenAcceptedVersion=2.  Accept both so either config works.
    return [
        f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        f"https://sts.windows.net/{tenant_id}/",
    ]


def _fetch_jwks(tenant_id: str) -> dict:
    """
    STEP 5 — Fetch the JWKS from Entra ID and return the key set.
    Synchronous HTTP call — called at startup or when cache expires.
    Analogous to a Java @PostConstruct method that fetches a public key store.
    """
    global _jwks_cache, _jwks_fetched_at

    now = time.monotonic()
    if _jwks_cache is not None and (now - _jwks_fetched_at) < _JWKS_TTL_SECONDS:
        return _jwks_cache                   # still fresh — return cached copy

    url = _jwks_url(tenant_id)
    logger.info("STEP 5 — Fetching JWKS from %s", url)
    response = httpx.get(url, timeout=10.0)
    response.raise_for_status()

    _jwks_cache = response.json()
    _jwks_fetched_at = now
    logger.info("STEP 5 — JWKS cache refreshed (%d keys)", len(_jwks_cache.get("keys", [])))
    return _jwks_cache


def verify_token(token: str) -> dict:
    """
    STEP 5 — Verify the OBO token forwarded by the Agent.

    Returns the decoded claims dict on success.
    Raises HTTPException(403) on any validation failure.

    LOCAL DEV BYPASS: if MCP_APP_ID or TENANT_ID is not set in the environment,
    signature verification is skipped and a stub claims dict is returned.
    This keeps the mock / local dev flow working without Entra config.
    """
    tenant_id  = os.getenv("TENANT_ID")
    mcp_app_id = os.getenv("MCP_APP_ID")

    # ── Local dev bypass ──────────────────────────────────────────────────────
    # Java analogy: like an @Profile("local") bean that swaps out the real impl.
    if not all([tenant_id, mcp_app_id]):
        logger.warning(
            "STEP 5 — Token validation skipped (TENANT_ID or MCP_APP_ID not set). "
            "Running in local dev mode — do NOT use this in production."
        )
        # Still try to decode for claim logging; ignore any errors
        try:
            claims = jwt.decode(
                token,
                key="",
                options={"verify_signature": False, "verify_aud": False, "verify_exp": False},
            )
            logger.info(
                "STEP 5 [local-dev] Token claims — iss: %s  aud: %s  scp: %s",
                claims.get("iss", "?"),
                claims.get("aud", "?"),
                claims.get("scp", "?"),
            )
            return claims
        except Exception:
            return {"sub": "local-dev", "scp": "mcp.call"}

    # ── Full JWT validation ───────────────────────────────────────────────────

    expected_audience = f"api://{mcp_app_id}"

    try:
        jwks = _fetch_jwks(tenant_id)

        # Try each accepted issuer (v1.0 and v2.0) — use whichever matches
        last_exc: Exception | None = None
        claims = None
        for issuer in _expected_issuers(tenant_id):
            try:
                claims = jwt.decode(
                    token,
                    jwks,
                    algorithms=["RS256"],
                    audience=expected_audience,
                    issuer=issuer,
                    options={"verify_exp": True},
                )
                logger.info("STEP 5 — Token accepted with issuer: %s", issuer)
                break
            except ExpiredSignatureError:
                raise   # expired is definitive — no point trying other issuers
            except JWTError as e:
                last_exc = e

        if claims is None:
            raise last_exc  # none of the issuers matched

    except ExpiredSignatureError:
        logger.warning("STEP 5 — Token rejected: expired")
        raise HTTPException(status_code=403, detail="Token has expired")

    except JWTError as exc:
        logger.warning("STEP 5 — Token rejected: %s", exc)
        raise HTTPException(status_code=403, detail=f"Token validation failed: {exc}")

    except Exception as exc:
        # JWKS fetch failure or unexpected error
        logger.error("STEP 5 — JWKS/token error: %s", exc)
        raise HTTPException(status_code=503, detail="Token validation service unavailable")

    # STEP 5 — scp claim: must contain "mcp.call"
    # Entra encodes scopes as a space-separated string, e.g. "mcp.call offline_access"
    scp: str = claims.get("scp", "")
    if "mcp.call" not in scp.split():
        logger.warning(
            "STEP 5 — Token rejected: missing mcp.call scope (scp=%s)", scp
        )
        raise HTTPException(
            status_code=403,
            detail=f"Insufficient scope — required: mcp.call, got: '{scp}'"
        )

    logger.info(
        "STEP 5 — OBO token VALID:  sub=%s  scp=%s  aud=%s  iss=%s",
        claims.get("sub", "?"),
        scp,
        claims.get("aud", "?"),
        claims.get("iss", "?"),
    )
    return claims
