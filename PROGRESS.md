# AgentPOC1 — Progress Summary

## Architecture

```
Browser (React SPA — localhost:5173)
    │  TOKEN #1  aud: agentpoc1-agent  scp: agent.access
    ▼
Agent (FastAPI — localhost:8000)
    │  OBO #1 → TOKEN #2  aud: agentpoc1-mcp      scp: mcp.call
    │  OBO #2 → TOKEN #3  aud: cognitiveservices.azure.com  scp: user_impersonation
    ├──────────────────────────────────────────────────────►  Azure OpenAI (TOKEN #3)
    │
    ▼
MCP Server (FastAPI — localhost:9000)
    │  validates TOKEN #2 (JWKS/RS256)
    │  client_credentials + private_key_jwt → OKTA TOKEN
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
| 4 | OBO token exchange — agent → Entra → MCP-scoped token | ✅ Done |
| 5 | MCP Server token validation — full JWKS/RS256/aud/scp check | ✅ Done |
| 6/7 | APIM | ⏭ Skipped — token validation stays in MCP Server |
| 8 | Okta token acquisition — private_key_jwt client_credentials | ✅ Done |
| 11 | Real Okta Management API calls (all 7 tools) | ✅ Done |
| 13 | Azure OpenAI (GPT-4.1) LLM integration | ✅ Done |
| 14 | OBO for AI — user identity flows into Azure OpenAI calls | ✅ Done |

---

## OBO for AI — What Was Done

The agent now performs **two OBO exchanges** per request using the same incoming user token:

| Exchange | Scope | Token Audience | Used For |
|---|---|---|---|
| OBO #1 | `api://b600aeb4.../mcp.call` | `api://b600aeb4...` | Authenticate to MCP Server |
| OBO #2 | `https://cognitiveservices.azure.com/.default` | `cognitiveservices.azure.com` | Authenticate to Azure OpenAI |

**Entra portal changes made:**
- `agentpoc1-agent` → API permissions → `Microsoft Cognitive Services / user_impersonation` (delegated) → admin consent granted
- `foundry3000a` → IAM → `Cognitive Services OpenAI User` role assigned to `shafiq.ahamed@hotmail.com`

**Benefit:** Azure OpenAI audit logs show the real user identity (`shafiq.ahamed@hotmail.com`) on every LLM call instead of a service account.

---

## Key Files

```
poc-client-app/
├── src/main.jsx               — MSAL bootstrap
├── src/App.jsx                — AuthApp (Entra) / LocalApp split
├── src/authConfig.js          — MSAL config, loginRequest, agentTokenRequest
├── src/pages/ChatPage.jsx
├── src/pages/TokenPanel.jsx   — displays ID token claims
└── src/services/agentService.js — acquireToken + sendPrompt

agent/
├── main.py               — FastAPI /chat, /debug/token, /debug/token/llm
├── orchestrator.py       — ReAct loop, dual OBO exchange, token_debug.txt writer
├── obo.py                — exchange_obo_token() + exchange_obo_token_for_llm()
├── llm.py                — Azure OpenAI GPT-4.1, OBO for AI via azure_ad_token_provider
├── mcp_client.py         — HTTP to MCP Server, mock fallback, error logging
├── tools.py              — 7 tool schemas + DESTRUCTIVE_TOOLS set
├── token_debug.txt       — per-request token flow log (auto-written)
└── .env                  — All values filled in

mcp_server/
├── main.py               — FastAPI /mcp/call, /debug/okta-token
├── token_verifier.py     — Full JWT validation (JWKS, RS256, aud, scp, exp)
├── okta_client.py        — private_key_jwt → Okta token (1h cache) + get_last_token_info()
├── okta_tools.py         — Real Okta API calls + mock fallback
├── okta_private.pem      — Local RSA private key (gitignored)
├── tool_call_debug.txt   — per-tool-call log (auto-written)
└── .env                  — All values filled in

plans/                    — Per-step implementation plans
steps/                    — Step-by-step task list
```

---

## Debug Endpoints

| Endpoint | Server | What it shows |
|---|---|---|
| `GET /debug/token` | Agent :8000 | User token + MCP OBO token claims |
| `GET /debug/token/llm` | Agent :8000 | User token + LLM OBO token claims (OBO for AI) |
| `GET /debug/okta-token` | MCP :9000 | Last acquired Okta token (sub, scope, expiry) |

**Test OBO for AI from browser DevTools:**
```js
fetch('http://localhost:8000/debug/token/llm', {
  headers: {
    'Authorization': 'Bearer ' + (await msalInstance.acquireTokenSilent({
      scopes: ['api://6b114879-c58c-4889-9355-d5d9b19647a7/agent.access'],
      account: msalInstance.getAllAccounts()[0]
    })).accessToken
  }
}).then(r => r.json()).then(console.log)
```

**Expected output:**
```json
{
  "llm_token": {
    "aud": "https://cognitiveservices.azure.com",
    "scp": "user_impersonation",
    "sub": "<user-oid>"
  },
  "llm_error": null
}
```

---

## Token Debug Log

Every request writes `agent/token_debug.txt`:

```
REQUEST FLOW — 2026-04-05 18:45:00 UTC
==================================================

[1] USER → AGENT  (Bearer token received)
  aud : api://6b114879-c58c-4889-9355-d5d9b19647a7
  scp : agent.access
  sub : <user-oid>

[2] OBO EXCHANGE → MCP SERVER
  aud : api://b600aeb4-32e1-40a7-840c-2ab22dd46fd6
  scp : mcp.call
  sub : <user-oid>

[3] OBO EXCHANGE → AZURE OPENAI (OBO for AI)
  aud : https://cognitiveservices.azure.com
  scp : user_impersonation
  sub : <user-oid>

[4] LLM CALL
  auth : OBO for AI ✓

[5] MCP SERVER → OKTA  (client_credentials / private_key_jwt)
  sub   : 0oax4b20kdBGCVvMk1d7
  scope : okta.users.read okta.users.manage ...
  aud   : https://oie-8764513.oktapreview.com/oauth2/v1/token
  expires_in: 3600s

==================================================
```

---

## Start Servers

```bash
# Terminal 1 — MCP Server
cd /Users/shafiqksm/claude/agentpoc1/mcp_server && source .venv/bin/activate && uvicorn main:app --port 9000

# Terminal 2 — Agent
cd /Users/shafiqksm/claude/agentpoc1/agent && source .venv/bin/activate && uvicorn main:app --port 8000

# Terminal 3 — React SPA
cd /Users/shafiqksm/claude/agentpoc1/poc-client-app && npm run dev
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

## Pending Items

- [ ] Assign **User Administrator** role to `agentpoc1-mcp-service` in Okta
  (Security → Administrators → Add administrator → User Administrator)
  Without this, `create_user` / `deactivate_user` return 403 from Okta
- [ ] Step 15 — final response formatting / LLM prompt tuning
- [ ] Remove debug endpoints before production deployment

---

## Reference Docs

| File | Purpose |
|---|---|
| `ENTRA_OBO_SETUP.md` | Entra App Registration setup for OBO (MCP) flow |
| `ENTRA_OBO_FOR_AI_SETUP.md` | Entra setup for OBO for AI (Azure OpenAI) |
| `OKTA_SETUP.md` | Okta service app + private_key_jwt key setup |
| `REQUEST_FLOW.md` | ASCII request/response flow — Scenarios A–E |
| `plans/` | Per-step implementation plans |
| `steps/steps.md` | Step-by-step task list |

---

## Git

- **main** — stable baseline
- **feature/obo-for-ai** — current branch (OBO for AI + debug logging + file reorganisation)
