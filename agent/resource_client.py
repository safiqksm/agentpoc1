# =============================================================================
# HR Resource Client — Agent calls the HR Resource Server via XAA token.
#
# The agent forwards the XAA access token acquired by xaa.py.
# Token verification is done inside the HR Resource Server.
#
# Two modes (controlled by RESOURCE_SERVER_URL in .env):
#   1. RESOURCE_SERVER_URL not set → in-process mock (no network call)
#   2. RESOURCE_SERVER_URL=http://localhost:8100 → local HR Resource Server
#
# The mock data mirrors resource_server/hr_data.py so local dev works without
# the resource server process running.
# =============================================================================

import os
import logging
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-process mock — used when RESOURCE_SERVER_URL is not set.
# ---------------------------------------------------------------------------
_MOCK_EMPLOYEES = {
    "00u1abc": {"okta_user_id": "00u1abc", "email": "alice@example.com",
                "first_name": "Alice", "last_name": "Smith",
                "department": "Engineering", "title": "Senior Software Engineer",
                "manager_id": "00u2def", "location": "San Francisco"},
    "00u2def": {"okta_user_id": "00u2def", "email": "bob@example.com",
                "first_name": "Bob", "last_name": "Jones",
                "department": "Engineering", "title": "Engineering Manager",
                "manager_id": None, "location": "San Francisco"},
    "00u3ghi": {"okta_user_id": "00u3ghi", "email": "carol@example.com",
                "first_name": "Carol", "last_name": "White",
                "department": "HR", "title": "HR Business Partner",
                "manager_id": None, "location": "New York"},
}

_MOCK_DEPARTMENTS = [
    {"id": "engineering", "name": "Engineering", "head_count": 42},
    {"id": "hr",          "name": "HR",          "head_count": 8},
    {"id": "sales",       "name": "Sales",       "head_count": 23},
    {"id": "product",     "name": "Product",     "head_count": 12},
]

MOCK_RESPONSES = {
    "get_employee_profile": lambda a: _MOCK_EMPLOYEES.get(
        a.get("okta_user_id", ""),
        {"error": f"No HR record for {a.get('okta_user_id', '?')}"}
    ),
    "list_departments":     lambda _: _MOCK_DEPARTMENTS,
    "get_org_chart":        lambda a: {
        "manager":        _MOCK_EMPLOYEES.get(a.get("okta_user_id"), {}),
        "direct_reports": [e for e in _MOCK_EMPLOYEES.values()
                           if e.get("manager_id") == a.get("okta_user_id")],
    },
}


def _mock_response(tool_name: str, args: dict) -> dict:
    mock = MOCK_RESPONSES.get(tool_name)
    if mock is None:
        return {"error": f"Unknown tool: {tool_name}"}
    return mock(args)


# ---------------------------------------------------------------------------
# Resource server tool call — HTTP to HR Resource Server, token forwarded.
# ---------------------------------------------------------------------------
async def call_resource_tool(tool_name: str, args: dict, token: str | None) -> dict:
    """
    POST /tools/call to the HR Resource Server with the XAA Bearer token.
    The Resource Server is responsible for verifying the token.

    Uses in-process mock if RESOURCE_SERVER_URL is not set.
    """
    resource_url = os.getenv("RESOURCE_SERVER_URL")

    if not resource_url:
        logger.warning("RESOURCE_SERVER_URL not set — using in-process mock for: %s", tool_name)
        return _mock_response(tool_name, args)

    if not token:
        logger.warning(
            "No XAA token available for tool '%s' — XAA exchange likely failed. "
            "Falling back to in-process mock.", tool_name
        )
        return _mock_response(tool_name, args)

    logger.info("Resource Server — calling %s/tools/call  tool=%s  args=%s",
                resource_url, tool_name, args)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{resource_url}/tools/call",
                json={"tool": tool_name, "arguments": args},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
    except httpx.ConnectError as e:
        raise RuntimeError(
            f"Cannot reach HR Resource Server at {resource_url} — is it running? ({e})"
        )
    except Exception as e:
        raise RuntimeError(f"Resource Server request failed for tool '{tool_name}': {e}")

    if not response.is_success:
        logger.error(
            "Resource Server returned HTTP %d for tool '%s': %s",
            response.status_code, tool_name, response.text,
        )
        raise RuntimeError(
            f"Resource Server rejected '{tool_name}' with HTTP {response.status_code}: {response.text}"
        )

    result = response.json()
    logger.info("Resource call ← tool=%s  status=ok", tool_name)
    return result
