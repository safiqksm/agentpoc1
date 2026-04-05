# Entra Setup — OBO for AI (Azure OpenAI on Behalf of User)

This guide adds the Entra configuration needed so the Agent can exchange
the user's token for an Azure OpenAI-scoped token (OBO for AI).

---

## What You Are Configuring

The Agent app registration (`agentpoc1-agent`) needs permission to request
tokens scoped to Azure Cognitive Services on behalf of the signed-in user.

---

## Step 1 — Add Azure Cognitive Services API Permission

1. Go to **portal.azure.com** → search **Microsoft Entra ID** → open it

2. In the left menu click **App registrations**

3. Click **agentpoc1-agent** (client ID `6b114879-c58c-4889-9355-d5d9b19647a7`)

4. In the left menu click **API permissions**

5. Click **+ Add a permission**

6. In the "Request API permissions" panel, click **APIs my organization uses** tab

7. In the search box type **Microsoft Cognitive Services** and click the result
   (App ID in this tenant: `7d312290-28c8-473c-a0ed-8e53749b6d6d`)

8. Select **Delegated permissions**

9. Tick **user_impersonation**

10. Click **Add permissions**

You should now see this row in the permissions table:

```
API                       Permission          Type        Status
────────────────────────────────────────────────────────────────
Azure Cognitive Services  user_impersonation  Delegated   ✗ Not granted
```

---

## Step 2 — Grant Admin Consent

1. Still on the **API permissions** page

2. Click **Grant admin consent for \<your tenant name\>**

3. Click **Yes** in the confirmation dialog

The status column should now show:

```
API                       Permission          Type        Status
────────────────────────────────────────────────────────────────
Azure Cognitive Services  user_impersonation  Delegated   ✓ Granted
```

> **Why admin consent?**
> `user_impersonation` on Azure Cognitive Services is a high-privilege scope.
> Entra requires a tenant admin to pre-approve it so individual users are not
> prompted with a consent dialog on every login.

---

## Step 3 — Verify the Token Configuration (optional but recommended)

1. Still on the **agentpoc1-agent** app registration

2. In the left menu click **Manifest**

3. Confirm `"accessTokenAcceptedVersion"` is set to `null` or `1`
   (v1.0 tokens — this is what your tenant currently issues, no change needed)

4. Click **Save** if you made no changes (no action required here)

---

## Step 4 — Assign RBAC on the Azure OpenAI Resource

This is done in the **Azure resource blade**, not Entra.

1. Go to **portal.azure.com** → search **foundry3000a** → open the resource

2. In the left menu click **Access control (IAM)**

3. Click **+ Add** → **Add role assignment**

4. On the **Role** tab:
   - Search for **Cognitive Services OpenAI User**
   - Select it → click **Next**

5. On the **Members** tab:
   - Assign access to: **User, group, or service principal**
   - Click **+ Select members**
   - Search for `shafiq.ahamed@hotmail.com` → select → click **Select**
   - Click **Next** → **Review + assign**

6. Click **Review + assign** again to confirm

> **Why this role?**
> The OBO token proves who the user is, but Azure OpenAI still checks that the
> user has the `Cognitive Services OpenAI User` (or higher) RBAC role on the
> resource before allowing the call.

---

## Step 5 — Verify Setup with the Debug Token Endpoint

After completing the portal steps, call the agent's debug endpoint with a
live token to confirm the OBO exchange works for the new scope.

Run this in browser DevTools after signing in to the SPA:

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

Expected output:

```json
{
  "llm_token": {
    "aud": "https://cognitiveservices.azure.com",
    "scp": "user_impersonation",
    "sub": "<your-user-oid>",
    "iss": "https://sts.windows.net/b66066d2.../"
  },
  "llm_error": null
}
```

If `llm_error` is not null, the most common causes are:

| Error | Cause | Fix |
|---|---|---|
| `AADSTS65001` | Admin consent not granted | Repeat Step 2 |
| `AADSTS500011` | Azure Cognitive Services permission not added | Repeat Step 1 |
| `403 from Azure OpenAI` | RBAC role not assigned | Repeat Step 4 |
| `AADSTS50013` | Token audience mismatch | Check scope in obo.py |

---

## Summary Checklist

```
[ ] Step 1 — agentpoc1-agent → API permissions → Azure Cognitive Services
             → Delegated → user_impersonation → Add permissions

[ ] Step 2 — Grant admin consent for tenant

[ ] Step 3 — Manifest check (no change needed — informational only)

[ ] Step 4 — foundry3000a → IAM → Cognitive Services OpenAI User
             → assign to shafiq.ahamed@hotmail.com

[ ] Step 5 — Call /debug/token/llm and confirm aud = cognitiveservices.azure.com
```

Once all five steps are done, notify your developer to implement the code
changes described in `step-obo-for-ai-plan.md`.
