import React, { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'

function getErrorMessage(error: unknown): string {
  // Check AxiosError response detail first (AxiosError extends Error, so instanceof check must come after)
  const axiosLike = error as { response?: { data?: { detail?: string } } }
  const detail = axiosLike?.response?.data?.detail
  if (detail === 'LOGIN_BAD_CREDENTIALS') {
    return 'Invalid email or password. Please try again.'
  }
  if (detail) return detail
  if (error instanceof Error) return error.message
  return 'An unexpected error occurred. Please try again.'
}

export function LoginPage() {
  const { login, isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (!isLoading && isAuthenticated) {
    return <Navigate to="/campaigns" replace />
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim() || !password) return

    setIsSubmitting(true)
    setError('')

    try {
      await login(email.trim(), password)
      navigate('/campaigns', { replace: true })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50 px-4">
      <div className="w-login-card bg-neutral-0 rounded-lg shadow-elev-raised border border-neutral-100 p-8">
        {/* Header */}
        <div className="flex flex-col items-center gap-3 mb-8">
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
              <path d="M6 12H14" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
              <path d="M6 15H10" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </div>
          <div className="text-center">
            <h1 className="text-heading-2 text-neutral-900">Email Builder</h1>
            <p className="text-body text-neutral-400 mt-1">Sign in to your account</p>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
          <Input
            label="Email address"
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value)
              if (error) setError('')
            }}
            error={error && !email ? 'Email is required' : undefined}
            disabled={isSubmitting}
            required
          />

          <Input
            label="Password"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value)
              if (error) setError('')
            }}
            error={error && !password ? 'Password is required' : undefined}
            disabled={isSubmitting}
            required
          />

          {/* Global auth error */}
          {error && email && password && (
            <div
              className="px-3 py-2 rounded-md bg-danger-50 border border-danger-600"
              role="alert"
            >
              <p className="text-small text-danger-600">{error}</p>
            </div>
          )}

          <Button
            type="submit"
            variant="primary"
            size="lg"
            fullWidth
            isLoading={isSubmitting}
            disabled={!email.trim() || !password || isSubmitting}
            className="mt-2"
          >
            Sign in
          </Button>
        </form>
      </div>
    </div>
  )
}
