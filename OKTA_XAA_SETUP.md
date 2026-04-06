# Okta XAA (Cross App Access) Setup Guide

This guide walks through every Okta admin step to get the XAA flow working, and tells you exactly which `.env` file to update with each value.

## What you are building

```
React SPA  →  (Okta ID token)  →  Agent  →  XAA Step 1: ID-JAG  →  Okta Org AS
                                         →  XAA Step 2: access token  →  Okta Custom AS
                                         →  (access token)  →  HR Resource Server
```

You need **4 app registrations** in Okta:

| App name (you choose) | Purpose | Already exists? |
|---|---|---|
| `agentpoc1-caa-spa` | User logs in here via browser (port 5174) | ❌ Create now |
| `agentpoc1-agent-service` | Agent's machine identity for XAA Step 1 | ❌ Create now |
| `agentpoc1-resource-server` | Resource server's identity | ❌ Create now |
| `agentpoc1-mcp-service` | Okta management API (existing) | ✅ `OKTA_CLIENT_ID=0oax4b20kdBGCVvMk1d7` |

You also need **1 Custom Authorization Server** for the resource server.

---

## Prerequisites

- ✅ Early Access feature "Cross App Access" is already enabled
- ✅ Okta org: `https://oie-8764513.oktapreview.com`

---

## Part 1 — Create `agentpoc1-caa-spa` (SPA login app)

This is the app the **React browser** uses to log users in via Okta OIDC.
The new XAA SPA lives in the `agentpoc1-caa-spa/` folder and runs on port **5174**
(separate from the existing `poc-client-app` on port 5173 — they do not share files).

### Steps

1. Okta Admin Console → **Applications → Applications → Create App Integration**
2. Select **OIDC - OpenID Connect** → **Single-Page Application** → Next
3. Fill in:
   - **App integration name**: `agentpoc1-caa-spa`
   - **Grant type**: check **Authorization Code** (PKCE is on by default for SPA)
   - **Sign-in redirect URIs**: `http://localhost:5174/login/callback`
   - **Sign-out redirect URIs**: `http://localhost:5174`
   - **Controlled access**: Allow everyone in your org (or assign yourself)
4. Click **Save**
5. On the next screen, copy the **Client ID**

### Where to put the value

File: `agentpoc1-caa-spa/.env`  ← **not** poc-client-app

```
VITE_OKTA_CLIENT_ID=<paste Client ID here>
VITE_OKTA_ISSUER=https://oie-8764513.oktapreview.com/oauth2/default
VITE_OKTA_REDIRECT_URI=http://localhost:5174/login/callback
```

> `VITE_OKTA_ISSUER` points to the Okta org-level default AS — this is where the user logs in and gets the ID token. Keep it as shown above.

---

## Part 2 — Create `agentpoc1-agent-service` (agent machine identity)

This is the **Python agent's** identity when calling the Okta Org AS for XAA Step 1.
It proves "I am the agent app, and I am requesting an ID-JAG on behalf of this user."

### Step 2a — Create the app

1. Okta Admin Console → **Applications → Applications → Create App Integration**
2. Select **API Services** (machine-to-machine, no user login) → Next
3. Fill in:
   - **App integration name**: `agentpoc1-agent-service`
4. Click **Save**

### Step 2b — Switch to public key auth

By default Okta uses a client secret. Switch it to RSA key (same method as the existing MCP server):

1. On the app page → **General** tab → scroll to **Client Credentials**
2. Click **Edit** → change **Client authentication** to **Public key / Private key**
3. Click **Add key** → select **Generate new key**
4. Okta shows a key pair — **download or copy the private key (PEM)** — you will not see it again
5. Note the **Key ID** shown next to the key

> Alternatively generate your own key pair and upload the public key:
> ```bash
> cd agent
> openssl genrsa -out okta_agent_private.pem 2048
> openssl rsa -in okta_agent_private.pem -pubout -out okta_agent_public.pem
> ```
> Then click **Add key → Import existing key** and paste the contents of `okta_agent_public.pem`.

