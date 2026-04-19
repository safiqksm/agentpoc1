# OBO for AI — Implementation Plan

## What Changes

Currently the agent calls Azure OpenAI with an **API key** (service identity).
After this change it will call Azure OpenAI with a **user OBO token** so Azure
sees the real user identity on every LLM call.

---

## Azure Portal Prerequisites (do these first)

### 1 — Entra: grant Cognitive Services permission to the agent app

```
Entra portal
  → App registrations
  → agentpoc1-agent  (6b114879-c58c-4889-9355-d5d9b19647a7)
  → API permissions
  → Add a permission
  → Azure Cognitive Services
  → Delegated → user_impersonation
  → Grant admin consent ✓
```

### 2 — Azure OpenAI resource: assign user RBAC

```
Azure portal
  → foundry3000a  (your OpenAI resource)
  → Access control (IAM)
  → Add role assignment
  → Role: Cognitive Services OpenAI User
  → Assign to: shafiq.ahamed@hotmail.com
```

---

## Code Changes (3 files)

| File | Change |
|---|---|
| `agent/obo.py` | Add `exchange_obo_token_for_llm()` — second OBO for Cognitive Services scope |
| `agent/orchestrator.py` | Call the new OBO function; pass LLM token into `call_llm_with_tools()` |
| `agent/llm.py` | Accept optional `user_token` param; use it instead of API key when present |

---

## Full Request / Response Data Flow — "List users in Okta"

```
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Browser (React SPA — http://localhost:5173)                            │
  └─────────────────────────────────────────────────────────────────────────┘
          │
          │  1. User types: "List all users in Okta"
          │     MSAL acquireTokenSilent()
          │     scope: api://6b114879.../agent.access
          │
          ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Entra ID (login.microsoftonline.com)                                   │
  │                                                                         │
  │  Issues ACCESS TOKEN #1  (User → Agent)                                 │
  │    aud : api://6b114879-c58c-4889-9355-d5d9b19647a7                     │
  │    scp : agent.access                                                   │
  │    sub : <user-oid>                                                     │
  │    iss : https://sts.windows.net/b66066d2.../                           │
  └─────────────────────────────────────────────────────────────────────────┘
          │
          │  2. POST http://localhost:8000/chat
          │     Authorization: Bearer <ACCESS TOKEN #1>
          │     Body: { "prompt": "List all users in Okta" }
          │
          ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Agent  (FastAPI — http://localhost:8000)                               │
  │                                                                         │
  │  main.py         — extracts Bearer token                                │
  │  orchestrator.py — starts OBO exchanges                                 │
  └─────────────────────────────────────────────────────────────────────────┘
          │
          │  3a. OBO Exchange #1 — token for MCP Server
          │      POST https://login.microsoftonline.com/{tid}/oauth2/v2.0/token
          │      grant_type  : urn:ietf:params:oauth:grant-type:jwt-bearer
          │      assertion   : <ACCESS TOKEN #1>
          │      scope       : api://b600aeb4.../mcp.call
          │
          │  3b. OBO Exchange #2 — token for Azure OpenAI  ← NEW
          │      POST https://login.microsoftonline.com/{tid}/oauth2/v2.0/token
          │      grant_type  : urn:ietf:params:oauth:grant-type:jwt-bearer
          │      assertion   : <ACCESS TOKEN #1>
          │      scope       : https://cognitiveservices.azure.com/.default
          │
          ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Entra ID                                                               │
  │                                                                         │
  │  Issues ACCESS TOKEN #2  (User → MCP Server)                           │
  │    aud : api://b600aeb4-32e1-40a7-840c-2ab22dd46fd6                    │
  │    scp : mcp.call                                                       │
  │    sub : <user-oid>                                                     │
  │                                                                         │
  │  Issues ACCESS TOKEN #3  (User → Azure OpenAI)  ← NEW                  │
  │    aud : https://cognitiveservices.azure.com                            │
  │    scp : user_impersonation                                             │
  │    sub : <user-oid>                                                     │
  └─────────────────────────────────────────────────────────────────────────┘
          │
          │  4. Agent calls Azure OpenAI with ACCESS TOKEN #3
          │     POST https://foundry3000a.cognitiveservices.azure.com/
          │          openai/deployments/gpt-4.1/chat/completions
          │     Authorization: Bearer <ACCESS TOKEN #3>
          │     Body: {
          │       "messages": [
          │         { "role": "system", "content": "You are a helpful AI..." },
          │         { "role": "user",   "content": "List all users in Okta" }
          │       ],
          │       "tools": [ list_users, get_user, ... ],
          │       "tool_choice": "auto"
          │     }
          │
          ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Azure OpenAI  (gpt-4.1)                                                │
  │                                                                         │
  │  Sees user identity from ACCESS TOKEN #3 — audit log shows             │
  │  shafiq.ahamed@hotmail.com, not a service account.                     │
  │                                                                         │
  │  Responds with tool_call decision:                                      │
  │    finish_reason : "tool_calls"                                         │
  │    tool_calls[0] : {                                                    │
  │      "name"      : "list_users",                                        │
  │      "arguments" : { "limit": 25 }                                      │
  │    }                                                                    │
  └─────────────────────────────────────────────────────────────────────────┘
          │
          │  5. POST http://localhost:9000/mcp/call
          │     Authorization: Bearer <ACCESS TOKEN #2>
          │     Body: {
          │       "tool"      : "list_users",
          │       "arguments" : { "limit": 25 }
          │     }
          │
          ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  MCP Server  (FastAPI — http://localhost:9000)                          │
  │                                                                         │
  │  token_verifier.py                                                      │
  │    ✓ Fetch JWKS from Entra (cached 1h)                                  │
  │    ✓ RS256 signature verified                                           │
  │    ✓ aud  == api://b600aeb4...                                          │
  │    ✓ scp  == mcp.call                                                   │
  │    ✓ exp  not expired                                                   │
  │    ✓ iss  == sts.windows.net/b66066d2... (v1.0 accepted)                │
  │                                                                         │
  │  okta_tools.dispatch("list_users", { "limit": 25 })                    │
  └─────────────────────────────────────────────────────────────────────────┘
          │
          │  6. Acquire Okta service token (cached 1h)
          │     POST https://oie-8764513.oktapreview.com/oauth2/v1/token
          │     grant_type            : client_credentials
          │     client_assertion_type : urn:ietf:...:jwt-bearer
          │     client_assertion      : <signed JWT — private_key_jwt>
          │     scope                 : okta.users.read okta.users.manage ...
          │
          ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Okta Authorization Server                                              │
  │  (oie-8764513.oktapreview.com)                                          │
  │                                                                         │
  │  Validates private_key_jwt against uploaded public key                  │
  │  Issues OKTA ACCESS TOKEN                                               │
  │    scope : okta.users.read okta.users.manage ...                        │
  └─────────────────────────────────────────────────────────────────────────┘
          │
          │  7. GET https://oie-8764513.oktapreview.com/api/v1/users?limit=25
          │     Authorization: Bearer <OKTA ACCESS TOKEN>
          │     Accept: application/json
          │
          ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Okta Management API                                                    │
  │                                                                         │
  │  Returns user list:                                                     │
  │  [                                                                      │
  │    {                                                                    │
  │      "id"     : "00ux...",                                              │
  │      "status" : "ACTIVE",                                               │
  │      "profile": {                                                       │
  │        "login"    : "alice@example.com",                                │
  │        "email"    : "alice@example.com",                                │
  │        "firstName": "Alice",                                            │
  │        "lastName" : "Smith"                                             │
  │      }                                                                  │
  │    }, ...                                                               │
  │  ]                                                                      │
  └─────────────────────────────────────────────────────────────────────────┘
          │
          │  8. MCP Server returns to Agent:
          │     { "tool": "list_users", "result": [ ... ] }
          │     (also appended to tool_call_debug.txt)
          │
          │  9. Agent feeds tool result back to Azure OpenAI (round 2):
          │     messages += [
          │       { "role": "assistant", "tool_calls": [...] },
          │       { "role": "tool",      "content": "[{...}]" }
          │     ]
          │
          │  10. Azure OpenAI generates final text reply:
          │      "Here are the active users in your Okta tenant: ..."
          │
          │  11. Agent returns to SPA:
          │      {
          │        "reply"       : "Here are the active users...",
          │        "model"       : "gpt-4.1",
          │        "tools_called": [ { "tool": "list_users", ... } ],
          │        "token_preview": "eyJ0eXAiOiJKV1..."
          │      }
          │
          ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Browser — SPA renders the reply and tools_called panel                 │
  └─────────────────────────────────────────────────────────────────────────┘
```

