// =============================================================================
// Okta OIDC configuration — XAA (Cross App Access) SPA.
//
// Required .env vars:
//   VITE_OKTA_CLIENT_ID   — agentpoc1-caa-spa Okta app client ID
//   VITE_OKTA_ISSUER      — https://oie-8764513.oktapreview.com/oauth2/default
//   VITE_OKTA_REDIRECT_URI — http://localhost:5174/login/callback
// =============================================================================

export const oktaAuthConfig = {
  clientId:    import.meta.env.VITE_OKTA_CLIENT_ID,
  issuer:      import.meta.env.VITE_OKTA_ISSUER,
  redirectUri: import.meta.env.VITE_OKTA_REDIRECT_URI || `${window.location.origin}/login/callback`,
  scopes:      ['openid', 'profile', 'email'],
  pkce:        true,
};

/** True when Okta env vars are present in the build. */
export const isOktaConfigured =
  !!import.meta.env.VITE_OKTA_CLIENT_ID && !!import.meta.env.VITE_OKTA_ISSUER;
