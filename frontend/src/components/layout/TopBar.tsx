import React, { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { StatusPill } from '../ui/Pill'
import type { CampaignStatus } from '../../lib/api'

interface BreadcrumbItem {
  label: string
  href?: string
}

interface TopBarProps {
  breadcrumbs?: BreadcrumbItem[]
  campaignStatus?: CampaignStatus
  /** Number of products with quality warnings (scrape failures) */
  qualityWarningCount?: number
}

function AvatarMenu() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const initials = user?.email
    ? user.email.slice(0, 2).toUpperCase()
    : 'ME'

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center justify-center w-8 h-8 rounded-full bg-brand-primary text-neutral-0 text-small-strong hover:bg-brand-primary-hover transition-colors"
        aria-haspopup="true"
        aria-expanded={open}
        title={user?.email}
      >
        {initials}
      </button>

      {open && (
        <div className="absolute right-0 top-10 w-52 bg-neutral-0 rounded-lg shadow-elev-overlay border border-neutral-100 overflow-hidden z-50">
          <div className="px-4 py-3 border-b border-neutral-100">
            <p className="text-small-strong text-neutral-800 truncate">{user?.email}</p>
            <p className="text-caption text-neutral-400 capitalize">{user?.role}</p>
          </div>
          <nav className="py-1">
            <button
              type="button"
              className="w-full text-left px-4 py-2 text-body text-neutral-800 hover:bg-neutral-50 transition-colors"
              onClick={() => { setOpen(false); navigate('/preferences') }}
            >
              My Preferences
            </button>
            <button
              type="button"
              className="w-full text-left px-4 py-2 text-body text-neutral-800 hover:bg-neutral-50 transition-colors"
              onClick={() => { setOpen(false); navigate('/settings') }}
            >
              Settings
            </button>
            <div className="my-1 h-px bg-neutral-100" />
            <button
              type="button"
              className="w-full text-left px-4 py-2 text-body text-danger-600 hover:bg-danger-50 transition-colors"
              onClick={handleLogout}
            >
              Log out
            </button>
          </nav>
        </div>
      )}
    </div>
  )
}

export function TopBar({ breadcrumbs, campaignStatus, qualityWarningCount }: TopBarProps) {
  return (
    <header className="flex items-center justify-between h-topbar px-4 bg-neutral-900 border-b border-neutral-800 flex-shrink-0">
      {/* Left: Logo + breadcrumb */}
      <div className="flex items-center gap-4 min-w-0">
        {/* Logo mark */}
        <Link to="/campaigns" className="flex items-center gap-2 flex-shrink-0">
          <div className="w-7 h-7 rounded-md bg-brand-primary flex items-center justify-center">
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <rect x="2" y="3" width="12" height="10" rx="2" stroke="white" strokeWidth="1.5" />
              <path d="M2 6H14" stroke="white" strokeWidth="1.5" />
              <path d="M5 9H11" stroke="white" strokeWidth="1.25" strokeLinecap="round" />
              <path d="M5 11.5H8.5" stroke="white" strokeWidth="1.25" strokeLinecap="round" />
            </svg>
          </div>
          <span className="text-small-strong text-neutral-0 hidden sm:block">Email Builder</span>
        </Link>

        {/* Breadcrumb */}
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav className="flex items-center gap-1 min-w-0" aria-label="Breadcrumb">
            <span className="text-neutral-600 text-small">/</span>
            {breadcrumbs.map((crumb, index) => (
              <React.Fragment key={index}>
                {index > 0 && <span className="text-neutral-600 text-small">/</span>}
                {crumb.href ? (
                  <Link
                    to={crumb.href}
                    className="text-small text-neutral-400 hover:text-neutral-200 transition-colors truncate max-w-[160px]"
                  >
                    {crumb.label}
                  </Link>
                ) : (
                  <span className="text-small text-neutral-200 truncate max-w-[200px]">
                    {crumb.label}
                  </span>
                )}
              </React.Fragment>
            ))}
          </nav>
        )}

        {/* Status pill */}
        {campaignStatus && (
          <StatusPill status={campaignStatus} className="flex-shrink-0" />
        )}

        {/* Quality warning badge */}
        {qualityWarningCount != null && qualityWarningCount > 0 && (
          <span
            className="flex items-center gap-1 text-small px-2 py-0.5 rounded-full bg-error-600 text-neutral-0 flex-shrink-0"
            title={`${qualityWarningCount} product image${qualityWarningCount !== 1 ? 's' : ''} need attention`}
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
              <path
                d="M5 3.5v2M5 6.5v.25M1 8.5h8L5 1.5l-4 7z"
                stroke="currentColor"
                strokeWidth="1"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            {qualityWarningCount}
          </span>
        )}
      </div>

      {/* Right: Avatar menu */}
      <AvatarMenu />
    </header>
  )
}
