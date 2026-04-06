// =============================================================================
// Agent Service — XAA SPA version.
//
// Sends the Okta ID token as Bearer + X-Auth-Provider: okta so the agent
// performs the XAA two-step exchange instead of Entra OBO.
//
// If no Okta token is present (user not logged in), falls back to "local-dev"
// so you can still test the agent without authentication.
// =============================================================================

/**
 * Send a prompt to the agent backend.
 *
 * @param {string} prompt - user message (max 2000 chars)
 * @param {string|null} oktaIdToken - raw Okta ID token JWT from getOktaIdToken()
 * @returns {Promise<object>} { reply, model, tools_called, token_preview }
 */
export async function sendPrompt(prompt, oktaIdToken = null) {
  const token        = oktaIdToken ?? 'local-dev';
  const authProvider = oktaIdToken ? 'okta' : 'none';

  const endpoint = import.meta.env.VITE_AGENT_ENDPOINT;
  if (!endpoint) {
    throw new Error("VITE_AGENT_ENDPOINT is not set in .env");
  }

  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type":    "application/json",
      "Authorization":   `Bearer ${token}`,
      "X-Auth-Provider": authProvider,
    },
    body: JSON.stringify({ prompt }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Agent error ${response.status}: ${text}`);
  }

  return response.json();
}
