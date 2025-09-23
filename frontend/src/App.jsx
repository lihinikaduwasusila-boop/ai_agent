import React, { useEffect, useMemo, useState } from 'react'
import { getToken, setToken, clearToken } from './api.js'
import Login from './components/Login.jsx'
import Register from './components/Register.jsx'
import Search from './components/Search.jsx'
import History from './components/History.jsx'

export default function App() {
  const [view, setView] = useState('search')
  const [token, setTokenState] = useState(getToken())

  useEffect(() => {
    if (!token) setView('login')
  }, [token])

  const onLogin = (tok) => {
    setToken(tok)
    setTokenState(tok)
    setView('search')
  }

  const onLogout = () => {
    clearToken()
    setTokenState(null)
    setView('login')
  }

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, Helvetica, Arial' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid #e5e7eb' }}>
        <h1 style={{ margin: 0, fontSize: 18 }}>Legal Case Researcher</h1>
        <nav style={{ display: 'flex', gap: 12 }}>
          {token && (
            <>
              <button onClick={() => setView('search')}>Search</button>
              <button onClick={() => setView('history')}>History</button>
              <button onClick={onLogout}>Logout</button>
            </>
          )}
          {!token && (
            <>
              <button onClick={() => setView('login')}>Login</button>
              <button onClick={() => setView('register')}>Register</button>
            </>
          )}
        </nav>
      </header>

      <main style={{ padding: 16, maxWidth: 1000, margin: '0 auto' }}>
        {!token && view === 'login' && <Login onLogin={onLogin} />}
        {!token && view === 'register' && <Register onLogin={onLogin} />}
        {token && view === 'search' && <Search />}
        {token && view === 'history' && <History />}
      </main>
    </div>
  )
}