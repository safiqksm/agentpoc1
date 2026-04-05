# Step 4 Plan — OBO Token Exchange (Agent → Entra ID → OBO Token)

## Overview
The Agent holds the **user's incoming Bearer token** (issued by Entra ID, scoped to the Agent app).
OBO (On-Behalf-Of) lets the Agent exchange that token for a **new token scoped to the MCP Server** — so the MCP Server can verify *who the original user was* while granting the Agent delegated access.

```
User Token (aud = Agent App)
    │
    ▼  POST /oauth2/v1/token  (OBO grant)
Entra ID
    │
    ▼
OBO Token (aud = MCP Server App)
    │
    ▼
Agent sends OBO Token to MCP Server
    │
    ▼
MCP Server validates OBO Token (Step 8)
```

---

## Three App Registrations Involved

| App Registration | Role | Already Created? |
|---|---|---|
| `poc-client-app` | React SPA — issues the original user token | Yes (Step 1) |
| `agentpoc1-agent` | Agent backend — receives user token, performs OBO | Yes (Step 1) |
| `agentpoc1-mcp` | MCP Server — target audience of the OBO token | **No — create in Step 4** |

---

## What We Are Building

### In Entra ID (see `ENTRA_OBO_SETUP.md`)
1. Create `agentpoc1-mcp` App Registration with a scope `mcp.call`
2. Add `agentpoc1-agent` as an **authorized client** for `mcp.call` (pre-authorize it)
3. Add a **Client Secret** to `agentpoc1-agent` (needed to call the OBO endpoint)
4. Grant `agentpoc1-agent` permission to call `agentpoc1-mcp/mcp.call`

### In Code
New file `agent/obo.py`:
- `exchange_obo_token(user_token, agent_client_secret) -> str`
- Calls `POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token`
- Grant type: `urn:ietf:params:oauth:grant-type:jwt-bearer`
- Returns the OBO access token string

Update `agent/orchestrator.py`:
- Before calling `mcp_client.call_tool()`, exchange the user token for an OBO token
- Pass the OBO token to `mcp_client.call_tool()` instead of the raw user token

Update `agent/.env.example`:
- Add `AGENT_CLIENT_SECRET`, `MCP_APP_ID`

---

## OBO Token Exchange — HTTP Request

```
POST https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token

Body (form-encoded):
  grant_type        = urn:ietf:params:oauth:grant-type:jwt-bearer
  client_id         = {AGENT_CLIENT_ID}         ← agentpoc1-agent app ID
  client_secret     = {AGENT_CLIENT_SECRET}      ← agent's client secret
  assertion         = {USER_ACCESS_TOKEN}        ← the incoming Bearer token
  scope             = api://{MCP_APP_ID}/mcp.call offline_access
  requested_token_use = on_behalf_of
```

Response contains:
```json
{
  "access_token": "<OBO token — aud = MCP app ID>",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

---

## Files to Create / Update

```
agent/
├── obo.py           ← NEW — OBO token exchange helper
├── orchestrator.py  ← UPDATE — use OBO token when calling MCP client
└── .env.example     ← UPDATE — add AGENT_CLIENT_ID, AGENT_CLIENT_SECRET, MCP_APP_ID
```

### `obo.py`
```python
async def exchange_obo_token(user_token: str) -> str:
    """
    Exchange the user's Bearer token for an OBO token scoped to the MCP Server.
    Returns the OBO access token string.
    Raises RuntimeError if env vars are missing or Entra returns an error.
    """
```

---

## Token Cache
OBO tokens are valid for ~1 hour. For this POC we call the OBO endpoint on every
request (simple, stateless). A token cache can be added later to avoid unnecessary
round-trips to Entra ID.

---

## OWASP Risk: LLM08 / AA05 — Broken Auth on Managed Identity

**Risk:** If the OBO exchange uses a weak or leaked client secret, an attacker can
impersonate the agent.

**Mitigations:**
- `AGENT_CLIENT_SECRET` stored in `.env` locally; in Azure replaced by **Managed Identity + certificate** (no secret at rest)
- OBO token is short-lived (1 hour)
- MCP Server validates `aud` claim matches its own App ID (Step 8)

---

## Success Criteria for Step 4

- [ ] `exchange_obo_token(user_token)` returns a valid JWT with:
  - `aud` = `api://{MCP_APP_ID}`
  - `scp` = `mcp.call`
  - `sub` = original user's object ID
- [ ] Orchestrator passes OBO token to `mcp_client.call_tool()` instead of raw user token
- [ ] If OBO exchange fails (missing config), agent returns a clear 500 error
- [ ] `POST /chat/echo` still works unchanged (does not go through OBO)

---

## Next Step
**Step 5** — Agent calls MCP Server directly over HTTP with the OBO token.
MCP Server validates the OBO token signature and `scp` claim (Step 8).
