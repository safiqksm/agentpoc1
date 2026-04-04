import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { PublicClientApplication } from '@azure/msal-browser'
import { MsalProvider } from '@azure/msal-react'
import { msalConfig, isAuthConfigured } from './authConfig'
import App from './App.jsx'
import './index.css'

async function bootstrap() {
  const root = createRoot(document.getElementById('root'))

  if (isAuthConfigured) {
    const msalInstance = new PublicClientApplication(msalConfig)
    await msalInstance.initialize()
    // Process auth code on redirect return — sets the account in MSAL cache
    await msalInstance.handleRedirectPromise()
    root.render(
      <StrictMode>
        <MsalProvider instance={msalInstance}>
          <App />
        </MsalProvider>
      </StrictMode>
    )
  } else {
    root.render(
      <StrictMode>
        <App />
      </StrictMode>
    )
  }
}

bootstrap().catch(err => {
  document.getElementById('root').innerHTML =
    `<div style="padding:40px;color:red"><b>Startup error:</b><pre>${err.message}</pre></div>`
})
