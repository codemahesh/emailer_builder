import React, {
  createContext,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'
import {
  getMeRequest,
  loginRequest,
  logoutRequest,
  type UserRead,
} from '../lib/api'

export interface AuthContextValue {
  user: UserRead | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<UserRead | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const isMounted = useRef(true)

  useEffect(() => {
    isMounted.current = true
    return () => {
      isMounted.current = false
    }
  }, [])

  // Try to restore session from localStorage token
  useEffect(() => {
    const restoreSession = async () => {
      const token = localStorage.getItem('access_token')
      if (!token) {
        setIsLoading(false)
        return
      }
      try {
        const me = await getMeRequest()
        if (isMounted.current) setUser(me)
      } catch {
        localStorage.removeItem('access_token')
      } finally {
        if (isMounted.current) setIsLoading(false)
      }
    }

    restoreSession()
  }, [])

  // Listen for global 401 events from the axios interceptor
  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null)
    }
    window.addEventListener('auth:unauthorized', handleUnauthorized)
    return () => {
      window.removeEventListener('auth:unauthorized', handleUnauthorized)
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await loginRequest(email, password)
    localStorage.setItem('access_token', access_token)
    const me = await getMeRequest()
    setUser(me)
  }, [])

  const logout = useCallback(async () => {
    try {
      await logoutRequest()
    } catch {
      // Swallow server errors; clear local state regardless
    } finally {
      localStorage.removeItem('access_token')
      setUser(null)
    }
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: user !== null,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
