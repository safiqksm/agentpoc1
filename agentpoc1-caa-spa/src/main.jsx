import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { isOktaConfigured } from './oktaConfig'
import App from './App.jsx'
import './index.css'

async function bootstrap() {
  const root = createRoot(document.getElementById('root'))

  // Handle Okta redirect callback — exchanges auth code for tokens.
  // Safe to call on every page load; no-op if not returning from Okta login.
  if (isOktaConfigured) {
    const { handleOktaCallback } = await import('./services/oktaAuthService.js')
    await handleOktaCallback()
  }

  root.render(
    <StrictMode>
      <App />
    </StrictMode>
  )
}

bootstrap().catch(err => {
  document.getElementById('root').innerHTML =
    `<div style="padding:40px;color:red"><b>Startup error:</b><pre>${err.message}</pre></div>`
})
