// =============================================================================
// MSAL configuration for Microsoft Entra ID (Azure AD) authentication.
//
// Values come from .env file (VITE_ prefix = exposed to browser by Vite).
// See ENTRA_SETUP.md for how to create these App Registrations.
//
// LOCAL DEV MODE: if VITE_CLIENT_ID is not set, MSAL is not initialised and
// the app runs without any authentication (unauthenticated mode).
// =============================================================================

/**
 * Core MSAL config — tells the library which Entra tenant + app to use.
 * clientId   : the App Registration for this React SPA (poc-client-app)
 * authority  : the Entra ID login URL for your tenant
 * redirectUri: where Entra sends the user back after login
 * cacheLocation: "sessionStorage" — token cache lives in the browser tab only
 */
export const msalConfig = {
  auth: {
    clientId:    import.meta.env.VITE_CLIENT_ID,
    authority:   `https://login.microsoftonline.com/${import.meta.env.VITE_TENANT_ID}`,
    redirectUri: import.meta.env.VITE_REDIRECT_URI || "http://localhost:5173",
  },
  cache: {
    cacheLocation:        "sessionStorage", // cleared when browser tab closes
    storeAuthStateInCookie: false,
  },
};

/**
 * Scopes requested during login (OIDC — who the user is).
 * openid  : required for OIDC — enables ID token
 * profile : adds name/preferred_username claims
 * email   : adds email claim
 */
export const loginRequest = {
  scopes: ["openid", "profile", "email"],
};

/**
 * Scopes requested when acquiring a token for the Agent backend (OAuth2).
 * VITE_AGENT_SCOPE = api://<agent-app-id>/agent.access
 * This is the access token forwarded to the Agent in the Authorization header.
 */
export const agentTokenRequest = {
  scopes: [import.meta.env.VITE_AGENT_SCOPE],
};

/**
 * True if Entra ID env vars are configured.
 * Used to decide whether to show the Login button or run in unauthenticated mode.
 */
export const isAuthConfigured =
  !!import.meta.env.VITE_CLIENT_ID && !!import.meta.env.VITE_TENANT_ID;
