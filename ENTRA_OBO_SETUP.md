# Entra ID Setup — OBO (On-Behalf-Of) Token Exchange

## What You Are Configuring

The OBO flow requires three App Registrations wired together:

```
poc-client-app  ──(user token)──►  agentpoc1-agent  ──(OBO token)──►  agentpoc1-mcp
   (React SPA)                       (FastAPI Agent)                   (MCP Server)
```

| App | Already exists? | Action |
|---|---|---|
| `poc-client-app` | Yes | No changes |
| `agentpoc1-agent` | Yes | Add client secret + API permission |
| `agentpoc1-mcp` | **No** | Create now |

---

## Part 1 — Create `agentpoc1-mcp` App Registration

This represents the MCP Server. The Agent will request an OBO token scoped to this app.

### 1.1 — Register the app
1. Go to [portal.azure.com](https://portal.azure.com) → **Microsoft Entra ID**
2. **App registrations** → **New registration**
3. Fill in:
   - **Name:** `agentpoc1-mcp`
   - **Supported account types:** Accounts in this organizational directory only
   - **Redirect URI:** Leave blank
4. Click **Register**
5. On the Overview page, copy:
   - **Application (client) ID** → this is your `MCP_APP_ID`
   - **Directory (tenant) ID** → same as before

### 1.2 — Expose an API scope
1. In the left menu → **Expose an API**
2. Click **Add** next to Application ID URI
   - Accept the default: `api://<MCP_APP_ID>`
   - Click **Save**
3. Click **Add a scope**
   - **Scope name:** `mcp.call`
   - **Who can consent:** Admins and users
   - **Admin consent display name:** Call AgentPOC1 MCP Server
   - **Admin consent description:** Allows the Agent to call the MCP Server on behalf of the user
   - **State:** Enabled
4. Click **Add scope**

Your full scope string is now: `api://<MCP_APP_ID>/mcp.call`

### 1.3 — Pre-authorize the Agent app (skip admin consent per-request)
1. Still on **Expose an API**
2. Under **Authorized client applications** → **Add a client application**
3. **Client ID:** paste the `agentpoc1-agent` Application (client) ID
4. **Authorized scopes:** tick `api://<MCP_APP_ID>/mcp.call`
5. Click **Add application**

> This pre-authorization means the Agent can perform OBO without prompting the user for consent on the MCP scope.

---

## Part 2 — Update `agentpoc1-agent` App Registration

The Agent needs a **client secret** to authenticate itself when calling the OBO endpoint, and needs permission to request the MCP scope.

### 2.1 — Add a client secret
1. Open `agentpoc1-agent` App Registration
2. Left menu → **Certificates & secrets** → **Client secrets** → **New client secret**
   - **Description:** `obo-secret`
   - **Expires:** 180 days (or your preference)
3. Click **Add**
4. **Copy the secret Value immediately** — it is only shown once
   - This is your `AGENT_CLIENT_SECRET`

> In Azure production: replace this secret with a **certificate** + Managed Identity (no secret stored at rest).

### 2.2 — Add API permission for MCP scope
1. Still in `agentpoc1-agent` → **API permissions** → **Add a permission**
2. **My APIs** tab → select `agentpoc1-mcp`
3. **Delegated permissions** → tick `mcp.call`
4. Click **Add permissions**
5. Click **Grant admin consent for \<your tenant\>** → **Yes**

---

## Part 3 — Verify `poc-client-app` permissions (no change needed)

The React SPA already requests a token scoped to `agentpoc1-agent`. The user's token arrives at the Agent with:
- `aud` = `api://<AGENT_APP_ID>`
- `scp` = `agent.access`

The Agent then performs OBO to get a token with:
- `aud` = `api://<MCP_APP_ID>`
- `scp` = `mcp.call`

No changes to `poc-client-app` are needed.

---

## Part 4 — Update agent/.env

Add these values to `agent/.env`:

```
# OBO token exchange — Step 4
TENANT_ID=<your-tenant-id>
AGENT_CLIENT_ID=<agentpoc1-agent application client ID>
AGENT_CLIENT_SECRET=<secret value from Part 2.1>
MCP_APP_ID=<agentpoc1-mcp application client ID>

# MCP Server URL (direct call — Step 5)
MCP_SERVER_URL=http://localhost:9000
```

---

## Part 5 — Update mcp_server/.env

The MCP Server needs to know its own App ID to validate the `aud` claim in the OBO token:

```
# Token validation — Step 8
TENANT_ID=<your-tenant-id>
MCP_APP_ID=<agentpoc1-mcp application client ID>
```

---

## Verify the OBO Flow

After implementing Step 4, you can verify the OBO token at [jwt.ms](https://jwt.ms):

1. Sign in to the React app
2. Send a prompt — check the agent logs for the OBO token
3. Paste the OBO token into `jwt.ms` and confirm:

| Claim | Expected value |
|---|---|
| `aud` | `api://<MCP_APP_ID>` |
| `scp` | `mcp.call` |
| `sub` | User's object ID (same as in the original user token) |
| `iss` | `https://login.microsoftonline.com/<TENANT_ID>/v2.0` |
| `appid` | `<AGENT_CLIENT_ID>` (the Agent acting on behalf of the user) |

---

## Summary — What You Created

```
agentpoc1-mcp (NEW)
  └── Expose API: api://<MCP_APP_ID>/mcp.call
  └── Authorized client: agentpoc1-agent (pre-authorized)

agentpoc1-agent (UPDATED)
  └── Client secret: obo-secret
  └── API permission: agentpoc1-mcp / mcp.call (admin consented)
```
