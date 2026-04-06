import { useState } from "react";

function formatTimestamp(ts) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString();
}

function isExpired(exp) {
  if (!exp) return false;
  return Date.now() > exp * 1000;
}

/** Decode JWT payload without a library (base64url → JSON). */
function decodeJwtPayload(token) {
  try {
    const [, payload] = token.split('.');
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')));
  } catch {
    return null;
  }
}

/**
 * Okta ID token panel — accepts a raw JWT string.
 * Shows decoded claims + collapsible raw JWT.
 */
export function OktaTokenPanel({ idToken }) {
  const [expanded, setExpanded]   = useState(false);
  const [showRaw,  setShowRaw]    = useState(false);
  const [copied,   setCopied]     = useState(false);

  if (!idToken) {
    return (
      <div style={{ ...panelWrap, borderColor: 'var(--az-border-mid)' }}>
        <div style={{ padding: '10px 16px', fontSize: 13, color: 'var(--az-text-secondary)' }}>
          No Okta ID token — sign in first.
        </div>
      </div>
    );
  }

  const claims  = decodeJwtPayload(idToken) || {};
  const expired = isExpired(claims.exp);

  function handleCopy() {
    navigator.clipboard.writeText(idToken).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <div style={panelWrap}>
      {/* Header toggle */}
      <button onClick={() => setExpanded(e => !e)} style={headerBtn}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--az-blue-dark)' }}>
            Okta ID Token
          </span>
          <span style={{
            fontSize: 11, fontWeight: 600,
            color:      expired ? 'var(--az-error)'   : 'var(--az-success)',
            background: expired ? 'var(--az-error-bg)': 'var(--az-success-bg)',
            padding: '1px 8px', borderRadius: 10,
          }}>
            {expired ? 'Expired' : 'Valid'}
          </span>
        </div>
        <span style={{ fontSize: 12, color: 'var(--az-blue)' }}>
          {expanded ? '▲ hide' : '▼ show'}
        </span>
      </button>

      {expanded && (
        <div style={{ padding: '12px 16px', background: '#fff' }}>
          {/* Claims table */}
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--az-bg)' }}>
                <th style={th}>Claim</th>
                <th style={th}>Value</th>
                <th style={th}>Description</th>
              </tr>
            </thead>
            <tbody>
              <ClaimRow claim="sub"   value={claims.sub}   desc="Subject — Okta user ID" />
              <ClaimRow claim="name"  value={claims.name}  desc="User display name" />
              <ClaimRow claim="email" value={claims.email || claims.preferred_username} desc="Email address" />
              <ClaimRow claim="aud"   value={Array.isArray(claims.aud) ? claims.aud.join(', ') : claims.aud} desc="Audience — SPA client ID" />
              <ClaimRow claim="iss"   value={claims.iss}   desc="Issuer — Okta AS that signed the token" />
              <ClaimRow claim="iat"   value={formatTimestamp(claims.iat)} desc={`Issued at — ${claims.iat}`} />
              <ClaimRow claim="exp"   value={formatTimestamp(claims.exp)} desc={`Expires at — ${claims.exp}`} highlight={expired} />
              <ClaimRow claim="nonce" value={claims.nonce} desc="One-time value — prevents replay" />
            </tbody>
          </table>

          {/* Raw JWT show/hide */}
          <div style={{ marginTop: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <button
                onClick={() => setShowRaw(r => !r)}
                style={smallBtn}
              >
                {showRaw ? 'Hide raw token' : 'Show raw token'}
              </button>
              <button onClick={handleCopy} style={smallBtn}>
                {copied ? 'Copied!' : 'Copy token'}
              </button>
            </div>
            {showRaw && (
              <pre style={{
                padding: '10px 12px',
                background: 'var(--az-blue-light)',
                border: '1px solid var(--az-blue-mid)',
                borderRadius: 3,
                overflowX: 'auto',
                fontSize: 11,
                fontFamily: 'var(--mono)',
                color: 'var(--az-text)',
                wordBreak: 'break-all',
                whiteSpace: 'pre-wrap',
              }}>
                {idToken}
              </pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const panelWrap = {
  marginBottom: 16,
  border: '1px solid var(--az-border)',
  borderRadius: 4,
  overflow: 'hidden',
  boxShadow: 'var(--az-shadow)',
};

const headerBtn = {
  width: '100%',
  textAlign: 'left',
  padding: '10px 16px',
  background: 'var(--az-blue-light)',
  border: 'none',
  cursor: 'pointer',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
};

const smallBtn = {
  fontSize: 12,
  padding: '3px 10px',
  border: '1px solid var(--az-blue-mid)',
  borderRadius: 3,
  cursor: 'pointer',
  background: 'var(--az-blue-light)',
  color: 'var(--az-blue-dark)',
};

// ---------------------------------------------------------------------------
// Original Entra token panel (kept for poc-client-app compatibility)
// ---------------------------------------------------------------------------

export default function TokenPanel({ account }) {
  const [expanded, setExpanded] = useState(false);
  const claims = account?.idTokenClaims || {};
  const expired = isExpired(claims.exp);

  return (
    <div style={{
      marginBottom: 16,
      border: '1px solid var(--az-border)',
      borderRadius: 4,
      overflow: 'hidden',
      boxShadow: 'var(--az-shadow)',
    }}>
      {/* Header */}
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          width: '100%',
          textAlign: 'left',
          padding: '10px 16px',
          background: 'var(--az-blue-light)',
          border: 'none',
          borderBottom: expanded ? '1px solid var(--az-blue-mid)' : 'none',
          cursor: 'pointer',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--az-blue-dark)' }}>
            OIDC Token Claims
          </span>
          <span style={{
            fontSize: 11, fontWeight: 600,
            color: expired ? 'var(--az-error)' : 'var(--az-success)',
            background: expired ? 'var(--az-error-bg)' : 'var(--az-success-bg)',
            padding: '1px 8px', borderRadius: 10,
          }}>
            {expired ? 'Expired' : 'Valid'}
          </span>
        </div>
        <span style={{ fontSize: 12, color: 'var(--az-blue)' }}>
          {expanded ? '▲ hide' : '▼ show'}
        </span>
      </button>

      {expanded && (
        <div style={{ padding: '12px 16px', background: '#fff' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: 'var(--az-bg)' }}>
                <th style={th}>Claim</th>
                <th style={th}>Value</th>
                <th style={th}>Description</th>
              </tr>
            </thead>
            <tbody>
              <ClaimRow claim="name"               value={claims.name}               desc="User's full display name" />
              <ClaimRow claim="preferred_username" value={claims.preferred_username}  desc="Login email / UPN" />
              <ClaimRow claim="email"              value={claims.email}               desc="Email address" />
              <ClaimRow claim="sub"    value={claims.sub}  desc="Subject — unique user ID within this app" />
              <ClaimRow claim="oid"    value={claims.oid}  desc="Object ID — permanent Entra identity" />
              <ClaimRow claim="tid"    value={claims.tid}  desc="Tenant ID — your Entra directory" />
              <ClaimRow claim="iss"    value={claims.iss}  desc="Issuer — who signed this token" />
              <ClaimRow claim="aud"    value={claims.aud}  desc="Audience — the app this token is for" />
              <ClaimRow claim="iat"    value={formatTimestamp(claims.iat)} desc={`Issued at — ${claims.iat}`} />
              <ClaimRow claim="exp"    value={formatTimestamp(claims.exp)} desc={`Expires at — ${claims.exp}`} highlight={expired} />
              <ClaimRow claim="ver"    value={claims.ver}  desc="Token version" />
              <ClaimRow claim="nonce"  value={claims.nonce} desc="One-time value — prevents replay" />
            </tbody>
          </table>

          <details style={{ marginTop: 12 }}>
            <summary style={{ cursor: 'pointer', fontSize: 12, color: 'var(--az-blue)', fontWeight: 600 }}>
              Raw JSON (all claims)
            </summary>
            <pre style={{ marginTop: 8, padding: '10px 12px', background: 'var(--az-blue-light)', border: '1px solid var(--az-blue-mid)', borderRadius: 3, overflowX: 'auto', fontSize: 12, fontFamily: 'var(--mono)', color: 'var(--az-text)' }}>
              {JSON.stringify(claims, null, 2)}
            </pre>
          </details>
        </div>
      )}
    </div>
  );
}

function ClaimRow({ claim, value, desc, highlight = false }) {
  return (
    <tr style={{ borderBottom: '1px solid var(--az-border)' }}
      onMouseEnter={e => e.currentTarget.style.background = 'var(--az-blue-light)'}
      onMouseLeave={e => e.currentTarget.style.background = ''}
    >
      <td style={{ ...td, color: 'var(--az-blue)', fontWeight: 600, fontFamily: 'var(--mono)', width: 160 }}>{claim}</td>
      <td style={{ ...td, color: highlight ? 'var(--az-error)' : 'var(--az-text)', wordBreak: 'break-all' }}>{value ?? '—'}</td>
      <td style={{ ...td, color: 'var(--az-text-secondary)' }}>{desc}</td>
    </tr>
  );
}

const th = {
  textAlign: 'left',
  padding: '6px 10px',
  color: 'var(--az-text-secondary)',
  fontWeight: 600,
  fontSize: 12,
  textTransform: 'uppercase',
  letterSpacing: '0.4px',
  borderBottom: '2px solid var(--az-border-mid)',
};

const td = {
  padding: '6px 10px',
  fontSize: 13,
};
