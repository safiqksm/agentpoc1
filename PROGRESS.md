# AgentPOC1 — Progress Summary

## Architecture

```
React SPA (poc-client-app)
    │  Bearer token (Entra OIDC)
    ▼
Agent (FastAPI :8000)
    │  OBO exchange → OBO token
    ▼
MCP Server (FastAPI :9000)
    │  private_key_jwt → Okta access token
    ▼
Okta Management API
```

---

## Steps Completed

| Step | What | Status |
|---|---|---|
| 1 | React SPA — Entra OIDC login (MSAL.js v5, loginRedirect) | ✅ Done |
| 2 | Agent FastAPI — /chat, /chat/echo, CORS, token extraction | ✅ Done |
| 3 | ReAct agent loop — LLM + tool dispatch + OWASP LLM06 guard | ✅ Done |
| 4 | OBO token exchange — agent calls Entra to get MCP-scoped token | ✅ Done |
| 5 | MCP Server token validation — full JWKS/RS256/aud/scp check | ✅ Done |
| 6/7 | APIM | ⏭ Skipped — token validation stays in MCP Server |
| 8 | Okta token acquisition — private_key_jwt client_credentials | ✅ Done |
| 11 | Real Okta Management API calls (all 7 tools) | ✅ Done |
| 13 | Azure OpenAI (GPT-4.1) LLM integration | ✅ Done |

---

## Key Files

```
poc-client-app/
├── src/main.jsx          — MSAL bootstrap (async init + handleRedirectPromise)
├── src/App.jsx           — AuthApp (Entra) / LocalApp (no auth) split
├── src/authConfig.js     — MSAL config, loginRequest, agentTokenRequest
├── src/pages/ChatPage.jsx
├── src/pages/TokenPanel.jsx — displays ID token claims
└── src/services/agentService.js — acquireToken + sendPrompt

agent/
├── main.py               — FastAPI entry point, /chat, /debug/token endpoint
├── orchestrator.py       — ReAct loop (MAX_TOOL_ROUNDS=5)
├── obo.py                — OBO token exchange (Entra), logs both token claims
├── llm.py                — Azure OpenAI GPT-4.1 (DefaultAzureCredential in prod)
├── mcp_client.py         — HTTP to MCP Server, mock fallback, error logging
├── tools.py              — 7 tool schemas + DESTRUCTIVE_TOOLS set
└── .env                  — All values filled in

mcp_server/
├── main.py               — FastAPI /mcp/call endpoint
├── token_verifier.py     — Full JWT validation (JWKS, RS256, aud, scp, exp)
├── okta_client.py        — private_key_jwt → Okta access token (1h cache)
├── okta_tools.py         — Real Okta API calls + mock fallback
├── okta_private.pem      — Local RSA private key (gitignored)
└── .env                  — All values filled in
```

---

## Environment Variables

### `agent/.env`
```
TENANT_ID=b66066d2-2dc9-4773-8a40-a7d93c1f76bf
AGENT_CLIENT_ID=6b114879-c58c-4889-9355-d5d9b19647a7
AGENT_CLIENT_SECRET=<set>
MCP_APP_ID=b600aeb4-32e1-40a7-840c-2ab22dd46fd6
MCP_SERVER_URL=http://localhost:9000
AZURE_OPENAI_ENDPOINT=https://foundry3000a.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=<set>
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-08-01-preview
ALLOWED_ORIGIN=http://localhost:5173
```

### `mcp_server/.env`
```
TENANT_ID=b66066d2-2dc9-4773-8a40-a7d93c1f76bf
MCP_APP_ID=b600aeb4-32e1-40a7-840c-2ab22dd46fd6
OKTA_DOMAIN=https://oie-8764513.oktapreview.com
OKTA_CLIENT_ID=0oax4b20kdBGCVvMk1d7
OKTA_PRIVATE_KEY_PATH=./okta_private.pem
OKTA_PRIVATE_KEY_KID=n2Mmr0smmXUo/R/MRm/OSkJPhfffF/ErNLTsnn4Q8LE=
ALLOWED_AGENT_ORIGIN=http://localhost:8000
```

