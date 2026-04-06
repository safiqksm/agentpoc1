# Entra ID Setup — Get Values for .env

## What You Need

| .env Variable | Where It Comes From |
|---|---|
| `VITE_TENANT_ID` | Your Entra ID tenant |
| `VITE_CLIENT_ID` | App Registration for the React client |
| `VITE_AGENT_SCOPE` | App Registration for the Agent backend |
| `VITE_AGENT_ENDPOINT` | Set in Step 2 (leave placeholder for now) |
| `VITE_REDIRECT_URI` | `http://localhost:5173` (no change needed) |

---

## Step A — Get Your Tenant ID

1. Go to [https://portal.azure.com](https://portal.azure.com)
2. Search for **Microsoft Entra ID** in the top search bar
3. On the **Overview** page, copy the **Tenant ID**
4. Paste it as `VITE_TENANT_ID` in your `.env`

---

## Step B — Create the Agent App Registration (backend)

> This represents the AI Agent backend that the React app will call.

1. In **Microsoft Entra ID**, go to **App registrations → New registration**
2. **Name:** `agentpoc1-agent`
3. **Supported account types:** Accounts in this organizational directory only
4. **Redirect URI:** Leave blank
5. Click **Register**
6. On the Overview page, copy the **Application (client) ID** — this is `<agent-app-id>`

**Expose a scope:**

7. In the left menu, click **Expose an API**
8. Click **Add** next to Application ID URI → accept the default (`api://<agent-app-id>`) → **Save**
9. Click **Add a scope**
   - Scope name: `agent.access`
   - Who can consent: **Admins and users**
   - Admin consent display name: `Access AgentPOC1`
   - Admin consent description: `Allows the app to call the AgentPOC1 agent`
   - State: **Enabled**
10. Click **Add scope**
11. Your full scope string is now: `api://<agent-app-id>/agent.access` → paste as `VITE_AGENT_SCOPE`

---

## Step C — Create the Client App Registration (React SPA)

1. Go to **App registrations → New registration**
2. **Name:** `poc-client-app`
3. **Supported account types:** Accounts in this organizational directory only
4. **Redirect URI:**
   - Platform: **Single-page application (SPA)**
   - URI: `http://localhost:5173`
5. Click **Register**
6. On the Overview page, copy the **Application (client) ID** → paste as `VITE_CLIENT_ID`

**Grant permission to call the Agent:**

7. In the left menu, click **API permissions → Add a permission**
8. Select **My APIs** tab
9. Select `agentpoc1-agent`
10. Select **Delegated permissions** → tick `agent.access`
11. Click **Add permissions**
12. Click **Grant admin consent for \<your tenant\>** → confirm

---

## Step D — Final .env

```
VITE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
VITE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
VITE_AGENT_SCOPE=api://xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/agent.access
VITE_AGENT_ENDPOINT=http://localhost:8000/chat
VITE_REDIRECT_URI=http://localhost:5173
```

---

## Verify It Works

1. Run `npm run dev` in `poc-client-app/`
2. Open `http://localhost:5173`
3. Click **Sign in with Microsoft** — you should be redirected to Entra ID login
4. After sign-in, open browser DevTools → Application → Session Storage
5. You should see MSAL cache entries with a token
6. Decode the token at [jwt.ms](https://jwt.ms) and confirm:
   - `aud` = `api://<agent-app-id>`
   - `scp` = `agent.access`
