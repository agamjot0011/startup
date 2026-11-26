import { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem('wzdm_session')
    if (stored) {
      try {
        setSession(JSON.parse(stored))
      } catch (e) {
        localStorage.removeItem('wzdm_session')
      }
    }
    setLoading(false)
  }, [])

  const login = (sessionData) => {
    setSession(sessionData)
    localStorage.setItem('wzdm_session', JSON.stringify(sessionData))
  }

  const logout = () => {
    setSession(null)
    localStorage.removeItem('wzdm_session')
  }

  return (
    <AuthContext.Provider value={{ session, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
