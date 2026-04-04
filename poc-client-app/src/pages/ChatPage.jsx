import { useState } from "react";
import { sendPrompt } from "../services/agentService";
import TokenPanel from "./TokenPanel";

const MAX_PROMPT_LENGTH = 2000;

/**
 * ChatPage — receives account + instance as props from App.
 * Works in both authenticated (real token) and unauthenticated (local dev) modes.
 */
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
    <div style={{ maxWidth: 720, margin: "40px auto", padding: "0 16px", fontFamily: "sans-serif" }}>
      <h2>AgentPOC1 — Chat</h2>

      {/* Auth status line */}
      <p style={{ color: "#666", fontSize: 13, marginBottom: 12 }}>
        {account
          ? <>Signed in as <strong>{account.username}</strong> — sending real Entra token</>
          : <>Local dev mode — sending placeholder token (no login required)</>
        }
      </p>

      {/* OIDC token claims — only shown when signed in */}
      {account && <TokenPanel account={account} />}

      {/* Prompt form */}
      <form onSubmit={handleSubmit}>
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value.slice(0, MAX_PROMPT_LENGTH))}
          placeholder="Enter your prompt... (e.g. 'List all Okta users')"
          rows={5}
          style={{ width: "100%", padding: 8, fontSize: 14, boxSizing: "border-box" }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8 }}>
          <span style={{ fontSize: 12, color: prompt.length > MAX_PROMPT_LENGTH * 0.9 ? "#b45309" : "#999" }}>
            {prompt.length} / {MAX_PROMPT_LENGTH}
          </span>
          <button type="submit" disabled={loading || !prompt.trim()} style={{ padding: "8px 20px" }}>
            {loading ? "Sending..." : "Send"}
          </button>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div style={{ marginTop: 16, padding: 12, background: "#fdecea", color: "#b00020", borderRadius: 4 }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Response */}
      {response && (
        <div style={{ marginTop: 16 }}>
          <div style={{ padding: 12, background: "#f1f8e9", borderRadius: 4 }}>
            <strong>Agent Reply:</strong>
            <pre style={{ whiteSpace: "pre-wrap", marginTop: 8, fontSize: 13 }}>{response.reply}</pre>
          </div>
          {response.tools_called?.length > 0 && (
            <div style={{ marginTop: 8, padding: 12, background: "#e8f0fe", borderRadius: 4 }}>
              <strong>Tools called:</strong>
              <pre style={{ whiteSpace: "pre-wrap", marginTop: 8, fontSize: 12 }}>
                {JSON.stringify(response.tools_called, null, 2)}
              </pre>
            </div>
          )}
          <div style={{ marginTop: 4, fontSize: 11, color: "#999" }}>
            model: {response.model} &nbsp;|&nbsp; token: {response.token_preview}
          </div>
        </div>
      )}
    </div>
  );
}
