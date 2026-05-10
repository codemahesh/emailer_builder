import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Button } from '../ui/Button'
import { Input } from '../ui/Input'
import { Modal } from '../ui/Modal'
import {
  startFullSync,
  startFastSync,
  getSyncStatus,
  updateCampaign,
  type Campaign,
  type SyncStatus,
} from '../../lib/api'
import { showToast } from '../ui/Toast'

// ── Types ─────────────────────────────────────────────────────────────────────

type PanelState =
  | 'empty'       // no sheet URL yet
  | 'ready'       // sheet URL set, no sync in progress
  | 'confirming'  // full sync confirm modal open
  | 'running'     // sync in progress
  | 'success'     // last sync completed with 0 failures
  | 'partial'     // last sync completed with some failures
  | 'error'       // last sync failed entirely

interface SyncPanelProps {
  campaignId: string
  sheetUrl?: string
  onSyncComplete?: () => void
}

// ── Helper components ─────────────────────────────────────────────────────────

function CopyChip({ value, label }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex items-center gap-2 bg-neutral-100 rounded-md px-3 py-2 border border-neutral-200">
      <span className="text-small text-info-600 font-mono truncate flex-1 min-w-0">
        {label ?? value}
      </span>
      <button
        type="button"
        onClick={handleCopy}
        className="flex-shrink-0 text-small-strong text-brand-primary hover:text-brand-primary-hover transition-colors"
        title="Copy service account email"
        aria-label="Copy service account email to clipboard"
      >
        {copied ? 'Copied!' : 'Copy'}
      </button>
    </div>
  )
}

function StatusDot({ state }: { state: PanelState }) {
  if (state === 'running') {
    return (
      <span className="inline-block w-2 h-2 rounded-full bg-brand-primary animate-pulse" />
    )
  }
  if (state === 'success') {
    return <span className="inline-block w-2 h-2 rounded-full bg-success-600" />
  }
  if (state === 'partial') {
    return <span className="inline-block w-2 h-2 rounded-full bg-warning-500" />
  }
  if (state === 'error') {
    return <span className="inline-block w-2 h-2 rounded-full bg-error-600" />
  }
  return null
}

