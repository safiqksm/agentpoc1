# =============================================================================
# STEP 11 — Okta Tool Handlers: real Okta Management API calls
#
# Each function maps to one Okta REST endpoint.
# okta_client.get_okta_token() provides the Bearer token (Step 8).
#
# LOCAL DEV FALLBACK:
#   If OKTA_CLIENT_ID / OKTA_PRIVATE_KEY_KID are not set, each handler returns
#   mock data so the full local dev flow still works without an Okta tenant.
#
# Okta API reference: https://developer.okta.com/docs/reference/api/users/
# =============================================================================

import os
import logging
import httpx
from fastapi import HTTPException
from okta_client import get_okta_token, is_configured

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _okta_base() -> str:
    return os.getenv("OKTA_DOMAIN", "").rstrip("/")


async def _okta_headers() -> dict:
    """STEP 8 — Build auth headers using the cached Okta token."""
    token = await get_okta_token()
    return {
        "Authorization": f"Bearer {token}",
        "Accept":        "application/json",
        "Content-Type":  "application/json",
    }


async def _okta_get(path: str) -> dict | list:
    """GET {OKTA_DOMAIN}{path} and return parsed JSON. Raises HTTPException on error."""
    url = f"{_okta_base()}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, headers=await _okta_headers())
    _raise_for_okta_error(r, path)
    return r.json()


async def _okta_post(path: str, body: dict | None = None) -> dict:
    url = f"{_okta_base()}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(url, headers=await _okta_headers(), json=body or {})
    _raise_for_okta_error(r, path)
    return r.json() if r.content else {}


async def _okta_put(path: str, body: dict | None = None) -> dict:
    url = f"{_okta_base()}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.put(url, headers=await _okta_headers(), json=body or {})
    _raise_for_okta_error(r, path)
    return r.json() if r.content else {}


async def _okta_delete(path: str) -> None:
    url = f"{_okta_base()}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.delete(url, headers=await _okta_headers())
    _raise_for_okta_error(r, path)


def _raise_for_okta_error(response: httpx.Response, path: str) -> None:
    if response.status_code < 400:
        return
    try:
        detail = response.json()
    except Exception:
        detail = response.text
    logger.error("Okta API error %s %s: %s", response.status_code, path, detail)
    raise HTTPException(status_code=response.status_code, detail=detail)


# ---------------------------------------------------------------------------
# Mock responses (local dev fallback — used when Okta is not configured)
# ---------------------------------------------------------------------------

_MOCK_USERS = [
    {"id": "00u1abc", "login": "alice@example.com", "status": "ACTIVE",
     "profile": {"firstName": "Alice", "lastName": "Smith", "email": "alice@example.com"}},
    {"id": "00u2def", "login": "bob@example.com",   "status": "ACTIVE",
     "profile": {"firstName": "Bob",   "lastName": "Jones", "email": "bob@example.com"}},
    {"id": "00u3ghi", "login": "carol@example.com", "status": "INACTIVE",
     "profile": {"firstName": "Carol", "lastName": "White", "email": "carol@example.com"}},
]


# ---------------------------------------------------------------------------
# STEP 11 — Tool handlers
# ---------------------------------------------------------------------------

async def list_users(args: dict) -> list:
    limit = int(args.get("limit", 25))
    logger.info("list_users limit=%d", limit)

    if not is_configured():
        logger.warning("Okta not configured — returning mock users")
        return _MOCK_USERS[:limit]

    # STEP 11 — GET /api/v1/users?limit={limit}&filter=status eq "ACTIVE"
    result = await _okta_get(f"/api/v1/users?limit={limit}")
    return result


async def get_user(args: dict) -> dict:
    user_id = args.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    logger.info("get_user id=%s", user_id)

    if not is_configured():
        logger.warning("Okta not configured — returning mock user")
        return _MOCK_USERS[0] | {"id": user_id}

    # STEP 11 — GET /api/v1/users/{user_id}
    return await _okta_get(f"/api/v1/users/{user_id}")


async def create_user(args: dict) -> dict:
    email      = args.get("email")
    first_name = args.get("first_name", "")
    last_name  = args.get("last_name", "")
    if not email:
        raise HTTPException(status_code=400, detail="email is required")
    logger.info("create_user email=%s", email)

    if not is_configured():
        logger.warning("Okta not configured — returning mock created user")
        return {"id": "00u4new", "login": email, "status": "STAGED",
                "profile": {"firstName": first_name, "lastName": last_name, "email": email}}

    # STEP 11 — POST /api/v1/users?activate=true
    body = {
        "profile": {
            "firstName": first_name,
            "lastName":  last_name,
            "email":     email,
            "login":     email,
        }
    }
    return await _okta_post("/api/v1/users?activate=true", body)


async def deactivate_user(args: dict) -> dict:
    user_id = args.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    logger.info("deactivate_user id=%s", user_id)

    if not is_configured():
        logger.warning("Okta not configured — returning mock deactivated user")
        return {"id": user_id, "status": "DEPROVISIONED"}

    # STEP 11 — POST /api/v1/users/{user_id}/lifecycle/deactivate
    await _okta_post(f"/api/v1/users/{user_id}/lifecycle/deactivate")
    return {"id": user_id, "status": "DEPROVISIONED"}


async def get_group(args: dict) -> dict:
    group_id = args.get("group_id")
    if not group_id:
        raise HTTPException(status_code=400, detail="group_id is required")
    logger.info("get_group id=%s", group_id)

    if not is_configured():
        logger.warning("Okta not configured — returning mock group")
        return {"id": group_id, "profile": {"name": "Engineering", "description": "Engineering team"}}

    # STEP 11 — GET /api/v1/groups/{group_id}
    return await _okta_get(f"/api/v1/groups/{group_id}")


async def assign_app(args: dict) -> dict:
    user_id = args.get("user_id")
    app_id  = args.get("app_id")
    if not user_id or not app_id:
        raise HTTPException(status_code=400, detail="user_id and app_id are required")
    logger.info("assign_app user=%s app=%s", user_id, app_id)

    if not is_configured():
        logger.warning("Okta not configured — returning mock app assignment")
        return {"id": "00a1assign", "user_id": user_id, "app_id": app_id, "status": "ACTIVE"}

    # STEP 11 — POST /api/v1/apps/{app_id}/users
    body = {"id": user_id}
    return await _okta_post(f"/api/v1/apps/{app_id}/users", body)


async def reset_mfa(args: dict) -> dict:
    user_id = args.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    logger.info("reset_mfa user=%s", user_id)

    if not is_configured():
        logger.warning("Okta not configured — returning mock MFA reset")
        return {"user_id": user_id, "factors_reset": True}

    # STEP 11 — DELETE /api/v1/users/{user_id}/factors  (removes all enrolled factors)
    await _okta_delete(f"/api/v1/users/{user_id}/factors")
    return {"user_id": user_id, "factors_reset": True}


# ---------------------------------------------------------------------------
# Dispatcher — routes tool name → handler function
# ---------------------------------------------------------------------------
HANDLERS = {
    "list_users":       list_users,
    "get_user":         get_user,
    "create_user":      create_user,
    "deactivate_user":  deactivate_user,
    "get_group":        get_group,
    "assign_app":       assign_app,
    "reset_mfa":        reset_mfa,
}


async def dispatch(tool_name: str, args: dict):
    handler = HANDLERS.get(tool_name)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
    return await handler(args)
