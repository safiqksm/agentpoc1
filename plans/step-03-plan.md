# Step 3 Plan — AI Agent Container: Orchestration + MCP Client

## Overview
This step transforms the simple FastAPI stub into a **real AI Agent** that can:
1. Receive a user prompt
2. Ask the LLM whether it needs to call a tool (Okta operation)
3. If yes → call the **MCP Server** via the MCP Client (Steps 5–12 wire up the real MCP Server; for now we use a **local stub**)
4. Feed the tool result back to the LLM
5. Return the final natural language response to the user

This is the **orchestration loop** — the agent reasons, acts, observes, and responds.

---

## The Agent Loop (ReAct Pattern)

```
User Prompt
    │
    ▼
LLM (with tool definitions) ──► "I need to call list_users"
    │
    ▼
MCP Client calls Tool (e.g. list_users)
    │
    ▼
Tool Result returned to LLM
    │
    ▼
LLM generates final response
    │
    ▼
Response → User
```

In Java terms: think of this as a **pipeline with a decision branch** — the LLM is the decision maker, the MCP Client is the executor.

---

## What We Are Building

Updates to `agent/`:

| File | Change |
|---|---|
| `orchestrator.py` | NEW — the agent loop (prompt → LLM → tool call → LLM → response) |
| `mcp_client.py` | NEW — MCP Client stub that calls the MCP Server (local stub for now) |
| `tools.py` | NEW — tool definitions exposed to the LLM (OpenAI function-calling format) |
| `main.py` | UPDATE — `POST /chat` calls `orchestrator.run()` instead of `call_llm()` directly |
| `llm.py` | UPDATE — add `call_llm_with_tools()` that supports function calling |
| `.env.example` | UPDATE — add `MCP_SERVER_URL` |

---

## Tool Definitions (Okta Operations)

These are the MCP tools exposed to the LLM. Defined in OpenAI function-calling format:

| Tool Name | Description | Parameters |
|---|---|---|
| `list_users` | List Okta users | `limit` (int, optional) |
| `get_user` | Get a specific Okta user | `user_id` (string) |
| `create_user` | Create a new Okta user | `first_name`, `last_name`, `email` |
| `deactivate_user` | Deactivate an Okta user | `user_id` |
| `get_group` | Get an Okta group | `group_id` |
| `assign_app` | Assign app to a user | `user_id`, `app_id` |
| `reset_mfa` | Reset MFA for a user | `user_id` |

The LLM decides **which tool to call and with what arguments** based on the user's prompt.

---

## Files to Create / Update

### `tools.py` — Tool definitions
Defines the tools in OpenAI function-calling JSON format so the LLM knows what's available.

```python
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_users",
            "description": "List users in Okta",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max number of users to return", "default": 10}
                }
            }
        }
    },
    # ... more tools
]
```

### `mcp_client.py` — MCP Client
Calls `POST {MCP_SERVER_URL}/mcp/call` with:
- Tool name + arguments
- `Authorization: Bearer <obo_token>` (OBO token added in Step 4; for now uses the incoming user token)

Returns the tool result JSON.

**Local stub behaviour:** if `MCP_SERVER_URL` is not set or call fails, returns mock data so the agent loop still works end-to-end locally.

### `orchestrator.py` — Agent Loop
```
1. Call LLM with user prompt + tool definitions
2. If LLM response contains a tool_call:
   a. Extract tool name + arguments
   b. Call mcp_client.call_tool(tool_name, args, token)
   c. Append tool result to message history
   d. Call LLM again with updated history
3. Return final LLM text response
```

### `llm.py` updates
Add `call_llm_with_tools(messages, tools)` — passes the tool definitions to the OpenAI API and returns either a text response or a `tool_call` decision.

### `main.py` updates
`POST /chat` calls `orchestrator.run(prompt, token)` instead of `call_llm(prompt)` directly.

---

## Session Management (POC scope)

For this POC, **session state is in-memory per request** (stateless). Each `POST /chat` is a fresh conversation turn. Multi-turn session persistence is out of scope.

---

## Local MCP Stub Behaviour

Since the real MCP Server (Steps 5–12) isn't built yet, `mcp_client.py` returns **mock responses**:

| Tool | Mock Response |
|---|---|
| `list_users` | `[{"id": "00u1", "login": "alice@example.com"}, {"id": "00u2", "login": "bob@example.com"}]` |
| `get_user` | `{"id": "<user_id>", "login": "alice@example.com", "status": "ACTIVE"}` |
| `create_user` | `{"id": "00u3", "login": "<email>", "status": "STAGED"}` |
| `deactivate_user` | `{"id": "<user_id>", "status": "DEPROVISIONED"}` |
| `get_group` | `{"id": "<group_id>", "profile": {"name": "Engineering"}}` |

The mock is swapped for a real MCP HTTP call in Step 5.

---

## Updated `.env.example` additions

```
# MCP Server (local stub until Step 5)
MCP_SERVER_URL=http://localhost:9000
```

---

## OWASP Risk: LLM06 / AA03 — Excessive Agency

**Risk:** The agent has real delegated power (can create/deactivate users). If the LLM is manipulated via prompt injection, it could call destructive tools.

**Mitigations at this layer:**
- Tool list is **hardcoded** — the LLM can only call tools we explicitly define, not arbitrary functions
- Tool arguments are **validated** before being passed to the MCP client
- Destructive tools (`deactivate_user`, `reset_mfa`) log a warning and require explicit confirmation intent in the prompt (checked in orchestrator)

---

## Success Criteria for Step 3

- [ ] `POST /chat` with `"List all Okta users"` → LLM calls `list_users` tool → returns mock user list in natural language
- [ ] `POST /chat` with `"What is 2+2?"` → LLM answers directly without calling any tool
- [ ] `POST /chat/echo` still works unchanged
- [ ] Tool call arguments are logged to console for visibility
- [ ] If `MCP_SERVER_URL` is not set, mock data is used and a warning is logged

---

## Out of Scope for This Step

- OBO token exchange (Step 4) — user token passed as-is for now
- Real MCP Server HTTP call (Step 5)
- APIM (Step 6)
- Multi-turn session memory

---

## Next Step
**Step 4** — OBO token exchange: Agent uses Managed Identity + App Registration certificate to exchange the user's incoming token for a delegated OBO token scoped to APIM/MCP.
