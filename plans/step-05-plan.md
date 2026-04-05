# Step 5 Plan — MCP Server: Full OBO Token Validation

## Overview

The Agent now sends an OBO token (Step 4) to the MCP Server.  
The MCP Server currently decodes the token **without signature verification** (placeholder from Step 3).  
Step 5 upgrades `mcp_server/token_verifier.py` to **fully validate** the OBO token:

```
Agent  ──(OBO token)──►  MCP Server
                           │
                           ▼  verify_token(token)
                         Fetch JWKS from Entra ID
                           │
                           ▼  jose.jwt.decode(token, JWKS)
                         Check: RS256 signature ✓
                                iss = https://login.microsoftonline.com/{tenant}/v2.0 ✓
                                aud = api://{MCP_APP_ID} ✓
                                scp = mcp.call ✓
                                exp > now ✓
                           │
                           ▼  403 if any check fails
                         dispatch(tool, args)
```

---

## What We Are Building

### In Code

Update `mcp_server/token_verifier.py`:
- Fetch JWKS from Entra ID's OIDC discovery endpoint
- Cache the JWKS in memory (refreshed on `jwks_uri` fetch; 1 hour TTL)
- Verify RS256 signature using `python-jose[cryptography]`
- Validate claims: `iss`, `aud`, `scp`, `exp`
- Raise `HTTPException(403)` on any failure

Update `mcp_server/.env` (and example):
- Add `TENANT_ID`, `MCP_APP_ID` (already exist in example — just need real values)

---

## JWT Validation — Detail

### JWKS URL
```
https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys
```

### Claims to Verify

| Claim | Expected Value | Action on Failure |
|---|---|---|
| `iss` | `https://login.microsoftonline.com/{TENANT_ID}/v2.0` | 403 |
| `aud` | `api://{MCP_APP_ID}` | 403 |
| `scp` | contains `mcp.call` | 403 |
| `exp` | > current time | 403 |
| signature | RS256, key from JWKS | 403 |

### Local Dev Bypass
If `MCP_APP_ID` or `TENANT_ID` is not set:
- Skip signature verification (same as now)
- Log a warning
- Return `{"sub": "local-dev", "scp": "mcp.call"}`

---

## JWKS Caching

Entra JWKS is stable for hours; fetching on every request is wasteful.  
Simple in-memory cache:
```python
_jwks_cache: dict | None = None
_jwks_fetched_at: float = 0.0
_JWKS_TTL_SECONDS = 3600  # 1 hour
```

Analogy for Java developers: this is equivalent to a static field with a lazy-initialised `Instant` timestamp — no Spring Cache needed for this POC.

---

## Files to Create / Update

```
mcp_server/
├── token_verifier.py   ← UPDATE — full JWT validation replacing the stub
└── .env                ← add TENANT_ID, MCP_APP_ID (already in example)

mcp_server/.env copy.example  ← add TENANT_ID, MCP_APP_ID if missing
```

---

## OWASP Risk: LLM08 / AA05 — Broken Auth on Managed Identity

**Risk:** If token validation is skipped or misconfigured, any bearer token (or even
a crafted one) could call Okta tools.

**Mitigations:**
- Signature verification with Entra JWKS (RS256) — cannot be forged
- `aud` claim must match `api://{MCP_APP_ID}` — prevents token reuse from other apps
- `scp` claim must include `mcp.call` — enforces scope-based access control
- `exp` enforced — prevents replay of old tokens

---

## Success Criteria for Step 5

- [ ] Valid OBO token (aud=MCP_APP_ID, scp=mcp.call) → 200 OK, tool dispatched
- [ ] Token with wrong `aud` → 403 Forbidden
- [ ] Token with missing `scp=mcp.call` → 403 Forbidden
- [ ] Expired token → 403 Forbidden
- [ ] Non-JWT token → 403 in production mode; bypass in local dev mode
- [ ] JWKS fetched once and cached for 1 hour (not per-request)
- [ ] `POST /chat/echo` unaffected (agent route, not MCP Server)

---

## Next Step

**Step 6/7** — APIM layer (Azure API Management) sits between Agent and MCP Server.  
APIM `validate-azure-ad-token` policy pre-validates the OBO token before forwarding
to the MCP Server. The MCP Server's `token_verifier.py` remains as defence-in-depth.