6. Copy the **Client ID** from the top of the app page

### Where to put the values

File: `agent/.env`

```
OKTA_AGENT_CLIENT_ID=<paste Client ID here>
OKTA_AGENT_PRIVATE_KEY_PATH=./okta_agent_private.pem
OKTA_AGENT_KEY_KID=<paste Key ID here>
```

> Save the private key as `agent/okta_agent_private.pem`.
> This is a different key from the MCP server's `mcp_server/okta_private.pem` — do not mix them up.

---

## Part 3 — Create `agentpoc1-resource-server` (resource server identity)

This app represents the **HR Resource Server** (`resource_server/`).
It is the "audience" that the agent requests ID-JAGs for.

### Steps

1. Okta Admin Console → **Applications → Applications → Create App Integration**
2. Select **OIDC - OpenID Connect** → **Web Application** → Next
3. Fill in:
   - **App integration name**: `agentpoc1-resource-server`
   - **Grant type**: check **Client Credentials** (uncheck others)
   - **Sign-in redirect URIs**: `http://localhost:8100/callback` (placeholder, not used)
   - **Controlled access**: Allow everyone
4. Click **Save**
5. Copy the **Client ID**

### Where to put the value

File: `agent/.env`

```
OKTA_RESOURCE_APP_CLIENT_ID=<paste Client ID here>
```

---

## Part 4 — Create the Custom Authorization Server

The Custom AS is what issues the final **access token** (with `hr.read` scope) that the HR Resource Server validates.

### Step 4a — Create the Authorization Server

1. Okta Admin Console → **Security → API → Authorization Servers → Add Authorization Server**
2. Fill in:
   - **Name**: `agentpoc1-resource-as`
   - **Audience**: `http://localhost:8100`
   - **Description**: HR Resource Server (optional)
3. Click **Save**
4. You are taken to the AS details page
5. Copy the **Issuer URI** — it looks like:
   `https://oie-8764513.oktapreview.com/oauth2/abc123def`
   The last segment (`abc123def`) is the **AS ID**

### Where to put the values

File: `agent/.env`

```
OKTA_RESOURCE_AS_ID=<paste the AS ID segment here>
# Example: if Issuer is https://oie-8764513.oktapreview.com/oauth2/aus1abc123
# then OKTA_RESOURCE_AS_ID=aus1abc123
```

File: `resource_server/.env`

```
OKTA_DOMAIN=https://oie-8764513.oktapreview.com
RESOURCE_AS_ID=<same AS ID>
RESOURCE_AS_AUDIENCE=http://localhost:8100
```

### Step 4b — Add the `hr.read` scope

1. On the AS page → **Scopes** tab → **Add Scope**
2. Fill in:
   - **Name**: `hr.read`
   - **Display name**: Read HR employee data
   - **Description**: Access HR employee profiles, departments, and org chart
3. Click **Create**

### Step 4c — Add an access policy

This tells the Custom AS to accept the JWT Bearer grant (ID-JAG → access token).

1. On the AS page → **Access Policies** tab → **Add Policy**
2. Fill in:
   - **Name**: `XAA Agent Policy`
   - **Assign to**: **All clients** (or specifically `agentpoc1-agent-service`)
3. Click **Create Policy**
4. Click **Add Rule** on the new policy
5. Fill in:
   - **Rule Name**: `Allow JWT Bearer`
   - **Grant type**: check **Token Exchange** (or **JWT Bearer** if shown separately)
   - **Scopes**: `hr.read`
   - Leave other settings at default
6. Click **Create Rule**

---

## Part 5 — Configure XAA Connection between apps

This is the step that tells Okta's **org** authorization server that `agentpoc1-agent-service` is trusted to request ID-JAGs for `agentpoc1-resource-server`.

### Steps

1. Okta Admin Console → **Applications → Applications** → click **`agentpoc1-agent-service`**
2. Click the **Manage Connections** tab (appears only after enabling the Early Access feature)
3. Click **Add apps**
4. Search for and select **`agentpoc1-resource-server`**
5. Click **Save**
6. The resource server app should now show status **Managed** in the connections list

