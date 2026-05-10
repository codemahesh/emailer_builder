import { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '../ui/Button'
import { Modal } from '../ui/Modal'
import {
  startFullSync,
  startFastSync,
  getSyncStatus,
  updateCampaign,
  verifySheet,
  type Campaign,
  type SyncStatus,
  type VerifyResponse,
} from '../../lib/api'
import { showToast } from '../ui/Toast'

// ── Types ─────────────────────────────────────────────────────────────────────

type Source = 'link' | 'upload'

type VerifyPhase =
  | { status: 'idle' }
  | { status: 'verifying' }
  | { status: 'verified'; result: VerifyResponse }
  | { status: 'error'; result: VerifyResponse }
  | { status: 'warning'; result: VerifyResponse }  // EMPTY_SHEET — user can bypass

type SyncPhase = 'idle' | 'running' | 'success' | 'partial' | 'sync_error'

interface SyncPanelProps {
  campaignId: string
  campaign?: Campaign
  sheetUrl?: string
  onSyncComplete?: () => void
}

// ── Small helpers ─────────────────────────────────────────────────────────────

function CopyButton({ value, label }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = async () => {
    await navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button
      type="button"
      onClick={handleCopy}
      aria-label="Copy service account email"
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-neutral-100 border border-neutral-200 text-small-strong text-brand-primary hover:bg-neutral-200 transition-colors"
    >
      {copied ? (
        <>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path d="M2 7l3.5 3.5L12 3" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Copied
        </>
      ) : (
        <>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <rect x="5" y="5" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
            <path d="M9 5V3.5A1.5 1.5 0 007.5 2h-4A1.5 1.5 0 002 3.5v4A1.5 1.5 0 003.5 9H5" stroke="currentColor" strokeWidth="1.5" />
          </svg>
          {label ?? value}
        </>
      )}
    </button>
  )
}

function ProgressBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0
  return (
    <div className="w-full h-1.5 bg-neutral-200 rounded-full overflow-hidden">
      <div
        className="h-full bg-brand-primary transition-all duration-300"
        style={{ width: `${pct}%` }}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
      />
    </div>
  )
}

