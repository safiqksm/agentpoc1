# =============================================================================
# STEP 3 — Tool catalogue: Okta operations the LLM can invoke.
#
# These are passed to the LLM in every call (Step 13 — call_llm_with_tools).
# The LLM reads the "description" fields to decide which tool matches the
# user's intent and what arguments to supply.
#
# STEP 11 — Each tool maps to an Okta REST API call executed by the MCP Server:
#   list_users      → GET  /api/v1/users
#   get_user        → GET  /api/v1/users/{id}
#   create_user     → POST /api/v1/users
#   deactivate_user → POST /api/v1/users/{id}/lifecycle/deactivate
#   get_group       → GET  /api/v1/groups/{id}
#   assign_app      → POST /api/v1/apps/{appId}/users
#   reset_mfa       → DELETE /api/v1/users/{id}/factors
#
# OWASP LLM06/AA03 — The LLM can only call tools explicitly listed here.
# It cannot invoke arbitrary functions or access unlisted APIs.
# =============================================================================

# STEP 3 — Tool definitions in OpenAI function-calling format
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_users",
            "description": "List users in Okta",           # LLM reads this to match user intent
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of users to return (default 10)",
                    }
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user",
            "description": "Get details of a specific Okta user by their user ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The Okta user ID",
                    }
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_user",
            "description": "Create a new user in Okta",
            "parameters": {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "email": {"type": "string", "description": "Login email address"},
                },
                "required": ["first_name", "last_name", "email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deactivate_user",
            # OWASP LLM06 — destructive; guarded in orchestrator (DESTRUCTIVE_TOOLS check)
            "description": "Deactivate an Okta user account",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "The Okta user ID to deactivate"}
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_group",
            "description": "Get details of an Okta group by group ID",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_id": {"type": "string", "description": "The Okta group ID"}
                },
                "required": ["group_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assign_app",
            "description": "Assign an application to an Okta user",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string"},
                    "app_id": {"type": "string", "description": "The Okta application ID"},
                },
                "required": ["user_id", "app_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reset_mfa",
            # OWASP LLM06 — destructive; guarded in orchestrator (DESTRUCTIVE_TOOLS check)
            "description": "Reset all MFA factors for an Okta user",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "The Okta user ID"}
                },
                "required": ["user_id"],
            },
        },
    },
    # ── HR Resource Server tools (accessed via XAA token, not MCP/OBO) ────────
    {
        "type": "function",
        "function": {
            "name": "get_employee_profile",
            "description": (
                "Get the HR employee profile (department, job title, manager, location) "
                "for an Okta user. Use after looking up the user's Okta ID."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "okta_user_id": {
                        "type": "string",
                        "description": "The Okta user ID (e.g. 00u1abc)",
                    }
                },
                "required": ["okta_user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_departments",
            "description": "List all company departments with their employee counts.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_org_chart",
            "description": (
                "Get the direct reports for a manager, identified by their Okta user ID. "
                "Returns the manager's HR profile and a list of their direct reports."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "okta_user_id": {
                        "type": "string",
                        "description": "The Okta user ID of the manager",
                    }
                },
                "required": ["okta_user_id"],
            },
        },
    },
]

# STEP 3 — OWASP LLM06/AA03: tools that require explicit destructive intent
# in the user's prompt before the orchestrator will allow them to execute.
DESTRUCTIVE_TOOLS = {"deactivate_user", "reset_mfa"}

# Tools that route to the HR Resource Server via XAA token (not to MCP via OBO).
RESOURCE_SERVER_TOOLS = {"get_employee_profile", "list_departments", "get_org_chart"}
