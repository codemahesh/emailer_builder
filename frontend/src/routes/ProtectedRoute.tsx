import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-neutral-50">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 rounded-lg bg-brand-primary flex items-center justify-center">
            <svg
              width="20"
              height="20"
              viewBox="0 0 20 20"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <rect x="2" y="4" width="16" height="13" rx="2.5" stroke="white" strokeWidth="1.75" />
              <path d="M2 8H18" stroke="white" strokeWidth="1.75" />
            </svg>
          </div>
          <div className="flex items-center gap-2 text-neutral-400 text-small">
            <span
              className="inline-block w-4 h-4 animate-spin rounded-full border-2 border-brand-primary border-t-transparent"
              aria-hidden="true"
            />
            Loading…
          </div>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}
