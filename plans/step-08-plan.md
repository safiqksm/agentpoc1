# Step 8/9/10/11 Plan — Okta Integration (Client Credentials + Real API Calls)

## Overview

Steps 6/7 (APIM) are skipped — token validation stays in the MCP Server (Step 5).
Steps 8/9 (Key Vault + private_key_jwt) are simplified — this POC uses
**client_id + client_secret** for the Okta `client_credentials` grant.

```
MCP Server receives tool call (token already verified — Step 5)
    │
    ▼  STEP 8 — get Okta access token
    POST https://oie-8764513.oktapreview.com/oauth2/v1/token
    (client_credentials: OKTA_CLIENT_ID + OKTA_CLIENT_SECRET)
    │
    ▼  STEP 11 — call real Okta Management API
    GET/POST https://oie-8764513.oktapreview.com/api/v1/...
    (Bearer <okta_access_token>)
    │
    ▼  STEP 12 — return result to Agent
    JSON response → mcp_client → orchestrator → LLM → React
```

---

## What We Are Building

### New file: `mcp_server/okta_client.py`
- `get_okta_headers()` — returns `{"Authorization": "SSWS <OKTA_API_TOKEN>"}` header dict
- No token endpoint call — SSWS token used directly
- Single place to swap to `private_key_jwt` later if needed

### Updated file: `mcp_server/okta_tools.py`
Replace all mock responses with real Okta Management API calls:

| Tool | Okta API Endpoint |
|---|---|
| `list_users` | `GET /api/v1/users?limit=25` |
| `get_user` | `GET /api/v1/users/{user_id}` |
| `create_user` | `POST /api/v1/users?activate=true` |
| `deactivate_user` | `POST /api/v1/users/{user_id}/lifecycle/deactivate` |
| `get_group` | `GET /api/v1/groups/{group_id}` |
| `assign_app` | `PUT /api/v1/apps/{app_id}/users/{user_id}` |
| `reset_mfa` | `DELETE /api/v1/users/{user_id}/factors` (reset all enrolled factors) |

### Updated file: `mcp_server/.env.example`
Replace `OKTA_CLIENT_ID` with `OKTA_API_TOKEN`.

---

## Okta Auth — SSWS API Token

No token endpoint call needed. Every Okta Management API request includes:

```
Authorization: SSWS <OKTA_API_TOKEN>
```

The `okta_client.py` module reads `OKTA_API_TOKEN` from the environment and
returns the header dict. This is the POC approach; the production upgrade
is to replace the SSWS token with `private_key_jwt` + Key Vault.

Java analogy: like injecting a static API key from application.properties —
no OAuth handshake required.

---

## Local Dev Fallback

If `OKTA_API_TOKEN` is not set, `okta_tools.py` falls back to the in-process
mock responses. This preserves the end-to-end local dev flow without needing
an Okta tenant.

---

## Files to Create / Update

```
mcp_server/
├── okta_client.py     ← NEW — Okta token acquisition + caching
├── okta_tools.py      ← UPDATE — real Okta API calls (mock fallback retained)
└── .env.example       ← UPDATE — add OKTA_CLIENT_SECRET
```

---

## OWASP Risks

| Risk | Mitigation |
|---|---|
| LLM06 — Excessive Agency | Destructive tools (deactivate, reset_mfa) blocked in orchestrator unless explicit intent |
| AA05 — Broken Auth | `OKTA_CLIENT_SECRET` in `.env`; use Managed Identity + Key Vault in Azure prod |
| LLM02 — Prompt Injection | Tool args are passed as structured JSON, not interpolated into strings |

---

## Success Criteria for Step 8/10/11

- [ ] `get_okta_token()` returns a valid Okta access token (verified at jwt.ms)
- [ ] `list_users` returns real users from the Okta tenant
- [ ] `get_user` returns a real user profile by ID
- [ ] `create_user` creates a staged user in Okta
- [ ] `deactivate_user` deactivates a user (only called with explicit intent)
- [ ] Token cached — Okta token endpoint called once, not per tool call
- [ ] Without `OKTA_CLIENT_SECRET` set, mock responses still returned (local dev)

---

## Next Step

**Step 12** — result return chain is already wired:
`okta_tools.py` → `main.py` → `mcp_client.py` → `orchestrator.py` → `main.py` → React

No code changes needed for Step 12 — the wiring from Step 3/5 handles it.

**Step 14** — final response formatting review (LLM prompt tuning).
