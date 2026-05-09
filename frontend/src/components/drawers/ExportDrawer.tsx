import React, { useState, useEffect, useRef } from 'react'
import { Button } from '../ui/Button'
import { showToast } from '../ui/Toast'
import { api } from '../../lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────

interface AuditItem {
  check: string
  status: 'pass' | 'warn' | 'hard_stop'
  message: string
}

interface AuditReport {
  items: AuditItem[]
  size_kb: number
  has_hard_stops: boolean
  minified_html: string
}

interface ExportDrawerProps {
  campaignId: string
  isOpen: boolean
  onClose: () => void
  approvalInfo?: { reviewer_name: string; approved_at: string } | null
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatApprovalTime(isoString: string): string {
  try {
    const d = new Date(isoString)
    return d.toLocaleDateString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return isoString
  }
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <div
      className="h-10 rounded-md bg-neutral-100"
      style={{
        backgroundImage:
          'linear-gradient(90deg, #EEF1F5 0%, #F8F9FB 50%, #EEF1F5 100%)',
        backgroundSize: '200% 100%',
      }}
    />
  )
}

interface AuditRowProps {
  item: AuditItem
}

function AuditRow({ item }: AuditRowProps) {
  const styles = {
    pass: {
      bg: 'bg-success-50',
      text: 'text-success-600',
      icon: '✓',
    },
    warn: {
      bg: 'bg-warn-50',
      text: 'text-warn-600',
      icon: '⚠',
    },
    hard_stop: {
      bg: 'bg-danger-50',
      text: 'text-danger-600',
      icon: '⛔',
    },
  }

  const s = styles[item.status]

  return (
    <div
      className={`flex items-start gap-3 px-3 py-2.5 rounded-md ${s.bg}`}
      role="listitem"
    >
      <span
        className={`flex-shrink-0 text-body-strong ${s.text} mt-0.5`}
        aria-hidden="true"
      >
        {s.icon}
      </span>
      <div className="flex-1 min-w-0">
        <p className={`text-small-strong ${s.text}`}>{item.check}</p>
        <p className={`text-small ${s.text} mt-0.5`}>{item.message}</p>
      </div>
      {item.status === 'hard_stop' && (
        <button
          type="button"
          className={`flex-shrink-0 text-caption underline hover:no-underline ${s.text} focus-visible:ring-2 focus-visible:ring-brand-primary rounded-sm`}
        >
          View issue
        </button>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function ExportDrawer({
  campaignId,
  isOpen,
  onClose,
  approvalInfo,
}: ExportDrawerProps) {
  const [auditReport, setAuditReport] = useState<AuditReport | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [hasError, setHasError] = useState(false)
  const [isCopying, setIsCopying] = useState(false)
  const hasFetchedRef = useRef(false)

  const fetchAudit = React.useCallback(async () => {
    setIsLoading(true)
    setHasError(false)
    try {
      const response = await api.post<AuditReport>(
        `/campaigns/${campaignId}/audit`,
        { html: null },
      )
      setAuditReport(response.data)
    } catch {
      setHasError(true)
    } finally {
      setIsLoading(false)
    }
  }, [campaignId])

  // Fetch audit on open
  useEffect(() => {
    if (isOpen && !hasFetchedRef.current) {
      hasFetchedRef.current = true
      fetchAudit()
    }
    if (!isOpen) {
      hasFetchedRef.current = false
      setAuditReport(null)
      setHasError(false)
    }
  }, [isOpen, fetchAudit])

  // Esc to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
    }
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  const handleCopy = async () => {
    if (!auditReport) return
    setIsCopying(true)
    try {
      await navigator.clipboard.writeText(auditReport.minified_html)
      showToast(
        `Copied · ${auditReport.size_kb.toFixed(1)}KB · ready to paste`,
        'success',
      )
      setTimeout(() => {
        onClose()
      }, 2000)
    } catch {
      showToast('Failed to copy to clipboard', 'error')
    } finally {
      setIsCopying(false)
    }
  }

  const hardStops = auditReport?.items.filter((i) => i.status === 'hard_stop') ?? []
  const canCopy = Boolean(auditReport && !auditReport.has_hard_stops)

  return (
    <>
      {/* Scrim */}
      <div
        className={[
          'fixed inset-0 z-40 bg-black/40 transition-opacity duration-[240ms]',
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none',
        ].join(' ')}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer panel */}
      <aside
        className={[
          'fixed top-0 right-0 bottom-0 z-50 w-[480px] bg-neutral-0 shadow-elev-overlay',
          'flex flex-col transition-transform duration-[240ms]',
          isOpen ? 'translate-x-0' : 'translate-x-full',
        ].join(' ')}
        role="dialog"
        aria-modal="true"
        aria-label="Export to CleverTap"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 flex-shrink-0">
          <h2 className="text-heading-2 text-neutral-800">Export to CleverTap</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 transition-colors duration-[160ms] focus-visible:ring-2 focus-visible:ring-brand-primary rounded-sm"
            aria-label="Close export drawer"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path
                d="M15 5L5 15M5 5l10 10"
                stroke="currentColor"
                strokeWidth="1.75"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 flex flex-col gap-4">
          {/* Loading */}
          {isLoading && (
            <div className="flex flex-col gap-2" aria-busy="true" aria-label="Running audit">
              <p className="text-small text-neutral-400">Running pre-flight checks…</p>
              <SkeletonRow />
              <SkeletonRow />
              <SkeletonRow />
              <SkeletonRow />
            </div>
          )}

          {/* Error state */}
          {!isLoading && hasError && (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <p className="text-body text-neutral-600">Audit failed — retry</p>
              <Button variant="secondary" size="sm" onClick={fetchAudit}>
                Retry
              </Button>
            </div>
          )}

          {/* Audit results */}
          {!isLoading && auditReport && (
            <>
              <div className="flex flex-col gap-2" role="list" aria-label="Pre-flight checks">
                {auditReport.items.map((item, idx) => (
                  <AuditRow key={`${item.check}-${idx}`} item={item} />
                ))}
              </div>

              {/* Size info */}
              <p className="text-small text-neutral-400">
                HTML size: {auditReport.size_kb.toFixed(1)} KB
              </p>

              {/* Approval row */}
              <div className="flex items-center gap-2 border-t border-neutral-200 pt-4">
                <span
                  className={
                    approvalInfo ? 'text-success-600' : 'text-neutral-400'
                  }
                  aria-hidden="true"
                >
                  ●
                </span>
                {approvalInfo ? (
                  <p className="text-small text-neutral-600">
                    Approved by{' '}
                    <span className="font-semibold">{approvalInfo.reviewer_name}</span>
                    {' · '}
                    {formatApprovalTime(approvalInfo.approved_at)}
                  </p>
                ) : (
                  <p className="text-small text-neutral-400">Awaiting approval</p>
                )}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-200 flex-shrink-0">
          <div className="relative group">
            <Button
              variant="primary"
              fullWidth
              disabled={!canCopy || isCopying}
              isLoading={isCopying}
              onClick={handleCopy}
            >
              Copy to CleverTap
            </Button>

            {/* Tooltip listing hard stops */}
            {!canCopy && hardStops.length > 0 && (
              <div
                className={[
                  'absolute bottom-full left-0 right-0 mb-2 z-10 pointer-events-none',
                  'opacity-0 group-hover:opacity-100 transition-opacity duration-[160ms]',
                ].join(' ')}
                role="tooltip"
              >
                <div className="bg-neutral-900 text-neutral-0 text-caption rounded-md px-3 py-2 shadow-elev-overlay">
                  <p className="text-small-strong mb-1">Resolve before exporting:</p>
                  <ul className="flex flex-col gap-0.5">
                    {hardStops.map((hs, i) => (
                      <li key={i}>· {hs.check}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  )
}
