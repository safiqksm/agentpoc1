// =============================================================================
// Agent Service — handles communication between the SPA and the Agent backend.
//
// Two modes depending on whether the user is logged in:
//   Authenticated   : acquires a real Entra ID access token, sends it as Bearer
//   Unauthenticated : sends a placeholder token "local-dev" so the agent still
//                     works for local testing without Entra ID configured.
// =============================================================================

import { agentTokenRequest } from "../authConfig";

/**
 * Acquires an Entra ID access token for the Agent backend.
 *
 * 1. Tries silently (uses cached token from sessionStorage — no UI shown).
 * 2. Falls back to a popup if silent acquisition fails (e.g. token expired).
 *
 * @param {import("@azure/msal-browser").IPublicClientApplication} msalInstance
 * @param {import("@azure/msal-browser").AccountInfo} account - the signed-in user
 * @returns {Promise<string>} the raw access token JWT string
 */
async function acquireToken(msalInstance, account) {
  try {
    // Silent path — returns immediately if a valid cached token exists
    const tokenResponse = await msalInstance.acquireTokenSilent({
      ...agentTokenRequest,
      account,
    });
    return tokenResponse.accessToken;
  } catch {
    // Silent failed — use redirect to refresh (consistent with loginRedirect flow)
    await msalInstance.acquireTokenRedirect({ ...agentTokenRequest, account });
    return ""; // redirect navigates away; this line is never reached
  }
}

/**
 * Sends a prompt to the Agent backend and returns the parsed JSON response.
 *
 * Authenticated mode  (account != null):
 *   - Acquires a real Entra ID Bearer token via MSAL
 *   - Sends: Authorization: Bearer <real-jwt>
 *
 * Unauthenticated mode (account == null — local dev, no Entra config):
 *   - Uses a placeholder token "local-dev"
 *   - Sends: Authorization: Bearer local-dev
 *   - The Agent accepts this because token signature validation is not yet
 *     enforced (added in Step 4)
 *
 * @param {import("@azure/msal-browser").IPublicClientApplication} msalInstance
 * @param {import("@azure/msal-browser").AccountInfo | undefined} account
 * @param {string} prompt - the user's message (max 2000 chars enforced by UI)
 * @returns {Promise<object>} { reply, model, tools_called, token_preview }
 */
export async function sendPrompt(msalInstance, account, prompt) {
  // Decide which token to use based on auth state
  let token;
  if (account) {
    // Authenticated — get a real Entra ID access token
    token = await acquireToken(msalInstance, account);
  } else {
    // Unauthenticated — local dev placeholder (bypasses token validation)
    token = "local-dev";
  }

  const endpoint = import.meta.env.VITE_AGENT_ENDPOINT;
  if (!endpoint) {
    throw new Error("VITE_AGENT_ENDPOINT is not set in .env");
  }

  // POST to the Agent backend with the Bearer token and prompt body
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type":  "application/json",
      "Authorization": `Bearer ${token}`,
    },
    body: JSON.stringify({ prompt }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Agent error ${response.status}: ${text}`);
  }

  return response.json();
}
