import { useMsal, useIsAuthenticated } from '@azure/msal-react'
import { loginRequest, isAuthConfigured } from './authConfig'
import ChatPage from './pages/ChatPage'

// ── Authenticated shell — rendered inside MsalProvider ────────────────────
function AuthApp() {
  const { instance, accounts } = useMsal()
  const isAuthenticated = useIsAuthenticated()
  const account = accounts[0] ?? null

  // Use redirect flow — simpler and more reliable than popup
  function login()  { instance.loginRedirect(loginRequest) }
  function logout() { instance.logoutRedirect() }

  return (
    <div style={{ fontFamily: 'sans-serif' }}>
      <Header
        isAuthenticated={isAuthenticated}
        name={account?.name ?? account?.username}
        onLogin={login}
        onLogout={logout}
      />
      <ChatPage account={account} instance={instance} />
    </div>
  )
}

// ── Unauthenticated shell — no MsalProvider (local dev, no .env) ──────────
function LocalApp() {
  return (
    <div style={{ fontFamily: 'sans-serif' }}>
      <Header isAuthenticated={false} />
      <ChatPage account={null} instance={null} />
    </div>
  )
}

// ── Shared header ─────────────────────────────────────────────────────────
function Header({ isAuthenticated, name, onLogin, onLogout }) {
  return (
    <header style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '12px 24px', borderBottom: '1px solid #e0e0e0', background: '#fff',
    }}>
      <span style={{ fontWeight: 700, fontSize: 16 }}>AgentPOC1</span>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {isAuthenticated ? (
          <>
            {/* Welcome message — displayed after successful Entra login */}
            <span style={{ fontSize: 14, color: '#333' }}>
              Welcome, <strong>{name}</strong>
            </span>
            <span style={{ fontSize: 11, color: '#2e7d32', background: '#e8f5e9', padding: '2px 8px', borderRadius: 10 }}>
              Authenticated
            </span>
            <button onClick={onLogout} style={{ padding: '6px 14px', cursor: 'pointer' }}>
              Sign out
            </button>
          </>
        ) : (
          <>
            <span style={{ fontSize: 11, color: '#b45309', background: '#fef3c7', padding: '2px 8px', borderRadius: 10 }}>
              {isAuthConfigured ? 'Not signed in' : 'Local dev mode'}
            </span>
            {isAuthConfigured && (
              <button onClick={onLogin} style={{ padding: '6px 14px', cursor: 'pointer' }}>
                Sign in with Microsoft
              </button>
            )}
          </>
        )}
      </div>
    </header>
  )
}

// ── Root ──────────────────────────────────────────────────────────────────
export default function App() {
  return isAuthConfigured ? <AuthApp /> : <LocalApp />
}
