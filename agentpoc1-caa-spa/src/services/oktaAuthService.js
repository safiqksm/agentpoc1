// =============================================================================
// Okta Auth Service — thin wrapper around @okta/okta-auth-js.
//
// Manages Okta OIDC login. The key output is getOktaIdToken() — the raw ID
// token sent to the agent as Bearer so the agent performs XAA exchange.
// =============================================================================

import { OktaAuth } from '@okta/okta-auth-js';
import { oktaAuthConfig, isOktaConfigured } from '../oktaConfig';

let _oktaAuth = null;

function getOktaAuth() {
  if (!isOktaConfigured) return null;
  if (!_oktaAuth) _oktaAuth = new OktaAuth(oktaAuthConfig);
  return _oktaAuth;
}

/**
 * Handle the Okta OIDC redirect callback on app startup.
 * Call this before rendering — no-op if not returning from Okta login.
 */
export async function handleOktaCallback() {
  const auth = getOktaAuth();
  if (!auth) return;
  if (auth.isLoginRedirect()) {
    await auth.handleLoginRedirect();
  }
}

/** Start Okta PKCE login redirect. */
export async function loginWithOkta() {
  const auth = getOktaAuth();
  if (!auth) throw new Error('Okta not configured — set VITE_OKTA_CLIENT_ID in .env');
  await auth.signInWithRedirect({ originalUri: '/' });
}

/**
 * Return Okta user info from ID token claims, or null if not authenticated.
 * @returns {Promise<object|null>}
 */
export async function getOktaUser() {
  const auth = getOktaAuth();
  if (!auth) return null;
  const isAuthenticated = await auth.isAuthenticated();
  if (!isAuthenticated) return null;
  return auth.getUser();
}

/**
 * Return the raw Okta ID token JWT string.
 * This is sent to the agent as the Bearer token for the XAA flow.
 * @returns {Promise<string|null>}
 */
export async function getOktaIdToken() {
  const auth = getOktaAuth();
  if (!auth) return null;
  const tokens = await auth.tokenManager.getTokens();
  return tokens.idToken?.idToken ?? null;
}

/** Sign out from Okta and clear token cache. */
export async function logoutFromOkta() {
  const auth = getOktaAuth();
  if (!auth) return;
  await auth.signOut();
}
