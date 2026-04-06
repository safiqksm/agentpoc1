import { useState, useEffect } from 'react'
import { isOktaConfigured } from './oktaConfig'
import { getOktaUser, getOktaIdToken, loginWithOkta, logoutFromOkta } from './services/oktaAuthService'
import ChatPage from './pages/ChatPage'

export default function App() {
  const [oktaUser,    setOktaUser]    = useState(null)
  const [oktaIdToken, setOktaIdToken] = useState(null)

  // On mount, restore session if user was previously logged in
  useEffect(() => {
    getOktaUser().then(user => {
      if (user) {
        setOktaUser(user)
        getOktaIdToken().then(setOktaIdToken)
      }
    })
  }, [])

  async function handleLogin() {
    await loginWithOkta()
  }

  async function handleLogout() {
    await logoutFromOkta()
    setOktaUser(null)
    setOktaIdToken(null)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100svh', background: 'var(--az-bg)' }}>
      <Header oktaUser={oktaUser} onLogin={handleLogin} onLogout={handleLogout} />
      <ChatPage oktaUser={oktaUser} oktaIdToken={oktaIdToken} />
    </div>
  )
}

function Header({ oktaUser, onLogin, onLogout }) {
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
      {/* Left — title */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <OktaIcon />
        <span style={{ fontWeight: 600, fontSize: 15, color: '#fff', letterSpacing: '0.2px' }}>
          AgentPOC1
        </span>
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.55)', marginLeft: 4 }}>
          | XAA Demo
        </span>
      </div>

      {/* Right — auth controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {oktaUser ? (
          <>
            <span style={{ fontSize: 13, color: 'rgba(255,255,255,0.85)' }}>
              {oktaUser.email ?? oktaUser.name}
            </span>
            <Badge color="#2ecc71" bg="rgba(46,204,113,0.2)">Okta signed in</Badge>
            <HeaderButton onClick={onLogout}>Sign out</HeaderButton>
          </>
        ) : (
          <>
            <Badge color="#ffd700" bg="rgba(255,215,0,0.15)">
              {isOktaConfigured ? 'Not signed in' : 'Okta not configured'}
            </Badge>
            {isOktaConfigured && (
              <HeaderButton onClick={onLogin}>Sign in with Okta</HeaderButton>
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

function OktaIcon() {
  // Simple "O" lettermark in Okta brand colour
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="10" cy="10" r="9" stroke="#00297a" strokeWidth="2" fill="#fff"/>
      <circle cx="10" cy="10" r="4" fill="#00297a"/>
    </svg>
  )
}
