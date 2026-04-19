Here's the full step-by-step walkthrough of the diagram:

---

## Diagram: Azure AI Foundry — Agent + Okta MCP Server via APIM | OBO Auth Chain + OWASP Risk Badges

---

### **Step 1 — User / Client App sends a request**
The **End User / Client App** makes an **HTTPS call with a Bearer Token** to the system.
- This is the entry point — the user has already authenticated (e.g., via Entra ID / OIDC) and holds an access token.
- **OWASP Risk:** `LLM01 / AA01` — Prompt Injection risk at this boundary.

---

### **Step 2 — Request hits the ACA Ingress (TLS termination)**
The request arrives at the **Azure Container Apps Ingress** (HTTPS / TLS).
- TLS is terminated here before routing inward.
- **OWASP Risk:** `LLM01 / AA01` — same prompt injection concern at the ingress layer.

---

### **Step 3 — Ingress routes to the AI Agent Container**
The ingress forwards the request to the **AI Agent Container App** running inside the Azure Container Apps Environment.
- The Agent holds: orchestration logic, prompt engineering, MCP Client role, tool/function calling, session management, Managed Identity, and App Registration + Certificate (needed for OBO).
- **OWASP Risk:** `LLM06 / AA03` — Excessive Agency risk (the agent is a confidential client with real delegated power).

---

### **Step 4 — Agent performs OBO Token Exchange via Managed Identity**
The Agent uses its **Managed Identity (System-Assigned)** and its **App Registration + Certificate** to perform an **On-Behalf-Of (OBO) token exchange** with **Microsoft Entra ID**.
- The user's incoming Bearer Token is exchanged for an **OBO token** — a delegated token scoped to the downstream resource (APIM/MCP).
- Entra ID is the token authority here.
- **OWASP Risk:** `LLM08 / AA05` — Broken Auth risk on the Managed Identity and Entra configuration.

---

### **Step 5 — Agent calls Azure API Management with the OBO Token**
The Agent sends a **POST to `/mcp/okta`** on **Azure API Management (APIM)** with the OBO token in the Authorization header.
- This is the thick orange arrow — the primary MCP tool call path.
- APIM endpoint: `https://apim.contoso.azure-api.net/mcp/okta`
- **OWASP Risk:** `LLM08 / AA05` on APIM.

---

### **Step 6 — APIM validates the OBO token (local JWT validation)**
APIM runs the **`validate-azure-ad-token` policy** — this is a **local JWT validation** (no runtime call to Entra per request).
- It checks: issuer, audience (App ID), `scp` claims, and token expiry.
- Entra ID provides the JWKS/metadata at setup, but validation happens in-policy.
- Rate limiting is applied per Agent identity.
- On success, APIM routes to the MCP Server backend.
- **OWASP Risk:** `LLM07 / AA04` — Tool Misuse risk; APIM enforces scope (`scp`) claim validation here.

---

### **Step 7 — APIM forwards the request + OBO Token to the MCP Server**
APIM passes the validated request (with the OBO token) forward to the **MCP Server Container** (Custom Okta MCP).
- Transport: **Streamable HTTP POST** (MCP Spec 2025-03-26).
- **OWASP Risk:** `LLM07 / AA04` on the MCP Server.

---

### **Step 8 — MCP Server validates the OBO token scope**
The MCP Server first **validates the incoming OBO token's scope** to ensure it's authorized to proceed.

---

### **Step 9 — MCP Server retrieves the Private Key from Azure Key Vault**
The MCP Server uses its **Managed Identity** to pull a **private key (PFX/exportable secret)** from **Azure Key Vault**.
- The key is stored as a **secret** (not a cert object) — accessed via MI, not a password.
- **OWASP Risk:** `LLM08 / AA05` on Key Vault.

---

### **Step 10 — MCP Server signs a JWT client_assertion and calls Okta's token endpoint**
Using the retrieved private key, the MCP Server:
1. **Signs a JWT `client_assertion`** (Private Key JWT).
2. POSTs to **Okta's `/oauth2/v1/token`** endpoint using `client_credentials` + the signed JWT.
- **The private key never leaves the MCP Server** — only the signed assertion is sent on the wire.
- Okta sees the **MCP Server's identity**, not the end user's.
- **OWASP Risk:** `LLM09 / AA06` — Insecure Plugin risk; mitigated here by signed assertion and narrowest scopes.

---

### **Step 11 — MCP Server calls the Okta REST API with the Bearer Token**
Armed with the Okta access token, the MCP Server calls the relevant **Okta REST API** endpoint:
- Users API (`/api/v1/users`)
- Groups API (`/api/v1/groups`)
- Apps API (`/api/v1/apps`)
- Factors API (`/users/{id}/factors`)

Available **MCP Tools** include: `list_users`, `create_user`, `assign_app`, `deactivate_user`, `reset_mfa`, `get_group`.

---

### **Step 12 — MCP Server returns JSON result → APIM → Agent**
- MCP Server returns the **JSON result** to APIM.
- APIM returns the **Tool Result (sync)** back to the Agent.

---

### **Step 13 — Agent calls the LLM (Azure AI Foundry)**
The Agent calls the **LLM (GPT-4o / Phi-4)** via the **Foundry/OpenAI endpoint** using a **Managed Identity token** (scope: `ai.azure.com/.default`).
- The AI Foundry Hub contains the Project which deploys the LLM.
- Content Safety and Rate Limiting are applied at this layer.
- **OWASP Risk:** `LLM02 / AA02` — Sensitive Info Disclosure (LLM may leak PII from tool results; filter before re-injection).

---

### **Step 14 — LLM returns Completion to the Agent**
The LLM sends the **Completion** back to the Agent, which incorporates the tool result and generates the final response for the user.

---

Ready for your next prompt — deeper dive on any step, the OWASP badges, the OBO chain, or anything else.