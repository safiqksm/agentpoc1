import { useState } from "react";
import { sendPrompt } from "../services/agentService";
import TokenPanel from "./TokenPanel";

const MAX_PROMPT_LENGTH = 2000;

export default function ChatPage({ account, instance }) {
  const [prompt,   setPrompt]   = useState("");
  const [response, setResponse] = useState(null);
  const [error,    setError]    = useState(null);
  const [loading,  setLoading]  = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const result = await sendPrompt(instance, account, prompt.trim());
      setResponse(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ flex: 1, padding: '24px', maxWidth: 860, width: '100%', margin: '0 auto', boxSizing: 'border-box' }}>

      {/* Page title */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 20, fontWeight: 600, color: 'var(--az-text)', margin: 0 }}>
          Okta Agent Chat
        </h2>
        <p style={{ color: 'var(--az-text-secondary)', fontSize: 13, marginTop: 4 }}>
          {account
            ? <>Signed in as <strong>{account.username}</strong> — Entra token active</>
            : <>Local dev mode — no authentication required</>
          }
        </p>
      </div>

      {/* Token claims panel */}
      {account && <TokenPanel account={account} />}

      {/* Prompt card */}
      <div style={card}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--az-text-secondary)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Prompt
        </div>
        <form onSubmit={handleSubmit}>
          <textarea
            value={prompt}
            onChange={e => setPrompt(e.target.value.slice(0, MAX_PROMPT_LENGTH))}
            placeholder="e.g. List all active Okta users"
            rows={4}
            style={{
              width: '100%',
              padding: '10px 12px',
              fontSize: 14,
              boxSizing: 'border-box',
              border: '1px solid var(--az-border-mid)',
              borderRadius: 3,
              fontFamily: 'var(--sans)',
              resize: 'vertical',
              outline: 'none',
              transition: 'border-color 0.15s',
              background: '#fff',
              color: 'var(--az-text)',
            }}
            onFocus={e => e.target.style.borderColor = 'var(--az-blue)'}
            onBlur={e => e.target.style.borderColor = 'var(--az-border-mid)'}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
            <span style={{ fontSize: 12, color: prompt.length > MAX_PROMPT_LENGTH * 0.9 ? 'var(--az-warning)' : 'var(--az-text-secondary)' }}>
              {prompt.length} / {MAX_PROMPT_LENGTH}
            </span>
            <button
              type="submit"
              disabled={loading || !prompt.trim()}
              style={{
                padding: '7px 20px',
                fontSize: 14,
                fontWeight: 600,
                cursor: loading || !prompt.trim() ? 'not-allowed' : 'pointer',
                background: loading || !prompt.trim() ? 'var(--az-border-mid)' : 'var(--az-blue)',
                color: loading || !prompt.trim() ? 'var(--az-text-secondary)' : '#fff',
                border: 'none',
                borderRadius: 3,
                transition: 'background 0.15s',
              }}
              onMouseEnter={e => { if (!loading && prompt.trim()) e.target.style.background = 'var(--az-blue-dark)' }}
              onMouseLeave={e => { if (!loading && prompt.trim()) e.target.style.background = 'var(--az-blue)' }}
            >
              {loading ? 'Sending…' : 'Send'}
            </button>
          </div>
        </form>
      </div>

      {/* Error */}
      {error && (
        <div style={{ ...card, borderLeft: '4px solid var(--az-error)', background: 'var(--az-error-bg)', marginTop: 16 }}>
          <strong style={{ color: 'var(--az-error)' }}>Error</strong>
          <p style={{ marginTop: 6, fontSize: 13, color: 'var(--az-text)' }}>{error}</p>
        </div>
      )}

      {/* Response */}
      {response && (
        <div style={{ marginTop: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>

          {/* Agent reply */}
          <div style={{ ...card, borderLeft: '4px solid var(--az-blue)' }}>
            <div style={sectionLabel}>Agent Reply</div>
            <pre style={{ whiteSpace: 'pre-wrap', margin: '8px 0 0', fontSize: 13, color: 'var(--az-text)', fontFamily: 'var(--sans)', lineHeight: '1.6' }}>
              {response.reply}
            </pre>
          </div>

          {/* Tools called */}
          {response.tools_called?.length > 0 && (
            <div style={{ ...card, borderLeft: '4px solid var(--az-blue-dark)' }}>
              <div style={sectionLabel}>Tools Called ({response.tools_called.length})</div>
              <pre style={{ whiteSpace: 'pre-wrap', margin: '8px 0 0', fontSize: 12, color: 'var(--az-text)', fontFamily: 'var(--mono)', background: 'var(--az-blue-light)', padding: '10px 12px', borderRadius: 3, overflowX: 'auto' }}>
                {JSON.stringify(response.tools_called, null, 2)}
              </pre>
            </div>
          )}

          {/* Footer metadata */}
          <div style={{ fontSize: 12, color: 'var(--az-text-secondary)', padding: '0 4px', display: 'flex', gap: 16 }}>
            <span>Model: <code style={{ fontSize: 12 }}>{response.model}</code></span>
            <span>Token: <code style={{ fontSize: 12 }}>{response.token_preview}</code></span>
          </div>

        </div>
      )}
    </div>
  );
}

const card = {
  background: 'var(--az-surface)',
  border: '1px solid var(--az-border)',
  borderRadius: 4,
  padding: '16px 20px',
  boxShadow: 'var(--az-shadow)',
};

const sectionLabel = {
  fontSize: 12,
  fontWeight: 600,
  color: 'var(--az-text-secondary)',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
};
