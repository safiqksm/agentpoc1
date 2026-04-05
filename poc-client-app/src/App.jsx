import { useMsal, useIsAuthenticated } from '@azure/msal-react'
import { loginRequest, isAuthConfigured } from './authConfig'
import ChatPage from './pages/ChatPage'

// ── Authenticated shell — rendered inside MsalProvider ────────────────────
function AuthApp() {
  const { instance, accounts } = useMsal()
  const isAuthenticated = useIsAuthenticated()
  const account = accounts[0] ?? null

  function login()  { instance.loginRedirect(loginRequest) }
  function logout() { instance.logoutRedirect() }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100svh', background: 'var(--az-bg)' }}>
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

// ── Unauthenticated shell ─────────────────────────────────────────────────
function LocalApp() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100svh', background: 'var(--az-bg)' }}>
      <Header isAuthenticated={false} />
      <ChatPage account={null} instance={null} />
    </div>
  )
}

// ── Shared header ─────────────────────────────────────────────────────────
function Header({ isAuthenticated, name, onLogin, onLogout }) {
  return (
    <header style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      padding: '0 24px',
      height: 48,
      background: 'var(--az-header-bg)',
      color: '#fff',
      boxShadow: '0 2px 4px rgba(0,0,0,.3)',
      flexShrink: 0,
    }}>
      {/* Left — Azure logo + app name */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <AzureIcon />
        <span style={{ fontWeight: 600, fontSize: 15, color: '#fff', letterSpacing: '0.2px' }}>
          AgentPOC1
        </span>
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.55)', marginLeft: 4 }}>
          | Okta Agent
        </span>
      </div>

      {/* Right — auth controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {isAuthenticated ? (
          <>
            <span style={{ fontSize: 13, color: 'rgba(255,255,255,0.85)' }}>
              {name}
            </span>
            <Badge color="#2ecc71" bg="rgba(46,204,113,0.2)">Signed in</Badge>
            <HeaderButton onClick={onLogout}>Sign out</HeaderButton>
          </>
        ) : (
          <>
            <Badge color="#ffd700" bg="rgba(255,215,0,0.15)">
              {isAuthConfigured ? 'Not signed in' : 'Local dev'}
            </Badge>
            {isAuthConfigured && (
              <HeaderButton onClick={onLogin}>Sign in with Microsoft</HeaderButton>
            )}
          </>
        )}
      </div>
    </header>
  )
}

function Badge({ color, bg, children }) {
  return (
    <span style={{
      fontSize: 11, fontWeight: 600,
      color, background: bg,
      padding: '2px 8px', borderRadius: 10,
      border: `1px solid ${color}40`,
    }}>
      {children}
    </span>
  )
}

function HeaderButton({ onClick, children }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '5px 14px',
        fontSize: 13,
        cursor: 'pointer',
        background: 'rgba(255,255,255,0.12)',
        color: '#fff',
        border: '1px solid rgba(255,255,255,0.3)',
        borderRadius: 3,
        transition: 'background 0.15s',
      }}
      onMouseEnter={e => e.target.style.background = 'rgba(255,255,255,0.22)'}
      onMouseLeave={e => e.target.style.background = 'rgba(255,255,255,0.12)'}
    >
      {children}
    </button>
  )
}

function AzureIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M33.338 7.166L11.94 60.735l21.122 2.75L53.957 21.4 33.338 7.166z" fill="#0089d6"/>
      <path d="M36.666 64.064l38.056 6.602L96 88.835H18.21l18.456-24.77z" fill="#0089d6"/>
      <path d="M53.957 21.4L33.338 63.485l3.328.579L62.39 29.8 53.957 21.4z" fill="#0060aa"/>
    </svg>
  )
}

// ── Root ──────────────────────────────────────────────────────────────────
export default function App() {
  return isAuthConfigured ? <AuthApp /> : <LocalApp />
}
