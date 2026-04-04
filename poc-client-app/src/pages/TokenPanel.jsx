// =============================================================================
// TokenPanel — displays decoded OIDC token claims for verification.
//
// MSAL stores the ID token claims directly on the account object after login
// (account.idTokenClaims). No JWT decoding library needed — MSAL already
// parsed them.
//
// Claims shown:
//   Standard OIDC claims  : sub, iss, aud, iat, exp, nonce
//   Entra-specific claims : oid, tid, preferred_username, name, email
//   OAuth2 claims         : scp (scope), roles, ver
// =============================================================================

import { useState } from "react";

/**
 * Formats a Unix timestamp (seconds) to a human-readable local date/time string.
 * OIDC iat (issued at) and exp (expiry) are Unix timestamps.
 */
function formatTimestamp(ts) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString();
}

/**
 * Returns true if the token is expired based on the exp claim.
 */
function isExpired(exp) {
  if (!exp) return false;
  return Date.now() > exp * 1000;
}

/**
 * TokenPanel component.
 *
 * @param {{ account: import("@azure/msal-browser").AccountInfo }} props
 *   account — the signed-in MSAL account, which carries idTokenClaims
 */
export default function TokenPanel({ account }) {
  // Controls whether the panel is expanded or collapsed
  const [expanded, setExpanded] = useState(true); // open by default so claims are visible immediately after login

  // idTokenClaims — the decoded claims from the Entra ID ID token (OIDC)
  // This is NOT the access token — it's the identity token about the user.
  const claims = account?.idTokenClaims || {};

  const expired = isExpired(claims.exp);

  return (
    <div style={{ marginBottom: 20, border: "1px solid #c5cae9", borderRadius: 6, overflow: "hidden" }}>

      {/* ── Collapse toggle header ─────────────────────────────────────────── */}
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          width: "100%", textAlign: "left", padding: "8px 12px",
          background: "#e8eaf6", border: "none", cursor: "pointer",
          fontWeight: 600, fontSize: 13, display: "flex", justifyContent: "space-between",
        }}
      >
        <span>OIDC Token Claims (ID Token)</span>
        <span>{expanded ? "▲ hide" : "▼ show"}</span>
      </button>

      {/* ── Claims table — shown when expanded ────────────────────────────── */}
      {expanded && (
        <div style={{ padding: 12, background: "#fafafa", fontSize: 12, fontFamily: "monospace" }}>

          {/* Token status badge */}
          <div style={{ marginBottom: 10 }}>
            {expired
              ? <span style={{ background: "#fdecea", color: "#b00020", padding: "2px 8px", borderRadius: 10 }}>Token EXPIRED</span>
              : <span style={{ background: "#e8f5e9", color: "#2e7d32", padding: "2px 8px", borderRadius: 10 }}>Token VALID</span>
            }
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #ddd" }}>
                <th style={{ textAlign: "left", padding: "4px 8px", color: "#555", fontWeight: 600 }}>Claim</th>
                <th style={{ textAlign: "left", padding: "4px 8px", color: "#555", fontWeight: 600 }}>Value</th>
                <th style={{ textAlign: "left", padding: "4px 8px", color: "#555", fontWeight: 600 }}>Description</th>
              </tr>
            </thead>
            <tbody>
              {/* ── Identity claims ───────────────────────────────────────── */}
              <ClaimRow claim="name"                value={claims.name}                 desc="User's full display name" />
              <ClaimRow claim="preferred_username"  value={claims.preferred_username}   desc="Login email / UPN" />
              <ClaimRow claim="email"               value={claims.email}                desc="Email address" />

              {/* ── OIDC standard claims ──────────────────────────────────── */}
              <ClaimRow claim="sub"   value={claims.sub}   desc="Subject — unique user ID within this app" />
              <ClaimRow claim="oid"   value={claims.oid}   desc="Object ID — user's permanent Entra ID (use this for identity)" />
              <ClaimRow claim="tid"   value={claims.tid}   desc="Tenant ID — your Entra directory" />

              {/* ── Token metadata ────────────────────────────────────────── */}
              <ClaimRow claim="iss"   value={claims.iss}   desc="Issuer — who signed this token (Entra ID)" />
              <ClaimRow claim="aud"   value={claims.aud}   desc="Audience — the app this token is for (client ID)" />
              <ClaimRow claim="iat"   value={formatTimestamp(claims.iat)}  desc={`Issued at — ${claims.iat}`} />
              <ClaimRow claim="exp"   value={formatTimestamp(claims.exp)}  desc={`Expires at — ${claims.exp}`} highlight={expired} />
              <ClaimRow claim="nbf"   value={formatTimestamp(claims.nbf)}  desc={`Not before — ${claims.nbf}`} />

              {/* ── OAuth2 / Entra-specific ───────────────────────────────── */}
              <ClaimRow claim="ver"   value={claims.ver}   desc="Token version (2.0 = v2 endpoint)" />
              <ClaimRow claim="nonce" value={claims.nonce} desc="One-time value — prevents replay attacks" />
              <ClaimRow claim="aio"   value={claims.aio ? "(present)" : "—"} desc="Internal Entra opaque claim" />
            </tbody>
          </table>

          {/* Raw claims JSON — for copy/paste into jwt.ms */}
          <details style={{ marginTop: 10 }}>
            <summary style={{ cursor: "pointer", color: "#555" }}>Raw JSON (all claims)</summary>
            <pre style={{ marginTop: 8, padding: 8, background: "#f5f5f5", borderRadius: 4, overflowX: "auto", fontSize: 11 }}>
              {JSON.stringify(claims, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}

/**
 * A single row in the claims table.
 * highlight=true renders the value in red (used for expired timestamps).
 */
function ClaimRow({ claim, value, desc, highlight = false }) {
  return (
    <tr style={{ borderBottom: "1px solid #f0f0f0" }}>
      <td style={{ padding: "4px 8px", color: "#3949ab", fontWeight: 600 }}>{claim}</td>
      <td style={{ padding: "4px 8px", color: highlight ? "#b00020" : "#333", wordBreak: "break-all" }}>
        {value ?? "—"}
      </td>
      <td style={{ padding: "4px 8px", color: "#888" }}>{desc}</td>
    </tr>
  );
}
