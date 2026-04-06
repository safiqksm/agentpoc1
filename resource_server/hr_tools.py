# =============================================================================
# HR tool handlers — dispatched from main.py after token validation.
# Each handler receives the parsed "arguments" dict from the tool call request.
# =============================================================================

import logging
from fastapi import HTTPException
from hr_data import EMPLOYEES, DEPARTMENTS

logger = logging.getLogger(__name__)


async def get_employee_profile(args: dict) -> dict:
    """Return HR profile for a single employee by Okta user ID."""
    okta_user_id = args.get("okta_user_id")
    if not okta_user_id:
        raise HTTPException(status_code=400, detail="okta_user_id is required")
    employee = EMPLOYEES.get(okta_user_id)
    if not employee:
        raise HTTPException(
            status_code=404,
            detail=f"No HR record found for Okta user ID: {okta_user_id}",
        )
    return employee


async def list_departments(args: dict) -> list:
    """Return all departments with their employee counts."""
    return DEPARTMENTS


async def get_org_chart(args: dict) -> dict:
    """Return a manager's profile and their direct reports."""
    manager_id = args.get("okta_user_id")
    if not manager_id:
        raise HTTPException(status_code=400, detail="okta_user_id is required")
    manager = EMPLOYEES.get(manager_id)
    direct_reports = [
        emp for emp in EMPLOYEES.values()
        if emp.get("manager_id") == manager_id
    ]
    return {
        "manager":        manager or {"okta_user_id": manager_id, "note": "not in HR records"},
        "direct_reports": direct_reports,
    }


# Dispatch table — main.py uses this to route tool calls
HANDLERS: dict = {
    "get_employee_profile": get_employee_profile,
    "list_departments":     list_departments,
    "get_org_chart":        get_org_chart,
}


async def dispatch(tool_name: str, args: dict):
    handler = HANDLERS.get(tool_name)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
    logger.debug("Dispatching tool: %s args=%s", tool_name, args)
    return await handler(args)