---

## Token Summary

| # | Token | Issued by | Audience | Scope | Used for |
|---|---|---|---|---|---|
| 1 | User → Agent | Entra | `api://6b114879...` | `agent.access` | Authenticate user to Agent |
| 2 | User → MCP | Entra (OBO) | `api://b600aeb4...` | `mcp.call` | Authenticate user to MCP Server |
| 3 | User → OpenAI | Entra (OBO) ← NEW | `cognitiveservices.azure.com` | `user_impersonation` | Authenticate user to Azure OpenAI |
| 4 | Service → Okta | Okta AS | Okta Org AS | `okta.users.read` … | Call Okta Management API |

---

## Implementation Steps

### 1 — `agent/obo.py`

Add a second exchange function:

```python
async def exchange_obo_token_for_llm(user_token: str) -> str:
    """OBO exchange scoped to Azure Cognitive Services (Azure OpenAI)."""
    scope = "https://cognitiveservices.azure.com/.default"
    # Same OBO grant as exchange_obo_token(), different scope
```

### 2 — `agent/orchestrator.py`

```python
mcp_token = await exchange_obo_token(user_token)          # MCP Server
llm_token = await exchange_obo_token_for_llm(user_token)  # Azure OpenAI (NEW)

response = await call_llm_with_tools(messages, TOOLS, llm_token)
```

### 3 — `agent/llm.py`

```python
async def call_llm_with_tools(messages, tools, user_token: str | None = None):
    if user_token:
        # OBO for AI — user identity flows into Azure OpenAI
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            azure_ad_token_provider=lambda: user_token,
            api_version=api_version,
        )
    else:
        # Fallback: API key (local dev without OBO configured)
        client = _build_client()
```

### 4 — `agent/.env`

```
# Keep API key as fallback for local dev without OBO configured
# Remove it to force OBO-only auth
# AZURE_OPENAI_API_KEY=<remove when OBO is confirmed working>
```

---

## Rollback

If OBO for AI fails (e.g. RBAC not assigned), the code falls back to API key
automatically — no service disruption.