---

## Part 6 — Summary of all values to fill in

### `agentpoc1-caa-spa/.env`

| Variable | Where to get it |
|---|---|
| `VITE_OKTA_CLIENT_ID` | Part 1 — `agentpoc1-caa-spa` Client ID |
| `VITE_OKTA_ISSUER` | Already set: `https://oie-8764513.oktapreview.com/oauth2/default` |
| `VITE_OKTA_REDIRECT_URI` | Already set: `http://localhost:5174/login/callback` |

### `agent/.env`

| Variable | Where to get it |
|---|---|
| `OKTA_AGENT_CLIENT_ID` | Part 2 — `agentpoc1-agent-service` Client ID |
| `OKTA_AGENT_PRIVATE_KEY_PATH` | Path to `agent/okta_agent_private.pem` (created in Part 2b) |
| `OKTA_AGENT_KEY_KID` | Part 2b — Key ID from the key uploaded to `agentpoc1-agent-service` |
| `OKTA_RESOURCE_APP_CLIENT_ID` | Part 3 — `agentpoc1-resource-server` Client ID |
| `OKTA_RESOURCE_AS_ID` | Part 4a — AS ID segment from the Issuer URI |
| `RESOURCE_SERVER_URL` | Already set: `http://localhost:8100` |

### `resource_server/.env`

| Variable | Where to get it |
|---|---|
| `OKTA_DOMAIN` | Already set: `https://oie-8764513.oktapreview.com` |
| `RESOURCE_AS_ID` | Part 4a — same AS ID as `OKTA_RESOURCE_AS_ID` above |
| `RESOURCE_AS_AUDIENCE` | Already set: `http://localhost:8100` |

---

## Part 7 — Test the flow end to end

### Start all three servers

```bash
# Terminal 1 — HR Resource Server
cd resource_server && uvicorn main:app --port 8100 --reload

# Terminal 2 — Agent
cd agent && uvicorn main:app --port 8000 --reload

# Terminal 3 — XAA SPA (port 5174)
cd agentpoc1-caa-spa && npm run dev
```

> The existing `poc-client-app` (port 5173) is untouched and still works as before.

### Test resource server directly (Phase 1)

```bash
curl -s -X POST http://localhost:8100/tools/call \
  -H "Authorization: Bearer local-dev" \
  -H "Content-Type: application/json" \
  -d '{"tool": "list_departments", "arguments": {}}' | python3 -m json.tool
```

Expected: list of departments returned.

### Test XAA end to end (Phase 4)

1. Open `http://localhost:5174`
2. Click **"Sign in with Okta"** → login with your Okta credentials
3. Type a prompt: `What department does user 00u1abc work in?`
4. Click **Send**

Check `agent/token_debug.txt` — it should show:
```
[1] USER → AGENT  (Okta ID token received)
[2] XAA EXCHANGE → HR RESOURCE SERVER
    token acquired ✓
```

Check the resource server terminal — it should log:
```
XAA token VALID:  sub=...  scp=hr.read
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| "Manage Connections" tab missing on app | Early Access feature not enabled | Settings → Features → Early Access → Cross App Access ON |
| XAA Step 1 returns `invalid_client` | Wrong key or KID in `agent/.env` | Verify `OKTA_AGENT_KEY_KID` matches what Okta shows; verify private key is correct |
| XAA Step 1 returns `access_denied` | Missing connection between apps | Redo Part 5 — add `agentpoc1-resource-server` to `agentpoc1-agent-service` connections |
| XAA Step 2 returns `invalid_grant` | Custom AS policy missing JWT Bearer grant | Redo Part 4c — add rule with Token Exchange / JWT Bearer grant type |
| Resource server returns 403 `hr.read` | Scope not added to Custom AS | Redo Part 4b — add `hr.read` scope |
| `Sign in with Okta` button not showing | `VITE_OKTA_CLIENT_ID` blank in SPA `.env` | Fill in from Part 1 and restart `npm run dev` |
