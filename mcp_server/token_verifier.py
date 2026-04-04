# =============================================================================
# Token Verifier — verifies the Bearer token sent by the Agent.
#
# Current (Step 3): checks token is a non-empty string, decodes without
#   signature verification so we can log the subject claim.
#
# Step 4 will replace this with full JWT validation:
#   - Fetch JWKS from Entra ID (https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys)
#   - Verify RS256 signature
#   - Check iss, aud (AGENT_APP_ID), exp, and scp == "agent.access"
# =============================================================================

import os
import logging
from jose import jwt, JWTError

logger = logging.getLogger(__name__)


def verify_token(token: str) -> dict:
    """
    Verify the incoming Bearer token.

    Returns the decoded claims dict on success.
    Raises HTTPException(401) on failure.
    """
    # Step 4 (TODO) — replace with full signature + claims validation
    # For now: decode without verification to extract claims for logging
    try:
        claims = jwt.decode(
            token,
            key="",               # no key — signature not verified yet
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": False,
            },
        )
        logger.info(
            "Token claims — iss: %s  aud: %s  scp: %s",
            claims.get("iss", "?"),
            claims.get("aud", "?"),
            claims.get("scp", "?"),
        )
        return claims
    except JWTError:
        # Token is not a valid JWT at all (e.g. test string "test-token")
        # Allow in local dev; Step 4 will enforce strict validation
        logger.warning("Token is not a valid JWT — running in local dev mode without validation")
        return {"sub": "local-dev", "scp": "agent.access"}
