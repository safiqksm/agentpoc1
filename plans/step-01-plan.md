# Step 1 Plan — User / Client App Sends HTTPS Request with Bearer Token

## Overview
This is the **entry point** of the system. The end user authenticates via **Microsoft Entra ID (OIDC/OAuth2 Authorization Code + PKCE)** through a React web app, enters a prompt, and the app calls the **agentpoc1** backend with the access token.

---

## What We Are Building in This Step

A **React web application** (`poc-client-app`) that:
1. Signs the user in via **MSAL.js** (Authorization Code + PKCE flow) against Microsoft Entra ID.
2. Acquires an **access token** scoped to the Agent backend (`api://<agent-app-id>/.default`).
3. Provides a **chat/prompt UI** — the user types a prompt and submits.
4. Sends an **HTTPS POST** to the agentpoc1 backend endpoint with:
   - `Authorization: Bearer <access_token>` header
   - JSON body: `{ "prompt": "<user input>" }`
5. Displays the response from the agent.

---

## Components

| Component | Detail |
|---|---|
| Client Type | React (Vite + TypeScript) |
| Auth Library | `@azure/msal-browser` + `@azure/msal-react` |
| Auth Flow | Authorization Code + PKCE (SPA — no client secret) |
| Token Issuer | Microsoft Entra ID (tenant-specific) |
| Token Audience | Agent App Registration (`api://<agent-app-id>`) |
| Transport | HTTPS |
| Target Endpoint | agentpoc1 backend (placeholder URL via `.env` until Step 2) |

---

## Entra ID App Registration Requirements (Client Side)

- **App Registration name:** `poc-client-app`
- **Platform:** Single-page application (SPA)
- **Redirect URI:** `http://localhost:5173` (Vite dev server)
- **API Permission:** Delegated scope on the Agent App Registration — e.g., `api://<agent-app-id>/agent.access`
- **No client secret** — PKCE SPA flow only
- **Token claims:** `scp` claim must contain `agent.access`; `aud` must match the agent app ID

---

## Files to Create

```
agentpoc1/
└── poc-client-app/                  # React SPA
    ├── src/
    │   ├── main.tsx                 # React entry point, MsalProvider wrapper
    │   ├── App.tsx                  # Route shell
    │   ├── authConfig.ts            # MSAL config (clientId, authority, scopes)
    │   ├── pages/
    │   │   └── ChatPage.tsx         # Prompt input + response display
    │   └── services/
    │       └── agentService.ts      # acquireTokenSilent + POST to backend
    ├── .env.example                 # Env var template (no secrets)
    ├── index.html
    ├── vite.config.ts
    ├── tsconfig.json
    └── package.json
```

### `authConfig.ts` — key values
```ts
export const msalConfig = {
  auth: {
    clientId: import.meta.env.VITE_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_TENANT_ID}`,
    redirectUri: "http://localhost:5173",
  },
};

export const agentScopes = [import.meta.env.VITE_AGENT_SCOPE];
// e.g. "api://<agent-app-id>/agent.access"
```

### `agentService.ts` — responsibilities
- Call `acquireTokenSilent` (falls back to `acquireTokenPopup`)
- POST to `VITE_AGENT_ENDPOINT` with `Authorization: Bearer <token>` and `{ "prompt": "..." }` body
- Return the agent response JSON

### `ChatPage.tsx` — UI
- Login/Logout button (MSAL `useMsal` hook)
- Text area for user prompt input
- Submit button — triggers `agentService.sendPrompt()`
- Response display area (shows agent reply or error)

### `.env.example`
```
VITE_TENANT_ID=<your-tenant-id>
VITE_CLIENT_ID=<poc-client-app-registration-id>
VITE_AGENT_SCOPE=api://<agent-app-id>/agent.access
VITE_AGENT_ENDPOINT=http://localhost:8000/chat
```

---

## OWASP Risk: LLM01 / AA01 — Prompt Injection

**Risk at this boundary:** The user-supplied prompt could contain adversarial content designed to hijack the agent's behaviour downstream.

**Mitigations planned (noted here, enforced in later steps):**
- Input length cap enforced in the React UI (e.g., max 2000 chars).
- Input length and character validation at the ingress (Step 2).
- Prompt sanitisation and system prompt separation in the Agent (Step 3).

---

## Dependencies / Assumptions

- Entra ID tenant is available and the user running the POC can create App Registrations.
- The **Agent App Registration** (Step 3) scope (`api://<agent-app-id>/agent.access`) must exist before a real token can be acquired — a **placeholder scope** is used until then.
- `VITE_AGENT_ENDPOINT` points to `http://localhost:8000/chat` (stub) until Step 2 is complete.

---

## Success Criteria for Step 1

- [ ] React app starts (`npm run dev`) and renders a login button.
- [ ] User can sign in via Entra ID — MSAL redirect/popup completes successfully.
- [ ] `acquireTokenSilent` returns a valid JWT access token with correct `aud` and `scp` claims.
- [ ] Submitting a prompt sends a POST to the backend endpoint with `Authorization: Bearer <token>`.
- [ ] A `200` or stub response is received and displayed in the UI.

---

## Out of Scope for This Step

- TLS termination (Step 2)
- OBO exchange (Step 4)
- Any agent logic

---

## Next Step
**Step 2** — ACA Ingress TLS termination and routing to the AI Agent Container.
