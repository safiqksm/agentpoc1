# Step 2 Plan — ACA Ingress (TLS Termination + Routing to Agent)

## Overview
The React client app (Step 1) sends an HTTPS request with a Bearer token. This step defines the **Azure Container Apps (ACA) Environment and Ingress** that:
1. Terminates TLS (HTTPS → HTTP internally)
2. Validates the incoming request has an `Authorization` header (basic guard)
3. Routes to the **AI Agent Container** (Step 3)

For **local development**, this is replaced by a simple **FastAPI app** running on `http://localhost:8000` that accepts the Bearer token and returns a stub response — so the React app has something to call right now.

---

## Two-Track Approach

| Track | Purpose |
|---|---|
| **Local (this step)** | FastAPI stub on `localhost:8000` — validates Bearer token presence, echoes prompt back |
| **Azure (later)** | Azure Container Apps Environment + Ingress YAML — TLS, routing, rate limiting |

We implement the **local track** now so the full local loop works (React → Agent stub → response). The Azure infra track is documented here as the deployment target.

---

## Local Track — What We Are Building

A **FastAPI Python app** (`agentpoc1/`) that:
1. Listens on `http://localhost:8000`
2. Accepts `POST /chat` with `Authorization: Bearer <token>` and `{ "prompt": "..." }` body
3. Validates the Bearer token is present (signature verification added in Step 4)
4. Returns a stub JSON response: `{ "reply": "Echo: <prompt>" }`
5. Enforces input length (max 2000 chars) — OWASP LLM01 mitigation

---

## Files to Create

```
agentpoc1/
└── agent/
    ├── main.py            # FastAPI app — /chat endpoint
    ├── requirements.txt   # fastapi, uvicorn, python-jose
    ├── .env.example       # TENANT_ID, CLIENT_ID, AGENT_APP_ID (for token validation later)
    └── README.md          # How to run
```

### `main.py` — responsibilities
- `POST /chat` — extract Bearer token from `Authorization` header, validate presence
- Parse `{ "prompt": "..." }` body, enforce max length 2000
- Return `{ "reply": "Echo: <prompt>", "token_preview": "<first 20 chars of token>..." }`
- CORS enabled for `http://localhost:5173` (React dev server)

### `requirements.txt`
```
fastapi
uvicorn[standard]
python-jose[cryptography]
python-dotenv
httpx
```

---

## Azure Track — ACA Ingress Configuration (Documentation)

When deploying to Azure Container Apps:

- **Ingress type:** External (HTTPS)
- **TLS:** Managed certificate (ACA handles Let's Encrypt / custom domain)
- **Target port:** 8000 (internal HTTP to the agent container)
- **Transport:** HTTP/1.1
- **CORS policy:** Restricted to the SPA origin
- **Traffic rules:** 100% to the latest revision

Bicep snippet (for reference — not deployed in this step):
```bicep
ingress: {
  external: true
  targetPort: 8000
  transport: 'http'
  corsPolicy: {
    allowedOrigins: ['https://<spa-domain>']
    allowedMethods: ['POST', 'OPTIONS']
    allowedHeaders: ['Authorization', 'Content-Type']
  }
}
```

---

## OWASP Risk: LLM01 / AA01 — Prompt Injection

**Mitigations at this layer:**
- Max prompt length enforced (2000 chars) — rejects oversized payloads before they reach the LLM
- `Authorization` header required — unauthenticated requests rejected with `401`
- CORS restricted to known SPA origin — prevents cross-origin abuse

---

## Success Criteria for Step 2

- [ ] `uvicorn agent.main:app --reload` starts without errors
- [ ] `POST http://localhost:8000/chat` with a Bearer token and `{ "prompt": "hello" }` returns `{ "reply": "Echo: hello" }`
- [ ] Request without `Authorization` header returns `401`
- [ ] Prompt over 2000 chars returns `422`
- [ ] React app (Step 1) can call the local agent and display the echo response

---

## Out of Scope for This Step

- Real token signature validation (Step 4 — OBO)
- OBO exchange (Step 4)
- LLM calls (Step 13)
- Azure deployment (covered when we wire up full infra)

---

## Next Step
**Step 3** — AI Agent Container: orchestration logic, MCP client, session management, Managed Identity setup.
