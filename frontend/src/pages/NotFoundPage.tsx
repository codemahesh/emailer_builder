import React from 'react'
import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50 px-4">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 rounded-2xl bg-brand-primary-soft flex items-center justify-center mx-auto mb-6">
          <span className="text-3xl font-bold text-brand-primary">?</span>
        </div>
        <h1 className="text-display text-neutral-900 mb-3">Page not found</h1>
        <p className="text-body text-neutral-400 mb-8">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <Link
          to="/campaigns"
          className="inline-flex items-center justify-center h-11 px-6 rounded-md bg-brand-primary text-neutral-0 text-body-strong hover:bg-brand-primary-hover transition-colors"
        >
          Go to Campaigns
        </Link>
      </div>
    </div>
  )
}