### `poc-client-app/.env`
```
VITE_TENANT_ID=b66066d2-2dc9-4773-8a40-a7d93c1f76bf
VITE_CLIENT_ID=56705bd6-0ff3-492a-8d1d-77dba1a04553
VITE_AGENT_SCOPE=api://6b114879-c58c-4889-9355-d5d9b19647a7/agent.access
VITE_AGENT_ENDPOINT=http://localhost:8000/chat
VITE_REDIRECT_URI=http://localhost:5173
```

---

## Start Servers

```bash
# Terminal 1 — MCP Server
cd /Users/shafiqksm/claude/agentpoc1/mcp_server
source .venv/bin/activate
uvicorn main:app --port 9000

# Terminal 2 — Agent
cd /Users/shafiqksm/claude/agentpoc1/agent
source .venv/bin/activate
uvicorn main:app --port 8000

# Terminal 3 — React SPA
cd /Users/shafiqksm/claude/agentpoc1/poc-client-app
npm run dev
```

---

## Current Issue Being Debugged

**Symptom:** SPA returns mock data (alice/bob/carol) instead of real Okta users.

**Root causes found and fixed so far:**
1. `AGENT_APP_ID` in `.env` → should be `AGENT_CLIENT_ID` — **fixed**
2. MCP server started from wrong directory — **fixed in startup order**
3. `mcp_client.py` silently fell back to mock on ANY exception (connection refused, 403, timeout) — **fixed: now raises RuntimeError so the real error surfaces as HTTP 500**

**Debugging tool added:** `GET /debug/token` endpoint on the agent (port 8000).
Call it with the Entra Bearer token to see:
- User token claims: `aud`, `scp`, `sub`, `iss`
- OBO token claims: `aud`, `scp`, `sub`, `iss`
- OBO error (if exchange failed)

**After the fix**, the agent will return HTTP 500 with the real error instead of mock data. The two expected errors are:
- `"Cannot reach MCP Server at http://localhost:9000 — is it running?"` → MCP server not running
- `"MCP Server rejected 'list_users' with HTTP 403: ..."` → OBO token validation failure

**To call from browser DevTools after SPA login:**
```js
fetch('http://localhost:8000/debug/token', {
  headers: {
    'Authorization': 'Bearer ' + (await msalInstance.acquireTokenSilent({
      scopes: ['api://6b114879-c58c-4889-9355-d5d9b19647a7/agent.access'],
      account: msalInstance.getAllAccounts()[0]
    })).accessToken
  }
}).then(r => r.json()).then(console.log)
```

**Expected output when working correctly:**
```json
{
  "user_token": { "aud": "api://6b114879...", "scp": "agent.access", "sub": "<user-oid>" },
  "obo_token":  { "aud": "api://b600aeb4...", "scp": "mcp.call",     "sub": "<user-oid>" },
  "obo_error": null
}
```

---

## Pending Items

- [ ] Assign **User Administrator** role to `agentpoc1-mcp-service` in Okta
  (Security → Administrators → Add administrator → select app → User Administrator)
  Without this, `create_user` / `deactivate_user` return 403 from Okta
- [ ] Resolve mock data fallback issue (debug with `/debug/token` endpoint above)
- [ ] Commit all code to GitHub
- [ ] Step 14 — final response formatting / LLM prompt tuning

---

## Reference Docs in Repo

| File | Purpose |
|---|---|
| `ENTRA_OBO_SETUP.md` | Entra App Registration setup for OBO flow |
| `ENTRA_OBO_FOR_AI_SETUP.md` | Entra setup for OBO for AI (Azure OpenAI user impersonation) |
| `OKTA_SETUP.md` | Okta service app + private_key_jwt key setup |
| `REQUEST_FLOW.md` | ASCII request/response flow diagrams |
| `plans/step-01-plan.md` … `plans/step-13-plan.md` | Per-step implementation plans |
| `plans/step-obo-for-ai-plan.md` | OBO for AI implementation plan |
| `steps/steps.md` | Step-by-step task list |
