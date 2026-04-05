# Okta Setup — private_key_jwt for MCP Server

## Overview

The Org Authorization Server (used for `okta.*` management scopes) requires
`private_key_jwt`. For this POC we generate a key pair locally — no Key Vault needed.

```
MCP Server
  │  builds a signed client_assertion JWT (private key)
  ▼
POST /oauth2/v1/token  (client_credentials + private_key_jwt)
  │
  ▼  access_token  (okta.users.read, okta.users.manage, ...)
MCP Server
  │
  ▼  GET /api/v1/users  (Bearer access_token)
Okta Management API
```

---

## Part 1 — Generate Key Pair (one-time, in your terminal)

Run these commands inside the `mcp_server/` directory:

```bash
openssl genrsa -out okta_private.pem 2048
openssl rsa -in okta_private.pem -pubout -out okta_public.pem
```

This creates:
- `okta_private.pem` — kept locally, never committed, used by MCP Server to sign JWTs
- `okta_public.pem` — uploaded to Okta in Part 2

> **Add `okta_private.pem` to `.gitignore`** — treat it like a password.

---

## Part 2 — Upload Public Key to Okta

1. Go to **Admin Console** → **Applications** → **Applications**
2. Open `agentpoc1-mcp-service`
3. **General** tab → **Client Credentials** section → click **Edit**
4. Confirm **Client authentication** is set to **Public key / Private key**
5. Under **PUBLIC KEYS** → click **Add key**
6. Select **PEM** format
7. Paste the full contents of `okta_public.pem` (including `-----BEGIN PUBLIC KEY-----`)
8. Click **Done** → **Save**
9. Copy the **Key ID (kid)** shown next to the key — you'll need it for `.env`

---

## Part 3 — Grant Okta API Scopes

1. Still on `agentpoc1-mcp-service` → click the **Okta API Scopes** tab
2. Click **Grant** next to each scope:

   | Scope | Used for |
   |---|---|
   | `okta.users.read` | list_users, get_user |
   | `okta.users.manage` | create_user, deactivate_user |
   | `okta.groups.read` | get_group |
   | `okta.apps.manage` | assign_app |
   | `okta.factors.manage` | reset_mfa |

---

## Part 3b — Assign Admin Role to the Service App

Granting API scopes is not enough for write operations — the service app also needs
an **admin role** in Okta.

1. Go to **Security → Administrators**
2. Click **Add administrator**
3. In the search box type `agentpoc1-mcp-service` and select it
4. Assign role: **User Administrator**
   *(allows create_user, deactivate_user, reset_mfa)*
5. Click **Save changes**

> Without this step, `okta.users.manage` scoped calls return 403
> even though the scope is present in the token.

---

## Part 4 — Update mcp_server/.env

```
# Okta — private_key_jwt (Step 8)
OKTA_DOMAIN=https://oie-8764513.oktapreview.com
OKTA_CLIENT_ID=<your app client ID>
OKTA_PRIVATE_KEY_PATH=./okta_private.pem
OKTA_PRIVATE_KEY_KID=<kid from Part 2 step 9>
```

Remove `OKTA_CLIENT_SECRET` — it is no longer used.

---

## Verify with curl

```bash
# 1. Build a test client_assertion (use the MCP Server's built-in test endpoint after Step 8)
# 2. Or run the MCP Server and call /health — it will log the token acquisition

curl -s http://localhost:9000/health
# Then check the terminal log for: "STEP 8 — Okta token acquired"
```

---

## How client_assertion works

The MCP Server signs a short-lived JWT (5 min) and sends it as proof of identity:

```
Header:  { "alg": "RS256", "kid": "<OKTA_PRIVATE_KEY_KID>" }
Payload: {
  "iss": "<OKTA_CLIENT_ID>",
  "sub": "<OKTA_CLIENT_ID>",
  "aud": "https://oie-8764513.oktapreview.com/oauth2/v1/token",
  "iat": <now>,
  "exp": <now + 300>,
  "jti": "<uuid>"
}
Signed with: okta_private.pem (RS256)
```

Okta verifies the signature against the uploaded public key. No secret ever leaves the server.

---

## Summary

```
mcp_server/
├── okta_private.pem   ← generated locally, in .gitignore
├── okta_public.pem    ← uploaded to Okta app
└── .env
      OKTA_DOMAIN=https://oie-8764513.oktapreview.com
      OKTA_CLIENT_ID=<client id>
      OKTA_PRIVATE_KEY_PATH=./okta_private.pem
      OKTA_PRIVATE_KEY_KID=<kid>
```