function timeAgo(isoString: string): string {
  const diff = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)} hr ago`
  return `${Math.floor(diff / 86400)} days ago`
}

// ── Error banner ──────────────────────────────────────────────────────────────

interface ErrorBannerProps {
  result: VerifyResponse
  serviceAccountEmail: string
  onConnectAnyway?: () => void
}

const BANNER_COPY: Record<
  string,
  { title: string; body: string }
> = {
  INVALID_URL: {
    title: "URL doesn't look like a Google Sheets link.",
    body: 'Make sure the link starts with "https://docs.google.com/spreadsheets/".',
  },
  NOT_FOUND: {
    title: 'Sheet not found.',
    body: 'Double-check the URL — the sheet may have been moved or deleted.',
  },
  NOT_SHARED: {
    title: "Service account doesn't have access.",
    body: 'Share the sheet with the email below as Viewer or Editor, then verify again.',
  },
  EMPTY_SHEET: {
    title: 'Sheet is empty.',
    body: 'We connected, but found no rows.',
  },
  MISSING_COLUMNS: {
    title: '',
    body: 'Your sheet must include "sku" and "product_link". Use the template to get the headers right.',
  },
}

function ErrorBanner({ result, serviceAccountEmail, onConnectAnyway }: ErrorBannerProps) {
  const code = result.error_code ?? ''
  const copy = BANNER_COPY[code] ?? { title: 'Verification failed.', body: '' }
  const isWarning = code === 'EMPTY_SHEET'

  const title =
    code === 'MISSING_COLUMNS'
      ? result.missing_columns.length === 1
        ? `Missing column: ${result.missing_columns[0]}`
        : `Missing columns: ${result.missing_columns.join(', ')}`
      : copy.title

  return (
    <div
      role="alert"
      className={`rounded-lg border p-3 flex flex-col gap-2 text-small ${
        isWarning
          ? 'bg-warning-50 border-warning-200 text-warning-800'
          : 'bg-error-50 border-error-200 text-error-800'
      }`}
    >
      <div className="flex items-start gap-2">
        {isWarning ? (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="flex-shrink-0 mt-0.5 text-warning-600" aria-hidden="true">
            <path d="M8 6v3M8 11h.01M1.5 13.5h13L8 2.5l-6.5 11z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="flex-shrink-0 mt-0.5 text-error-600" aria-hidden="true">
            <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.5" />
            <path d="M8 5v3.5M8 10.5v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        )}
        <div>
          {title && <p className="font-semibold">{title}</p>}
          {copy.body && <p className={title ? 'mt-0.5' : ''}>{copy.body}</p>}
        </div>
      </div>

      {code === 'NOT_SHARED' && (
        <div className="flex items-center gap-2 pl-6">
          <span className="font-mono text-small text-neutral-700 truncate">{serviceAccountEmail}</span>
          <CopyButton value={serviceAccountEmail} label="Copy" />
        </div>
      )}

      {code === 'MISSING_COLUMNS' && (
        <div className="pl-6">
          <a
            href="/static/sheet-template.xlsx"
            download
            className="text-small-strong text-error-700 underline hover:no-underline"
          >
            ⤓ Download template
          </a>
        </div>
      )}

      {code === 'EMPTY_SHEET' && onConnectAnyway && (
        <div className="pl-6">
          <button
            type="button"
            onClick={onConnectAnyway}
            className="text-small-strong text-warning-700 underline hover:no-underline"
          >
            Connect anyway
          </button>
        </div>
      )}
    </div>
  )
}

// ── Connection chip ───────────────────────────────────────────────────────────

interface ConnectionChipProps {
  result: VerifyResponse
  sheetUrl: string
  serviceAccountEmail: string
  onChangeUrl: () => void
}

function ConnectionChip({ result, sheetUrl, serviceAccountEmail, onChangeUrl }: ConnectionChipProps) {
  const truncatedUrl = sheetUrl.length > 48
    ? sheetUrl.slice(0, 24) + '…' + sheetUrl.slice(-20)
    : sheetUrl

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-small-strong text-neutral-800">
            Connected to:{' '}
            <span className="font-semibold">"{result.sheet_title || 'Sheet'}"</span>
          </p>
          <p
            className="text-small font-mono text-neutral-500 truncate"
            title={sheetUrl}
          >
            {truncatedUrl}
          </p>
          <p className="text-small text-neutral-500">
            {result.row_count} products
            {result.tab_count > 1 && ` · ${result.tab_count} tabs`}
          </p>
          {result.headers_found.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              <span className="text-small text-neutral-400">Detected columns:</span>
              {result.headers_found.map((h) => (
                <span
                  key={h}
                  className="px-1.5 py-0.5 bg-neutral-100 rounded text-small font-mono text-neutral-600"
                >
                  {h}
                </span>
              ))}
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={onChangeUrl}
          className="text-small text-neutral-400 hover:text-neutral-600 underline flex-shrink-0"
        >
          Change
        </button>
      </div>

      {/* Service account row — quieter after connect */}
      <div className="flex items-center gap-2 text-small text-neutral-500">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className="flex-shrink-0" aria-hidden="true">
          <circle cx="6" cy="6" r="5.25" stroke="currentColor" strokeWidth="1.5" />
          <path d="M6 3.5v2.5l1.5 1.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        <span className="font-mono truncate">{serviceAccountEmail}</span>
        <CopyButton value={serviceAccountEmail} label="Copy" />
      </div>

      {result.tab_count > 1 && (
        <div className="flex items-start gap-2 bg-info-50 border border-info-200 rounded p-2 text-small text-info-700">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="flex-shrink-0 mt-0.5" aria-hidden="true">
            <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.5" />
            <path d="M7 6v4M7 4.5v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          This spreadsheet has {result.tab_count} tabs. We import from the first tab only.
        </div>
      )}
    </div>
  )
}

// ── Service account row (idle state) ─────────────────────────────────────────

function ServiceAccountRow({ email }: { email: string }) {
  return (
    <div className="flex flex-col gap-1">
      <p className="text-small text-neutral-500">
        Share your sheet with this email as Viewer or Editor:
      </p>
      <div className="flex items-center gap-2 bg-neutral-50 border border-neutral-200 rounded px-3 py-2">
        <span className="font-mono text-small text-neutral-700 truncate flex-1 min-w-0">
          {email}
        </span>
        <CopyButton value={email} label="Copy" />
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function SyncPanel({ campaignId, sheetUrl: initialSheetUrl, onSyncComplete }: SyncPanelProps) {
  const serviceAccountEmail =
    (import.meta as unknown as { env: Record<string, string> }).env.VITE_SERVICE_ACCOUNT_EMAIL ??
    'emailer-builder@your-project.iam.gserviceaccount.com'

  // ── State ──────────────────────────────────────────────────────────────────
  const [source, setSource] = useState<Source>('link')
  const [urlInput, setUrlInput] = useState(initialSheetUrl ?? '')

  // verifyPhase tracks the state of the verify flow
  const [verifyPhase, setVerifyPhase] = useState<VerifyPhase>(
    initialSheetUrl ? { status: 'idle' } : { status: 'idle' }
  )
  // If the campaign already has a sheet URL saved, start in a pseudo-verified state
  const [isConnected, setIsConnected] = useState(Boolean(initialSheetUrl))
  // savedSheetUrl = URL that has been committed to the campaign
  const [savedSheetUrl, setSavedSheetUrl] = useState(initialSheetUrl ?? '')

  const [syncPhase, setSyncPhase] = useState<SyncPhase>('idle')
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [hasEverSynced, setHasEverSynced] = useState(false)
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [showFailureDrawer, setShowFailureDrawer] = useState(false)

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── Polling ────────────────────────────────────────────────────────────────
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current !== null) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }, [])

  const handleSyncStatusUpdate = useCallback(
    (s: SyncStatus) => {
      setSyncStatus(s)
      if (s.status === 'running' || s.status === 'queued') {
        setSyncPhase('running')
        return
      }
      stopPolling()
      if (s.status === 'completed') {
        setSyncPhase('success')
        setHasEverSynced(true)
        onSyncComplete?.()
      } else if (s.status === 'partial') {
        setSyncPhase('partial')
        setHasEverSynced(true)
        onSyncComplete?.()
      } else if (s.status === 'failed') {
        setSyncPhase('sync_error')
      } else {
        setSyncPhase('idle')
      }
    },
    [onSyncComplete, stopPolling]
  )

  const startPolling = useCallback(() => {
    stopPolling()
    pollIntervalRef.current = setInterval(async () => {
      try {
        const s = await getSyncStatus(campaignId)
        handleSyncStatusUpdate(s)
      } catch {
        // silently ignore transient polling errors
      }
    }, 2000)
  }, [campaignId, handleSyncStatusUpdate, stopPolling])

  useEffect(() => () => stopPolling(), [stopPolling])

  // ── Verify & Connect ───────────────────────────────────────────────────────
  const handleVerify = async () => {
    const trimmed = urlInput.trim()
    setVerifyPhase({ status: 'verifying' })
    try {
      const result = await verifySheet(campaignId, trimmed)
      if (result.ok) {
        await _commitUrl(trimmed, result)
      } else if (result.error_code === 'EMPTY_SHEET') {
        setVerifyPhase({ status: 'warning', result })
      } else {
        setVerifyPhase({ status: 'error', result })
      }
    } catch {
      showToast('Verification failed. Please try again.', 'error')
      setVerifyPhase({ status: 'idle' })
    }
  }

  const _commitUrl = async (url: string, result: VerifyResponse) => {
    try {
      await updateCampaign(campaignId, { sheet_url: url })
      setSavedSheetUrl(url)
      setIsConnected(true)
      setVerifyPhase({ status: 'verified', result })
    } catch {
      showToast('Could not save sheet URL. Please try again.', 'error')
      setVerifyPhase({ status: 'idle' })
    }
  }

  const handleConnectAnyway = async () => {
    const result = (verifyPhase as { result: VerifyResponse }).result
    await _commitUrl(urlInput.trim(), result)
  }

  // Switching tabs preserves URL but clears verification status (I2)
  const handleSourceSwitch = (newSource: Source) => {
    setSource(newSource)
    setVerifyPhase({ status: 'idle' })
  }

  const handleChangeUrl = () => {
    setIsConnected(false)
    setVerifyPhase({ status: 'idle' })
  }

  // ── Sync actions ───────────────────────────────────────────────────────────
  const handleConfirmFullSync = async () => {
    setShowConfirmModal(false)
    setSyncPhase('running')
    setSyncStatus({ status: 'queued', total: 0, processed: 0, failed: 0 })
    try {
      await startFullSync(campaignId)
      startPolling()
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      const detail = e?.response?.data?.detail ?? 'Could not start sync. Please try again.'
      showToast(detail, 'error')
      setSyncPhase('sync_error')
    }
  }

  const handleFastSync = async () => {
    setSyncPhase('running')
    setSyncStatus({ status: 'queued', total: 0, processed: 0, failed: 0 })
    try {
      await startFastSync(campaignId)
      startPolling()
    } catch {
      showToast('Failed to start fast sync', 'error')
      setSyncPhase('idle')
    }
  }

  // ── Render: header badge ───────────────────────────────────────────────────
  const renderStatusBadge = () => {
    if (syncPhase === 'running') {
      return <span className="flex items-center gap-1.5 text-small text-brand-primary"><span className="w-2 h-2 rounded-full bg-brand-primary animate-pulse" />Syncing…</span>
    }
    if (syncPhase === 'success') {
      return <span className="flex items-center gap-1.5 text-small text-success-600"><span className="w-2 h-2 rounded-full bg-success-600" />Synced</span>
    }
    if (syncPhase === 'partial') {
      return <span className="flex items-center gap-1.5 text-small text-warning-600"><span className="w-2 h-2 rounded-full bg-warning-500" />Partial</span>
    }
    if (syncPhase === 'sync_error') {
      return <span className="flex items-center gap-1.5 text-small text-error-600"><span className="w-2 h-2 rounded-full bg-error-600" />Error</span>
    }
    if (isConnected) {
      return <span className="flex items-center gap-1.5 text-small text-success-600"><span className="w-2 h-2 rounded-full bg-success-600" />Connected</span>
    }
    return <span className="text-small text-neutral-400">○ Not connected</span>
  }

  // ── Render: sync progress / summary ───────────────────────────────────────
  const renderSyncSummary = () => {
    if (!syncStatus) return null
    if (syncPhase === 'running') {
      return (
        <div className="flex flex-col gap-1.5">
          <p className="text-small text-neutral-600">
            Reading sheet… {syncStatus.processed}/{syncStatus.total} products
          </p>
          <ProgressBar value={syncStatus.processed} max={syncStatus.total} />
        </div>
      )
    }
    if (syncPhase === 'success' && syncStatus.last_synced) {
      return (
        <p className="text-small text-success-600">
          {syncStatus.processed} of {syncStatus.total} imported · {timeAgo(syncStatus.last_synced)}
        </p>
      )
    }
    if (syncPhase === 'partial' && syncStatus.last_synced) {
      return (
        <p className="text-small text-warning-600">
          {syncStatus.processed} of {syncStatus.total} imported ·{' '}
          <button type="button" className="underline hover:no-underline" onClick={() => setShowFailureDrawer(true)}>
            {syncStatus.failed} failed
          </button>
        </p>
      )
    }
    if (syncPhase === 'sync_error') {
      return (
        <p className="text-small text-error-600">
          {syncStatus.error_message ?? 'Sync failed. Please try again.'}
        </p>
      )
    }
    return null
  }

  // ── Render: action buttons ─────────────────────────────────────────────────
  const renderActions = () => {
    const busy = syncPhase === 'running'
    return (
      <div className="flex flex-col gap-2">
        {/* Verify success helper — shown once before first sync */}
        {!hasEverSynced && verifyPhase.status === 'verified' && (
          <p className="text-small text-neutral-500">
            Verified — nothing imported yet. Click Full Sync to begin.
          </p>
        )}

        <Button
          variant="primary"
          fullWidth
          disabled={busy}
          isLoading={busy}
          onClick={() => setShowConfirmModal(true)}
        >
          Full Sync
        </Button>

        {hasEverSynced && (
          <Button
            variant="secondary"
            fullWidth
            disabled={busy}
            onClick={handleFastSync}
          >
            Fast Sync
          </Button>
        )}
      </div>
    )
  }

  // ── Main render ────────────────────────────────────────────────────────────
  return (
    <>
      <div className="flex flex-col gap-4 p-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="text-heading-3 text-neutral-800">Google Sheets</h3>
          {renderStatusBadge()}
        </div>

        {/* Source segmented control */}
        <div
          role="tablist"
          aria-label="Choose a source: Google Sheets link or file upload"
          className="flex rounded-lg border border-neutral-200 overflow-hidden text-small-strong"
        >
          <button
            role="tab"
            aria-selected={source === 'link'}
            type="button"
            onClick={() => handleSourceSwitch('link')}
            className={`flex-1 py-2 text-center transition-colors ${
              source === 'link'
                ? 'bg-brand-primary text-white'
                : 'bg-white text-neutral-500 hover:bg-neutral-50'
            }`}
          >
            Link
          </button>
          <button
            role="tab"
            aria-selected={source === 'upload'}
            type="button"
            disabled
            aria-disabled="true"
            className="flex-1 py-2 text-center text-neutral-300 bg-white cursor-not-allowed"
            title="File upload coming soon"
          >
            Upload
          </button>
        </div>

        {/* Link tab content */}
        {source === 'link' && (
          <>
            {/* Connected state: show connection chip */}
            {isConnected && verifyPhase.status === 'verified' ? (
              <>
                <ConnectionChip
                  result={verifyPhase.result}
                  sheetUrl={savedSheetUrl}
                  serviceAccountEmail={serviceAccountEmail}
                  onChangeUrl={handleChangeUrl}
                />
                {renderSyncSummary()}
                {renderActions()}
              </>
            ) : isConnected && verifyPhase.status === 'idle' ? (
              /* Campaign already has a saved URL but user hasn't re-verified in this session */
              <>
                <div className="flex flex-col gap-1">
                  <p className="text-small-strong text-neutral-600">Connected sheet:</p>
                  <p className="text-small font-mono text-neutral-500 truncate" title={savedSheetUrl}>
                    {savedSheetUrl}
                  </p>
                  <button
                    type="button"
                    onClick={handleChangeUrl}
                    className="text-small text-neutral-400 hover:text-neutral-600 underline text-left w-fit"
                  >
                    Change sheet URL
                  </button>
                </div>
                <ServiceAccountRow email={serviceAccountEmail} />
                {renderSyncSummary()}
                {renderActions()}
              </>
            ) : (
              /* Unconnected / verify flow */
              <>
                {/* URL input */}
                <div className="flex flex-col gap-1">
                  <label htmlFor="sheet-url" className="text-small-strong text-neutral-600">
                    Google Sheet URL
                  </label>
                  <input
                    id="sheet-url"
                    type="url"
                    value={urlInput}
                    onChange={(e) => {
                      setUrlInput(e.target.value)
                      // Clear error banner on edit (I2)
                      if (verifyPhase.status === 'error' || verifyPhase.status === 'warning') {
                        setVerifyPhase({ status: 'idle' })
                      }
                    }}
                    placeholder="https://docs.google.com/spreadsheets/d/…"
                    className="w-full px-3 py-2 border border-neutral-200 rounded-lg text-small font-mono placeholder:text-neutral-300 focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent"
                    aria-describedby={
                      verifyPhase.status === 'error' || verifyPhase.status === 'warning'
                        ? 'verify-error-banner'
                        : undefined
                    }
                  />
                </div>

                {/* Error / warning banner */}
                {(verifyPhase.status === 'error' || verifyPhase.status === 'warning') && (
                  <div id="verify-error-banner">
                    <ErrorBanner
                      result={verifyPhase.result}
                      serviceAccountEmail={serviceAccountEmail}
                      onConnectAnyway={
                        verifyPhase.status === 'warning' ? handleConnectAnyway : undefined
                      }
                    />
                  </div>
                )}

                {/* Service account row — always visible in idle/error */}
                <ServiceAccountRow email={serviceAccountEmail} />

                {/* Verify button */}
                <Button
                  variant="primary"
                  fullWidth
                  disabled={!urlInput.trim() || verifyPhase.status === 'verifying'}
                  isLoading={verifyPhase.status === 'verifying'}
                  onClick={handleVerify}
                >
                  {verifyPhase.status === 'verifying' ? 'Verifying…' : 'Verify & Connect'}
                </Button>
              </>
            )}
          </>
        )}

        {/* Upload tab placeholder */}
        {source === 'upload' && (
          <div className="flex flex-col items-center justify-center py-8 gap-2 text-neutral-400">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <rect x="6" y="4" width="20" height="24" rx="3" stroke="currentColor" strokeWidth="1.5" />
              <path d="M11 12h10M11 17h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <p className="text-small text-center">File upload coming in a future update.</p>
          </div>
        )}
      </div>

      {/* Full Sync confirm modal */}
      <Modal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        title="Re-scrape everything?"
      >
        <div className="flex flex-col gap-5 p-6">
          <p className="text-body text-neutral-600">
            This will re-fetch the sheet and re-scrape every product. Manual image overrides are
            preserved. This can take several minutes.
          </p>
          <div className="flex gap-3 justify-end">
            <Button variant="secondary" onClick={() => setShowConfirmModal(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleConfirmFullSync}>
              Re-scrape all
            </Button>
          </div>
        </div>
      </Modal>

      {/* Failure drawer */}
      {showFailureDrawer && syncStatus && (
        <div className="fixed inset-0 z-40 flex">
          <div className="flex-1 bg-black/30" onClick={() => setShowFailureDrawer(false)} />
          <aside className="w-80 bg-white shadow-xl flex flex-col overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-neutral-200">
              <h4 className="text-heading-3 text-neutral-800">{syncStatus.failed} Failed Products</h4>
              <button
                type="button"
                onClick={() => setShowFailureDrawer(false)}
                className="text-neutral-400 hover:text-neutral-600"
                aria-label="Close failures drawer"
              >
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M15 5L5 15M5 5l10 10" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <p className="text-small text-neutral-500">
                {syncStatus.error_message ??
                  `${syncStatus.failed} product(s) could not be imported. Check the sheet for invalid rows.`}
              </p>
            </div>
          </aside>
        </div>
      )}
    </>
  )
}