function ProgressBar({ value, max }: { value: number; max: number }) {
  const pct = max > 0 ? Math.min(100, Math.round((value / max) * 100)) : 0
  return (
    <div className="w-full h-1 bg-neutral-200 rounded-full overflow-hidden">
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
  if (diff < 60) return `${diff} seconds ago`
  if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`
  return `${Math.floor(diff / 86400)} days ago`
}

function isValidSheetsUrl(url: string): boolean {
  return /^https:\/\/docs\.google\.com\/spreadsheets\/d\/[a-zA-Z0-9_-]+/.test(url.trim())
}

// ── Main component ────────────────────────────────────────────────────────────

export function SyncPanel({ campaignId, sheetUrl: initialSheetUrl, onSyncComplete }: SyncPanelProps) {
  const serviceAccountEmail =
    (import.meta as unknown as { env: Record<string, string> }).env.VITE_SERVICE_ACCOUNT_EMAIL ??
    'emailer-builder@your-project.iam.gserviceaccount.com'

  // ── Local state ────────────────────────────────────────────────────────────
  const [sheetUrl, setSheetUrl] = useState(initialSheetUrl ?? '')
  const [urlError, setUrlError] = useState('')
  const [isSavingUrl, setIsSavingUrl] = useState(false)

  const [panelState, setPanelState] = useState<PanelState>(
    initialSheetUrl ? 'ready' : 'empty'
  )

  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [showConfirmModal, setShowConfirmModal] = useState(false)
  const [hasEverSynced, setHasEverSynced] = useState(false)
  const [showFailureDrawer, setShowFailureDrawer] = useState(false)

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const isConnected = Boolean(initialSheetUrl)

  // ── Polling helpers ────────────────────────────────────────────────────────
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current !== null) {
      clearInterval(pollIntervalRef.current)
      pollIntervalRef.current = null
    }
  }, [])

  const handleSyncStatusUpdate = useCallback(
    (status: SyncStatus) => {
      setSyncStatus(status)

      if (status.status === 'running' || status.status === 'queued') {
        setPanelState('running')
        return
      }

      stopPolling()

      if (status.status === 'completed') {
        setPanelState('success')
        setHasEverSynced(true)
        onSyncComplete?.()
      } else if (status.status === 'partial') {
        setPanelState('partial')
        setHasEverSynced(true)
        onSyncComplete?.()
      } else if (status.status === 'failed') {
        setPanelState('error')
      } else {
        // idle or unknown — treat as ready
        setPanelState(isConnected ? 'ready' : 'empty')
      }
    },
    [isConnected, onSyncComplete, stopPolling]
  )

  const startPolling = useCallback(() => {
    stopPolling()
    pollIntervalRef.current = setInterval(async () => {
      try {
        const status = await getSyncStatus(campaignId)
        handleSyncStatusUpdate(status)
      } catch {
        // silently ignore transient errors during polling
      }
    }, 2000)
  }, [campaignId, handleSyncStatusUpdate, stopPolling])

  // Clean up on unmount
  useEffect(() => {
    return () => stopPolling()
  }, [stopPolling])

  // ── Actions ────────────────────────────────────────────────────────────────
  const handleConnect = async () => {
    const trimmed = sheetUrl.trim()
    if (!isValidSheetsUrl(trimmed)) {
      setUrlError('Please enter a valid Google Sheets URL (docs.google.com/spreadsheets/…)')
      return
    }
    setIsSavingUrl(true)
    setUrlError('')
    try {
      await updateCampaign(campaignId, { sheet_url: trimmed })
      showToast('Google Sheet connected successfully', 'success')
      setPanelState('ready')
      // Reload page so the parent re-fetches campaign with new sheet_url
      window.location.reload()
    } catch {
      setUrlError('Failed to save URL. Please try again.')
      showToast('Failed to connect sheet', 'error')
    } finally {
      setIsSavingUrl(false)
    }
  }

  const handleFullSyncClick = () => {
    setShowConfirmModal(true)
  }

  const handleConfirmFullSync = async () => {
    setShowConfirmModal(false)
    setPanelState('running')
    setSyncStatus({ status: 'queued', total: 0, processed: 0, failed: 0 })

    try {
      await startFullSync(campaignId)
      startPolling()
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      const detail = e?.response?.data?.detail ?? 'Could not start sync. Please try again.'
      showToast(detail, 'error')
      setPanelState('error')
      setSyncStatus({
        status: 'failed',
        total: 0,
        processed: 0,
        failed: 0,
        error_message: detail,
      })
    }
  }

  // ── Render helpers ─────────────────────────────────────────────────────────
  const renderStatusBadge = () => {
    if (panelState === 'running') {
      return (
        <span className="flex items-center gap-1.5 text-small text-brand-primary">
          <StatusDot state="running" />
          Syncing…
        </span>
      )
    }
    if (panelState === 'success') {
      return (
        <span className="flex items-center gap-1.5 text-small text-success-600">
          <StatusDot state="success" />
          Synced
        </span>
      )
    }
    if (panelState === 'partial') {
      return (
        <span className="flex items-center gap-1.5 text-small text-warning-600">
          <StatusDot state="partial" />
          Partial
        </span>
      )
    }
    if (panelState === 'error') {
      return (
        <span className="flex items-center gap-1.5 text-small text-error-600">
          <StatusDot state="error" />
          Error
        </span>
      )
    }
    if (isConnected) {
      return (
        <span className="flex items-center gap-1.5 text-small text-success-600">
          <span className="w-2 h-2 rounded-full bg-success-600" />
          Connected
        </span>
      )
    }
    return null
  }

  const renderSyncSummary = () => {
    if (!syncStatus) return null

    if (panelState === 'running') {
      return (
        <div className="flex flex-col gap-1.5">
          <p className="text-small text-neutral-600">
            Reading sheet… {syncStatus.processed}/{syncStatus.total} products
          </p>
          <ProgressBar value={syncStatus.processed} max={syncStatus.total} />
        </div>
      )
    }

    if (panelState === 'success' && syncStatus.last_synced) {
      return (
        <p className="text-small text-success-600">
          {syncStatus.processed} of {syncStatus.total} imported · 0 failures ·{' '}
          {timeAgo(syncStatus.last_synced)}
        </p>
      )
    }

    if (panelState === 'partial' && syncStatus.last_synced) {
      return (
        <p className="text-small text-warning-600">
          {syncStatus.processed} of {syncStatus.total} imported ·{' '}
          <button
            type="button"
            className="underline hover:no-underline"
            onClick={() => setShowFailureDrawer(true)}
          >
            {syncStatus.failed} failed
          </button>
        </p>
      )
    }

    if (panelState === 'error') {
      const errMsg =
        syncStatus.error_message ??
        `Could not access sheet — share with ${serviceAccountEmail}`
      return (
        <div className="flex items-start gap-2 bg-error-50 border border-error-200 rounded-md p-3">
          <svg
            className="w-4 h-4 text-error-600 flex-shrink-0 mt-0.5"
            fill="none"
            viewBox="0 0 16 16"
            aria-hidden="true"
          >
            <path
              d="M8 5v3M8 10.5v.5M1.5 13.5h13L8 2.5l-6.5 11z"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <div className="flex-1 min-w-0">
            <p className="text-small text-error-700">{errMsg}</p>
          </div>
          <CopyChip value={serviceAccountEmail} label="Copy email" />
        </div>
      )
    }

    return null
  }

  // ── Sheet URL input form (empty state) ────────────────────────────────────
  if (panelState === 'empty') {
    return (
      <div className="flex flex-col gap-4 p-4">
        <div className="flex items-center justify-between">
          <h3 className="text-heading-3 text-neutral-800">Google Sheets</h3>
        </div>

        <p className="text-body text-neutral-400">
          Connect a Google Sheet to begin syncing your product data.
        </p>

        <div className="flex flex-col gap-1">
          <p className="text-small-strong text-neutral-600">
            Share your sheet with this service account:
          </p>
          <CopyChip value={serviceAccountEmail} />
        </div>

        <Input
          label="Google Sheet URL"
          type="url"
          placeholder="https://docs.google.com/spreadsheets/d/…"
          value={sheetUrl}
          onChange={(e) => {
            setSheetUrl(e.target.value)
            if (urlError) setUrlError('')
          }}
          error={urlError}
          helperText="Paste the full URL of your Google Spreadsheet"
        />

        <Button
          variant="primary"
          fullWidth
          isLoading={isSavingUrl}
          disabled={!sheetUrl.trim() || isSavingUrl}
          onClick={handleConnect}
        >
          Connect
        </Button>
      </div>
    )
  }

  // ── Connected / running / done states ─────────────────────────────────────
  return (
    <>
      <div className="flex flex-col gap-4 p-4">
        {/* Header row */}
        <div className="flex items-center justify-between">
          <h3 className="text-heading-3 text-neutral-800">Google Sheets</h3>
          {renderStatusBadge()}
        </div>

        {/* Sheet URL pill */}
        <p className="text-small text-neutral-400 font-mono truncate" title={initialSheetUrl}>
          {initialSheetUrl}
        </p>

        {/* Service account chip */}
        <div className="flex flex-col gap-1">
          <p className="text-small-strong text-neutral-600">
            Share your sheet with this service account:
          </p>
          <CopyChip value={serviceAccountEmail} />
        </div>

        {/* Status / progress summary */}
        {renderSyncSummary()}

        {/* Primary action: Full Sync */}
        <Button
          variant="primary"
          fullWidth
          disabled={panelState === 'running'}
          isLoading={panelState === 'running'}
          onClick={handleFullSyncClick}
        >
          Full Sync
        </Button>

        {/* Secondary action: Fast Sync — visible only after first successful sync */}
        {hasEverSynced && (
          <Button
            variant="secondary"
            fullWidth
            disabled={panelState === 'running'}
            isLoading={false}
            onClick={async () => {
              setPanelState('running')
              setSyncStatus({ status: 'queued', total: 0, processed: 0, failed: 0 })
              try {
                await startFastSync(campaignId)
                startPolling()
              } catch {
                showToast('Failed to start fast sync', 'error')
                setPanelState(isConnected ? 'ready' : 'empty')
              }
            }}
          >
            Fast Sync
          </Button>
        )}

        {/* Reconnect link */}
        <button
          type="button"
          className="text-small text-neutral-400 hover:text-neutral-600 underline text-left"
          onClick={() => setPanelState('empty')}
        >
          Change sheet URL
        </button>
      </div>

      {/* Full Sync confirmation modal */}
      <Modal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        title="Run Full Sync?"
      >
        <div className="flex flex-col gap-5 p-6">
          <p className="text-body text-neutral-600">
            This re-scrapes everything and will discard non-overridden assets.
            Continue?
          </p>
          <div className="flex gap-3 justify-end">
            <Button
              variant="secondary"
              onClick={() => setShowConfirmModal(false)}
            >
              Cancel
            </Button>
            <Button variant="primary" onClick={handleConfirmFullSync}>
              Run Full Sync
            </Button>
          </div>
        </div>
      </Modal>

      {/* Failure drawer (partial sync) */}
      {showFailureDrawer && syncStatus && (
        <div className="fixed inset-0 z-40 flex">
          {/* Backdrop */}
          <div
            className="flex-1 bg-black/30"
            onClick={() => setShowFailureDrawer(false)}
          />
          {/* Drawer panel */}
          <aside className="w-80 bg-white shadow-xl flex flex-col overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b border-neutral-200">
              <h4 className="text-heading-3 text-neutral-800">
                {syncStatus.failed} Failed Products
              </h4>
              <button
                type="button"
                onClick={() => setShowFailureDrawer(false)}
                className="text-neutral-400 hover:text-neutral-600"
                aria-label="Close failures drawer"
              >
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path
                    d="M15 5L5 15M5 5l10 10"
                    stroke="currentColor"
                    strokeWidth="1.75"
                    strokeLinecap="round"
                  />
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
