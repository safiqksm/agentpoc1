# =============================================================================
# Okta Tool Handlers — executed by the MCP Server after token verification.
#
# Step 11 — each function maps to an Okta REST API call.
# Currently returns mock data; real Okta calls wired in Step 11 when
# the Okta client_credentials token (Step 10) is available.
#
# Okta API mapping:
#   list_users       → GET  /api/v1/users
#   get_user         → GET  /api/v1/users/{id}
#   create_user      → POST /api/v1/users
#   deactivate_user  → POST /api/v1/users/{id}/lifecycle/deactivate
#   get_group        → GET  /api/v1/groups/{id}
#   assign_app       → POST /api/v1/apps/{appId}/users
#   reset_mfa        → DELETE /api/v1/users/{id}/factors
# =============================================================================

import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

async def list_users(args: dict) -> list:
    limit = args.get("limit", 10)
    logger.info("list_users limit=%d", limit)
    # Step 11 (TODO): GET /api/v1/users?limit={limit} with Okta token
    return [
        {"id": "00u1abc", "login": "alice@example.com", "status": "ACTIVE"},
        {"id": "00u2def", "login": "bob@example.com",   "status": "ACTIVE"},
        {"id": "00u3ghi", "login": "carol@example.com", "status": "INACTIVE"},
    ][:limit]


async def get_user(args: dict) -> dict:
    user_id = args.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    logger.info("get_user id=%s", user_id)
    # Step 11 (TODO): GET /api/v1/users/{user_id}
    return {"id": user_id, "login": "alice@example.com", "firstName": "Alice", "lastName": "Smith", "status": "ACTIVE"}


async def create_user(args: dict) -> dict:
    email = args.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="email is required")
    logger.info("create_user email=%s", email)
    # Step 11 (TODO): POST /api/v1/users
    return {"id": "00u4new", "login": email, "firstName": args.get("first_name", ""), "lastName": args.get("last_name", ""), "status": "STAGED"}


async def deactivate_user(args: dict) -> dict:
    user_id = args.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    logger.info("deactivate_user id=%s", user_id)
    # Step 11 (TODO): POST /api/v1/users/{user_id}/lifecycle/deactivate
    return {"id": user_id, "status": "DEPROVISIONED"}


async def get_group(args: dict) -> dict:
    group_id = args.get("group_id")
    if not group_id:
        raise HTTPException(status_code=400, detail="group_id is required")
    logger.info("get_group id=%s", group_id)
    # Step 11 (TODO): GET /api/v1/groups/{group_id}
    return {"id": group_id, "profile": {"name": "Engineering", "description": "Engineering team"}}


async def assign_app(args: dict) -> dict:
    user_id = args.get("user_id")
    app_id  = args.get("app_id")
    if not user_id or not app_id:
        raise HTTPException(status_code=400, detail="user_id and app_id are required")
    logger.info("assign_app user=%s app=%s", user_id, app_id)
    # Step 11 (TODO): POST /api/v1/apps/{app_id}/users
    return {"id": "00a1assign", "user_id": user_id, "app_id": app_id, "status": "ACTIVE"}


async def reset_mfa(args: dict) -> dict:
    user_id = args.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    logger.info("reset_mfa user=%s", user_id)
    # Step 11 (TODO): DELETE /api/v1/users/{user_id}/factors
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
