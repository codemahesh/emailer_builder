import React, { useState, useEffect, useRef } from 'react'
import { Button } from '../ui/Button'
import { showToast } from '../ui/Toast'
import { api } from '../../lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Snapshot {
  id: string
  campaign_id: string
  summary_chip: string
  created_at: string
}

interface SnapshotsPanelProps {
  campaignId: string
  onRestoreSnapshot: (snapshotId: string) => void
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatTime(isoString: string): string {
  try {
    const d = new Date(isoString)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return '--:--'
  }
}

function SkeletonRow() {
  return (
    <div
      className="h-8 rounded-sm bg-neutral-100"
      style={{
        backgroundImage:
          'linear-gradient(90deg, #EEF1F5 0%, #F8F9FB 50%, #EEF1F5 100%)',
        backgroundSize: '200% 100%',
      }}
    />
  )
}

// ── Preview modal ─────────────────────────────────────────────────────────────

interface SnapshotPreviewModalProps {
  snapshot: Snapshot
  isCurrentSnapshot: boolean
  onClose: () => void
  onRestore: (confirmSnapshot: boolean) => void
}

function SnapshotPreviewModal({
  snapshot,
  isCurrentSnapshot,
  onClose,
  onRestore,
}: SnapshotPreviewModalProps) {
  const [snapshotFirst, setSnapshotFirst] = useState(true)

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="snapshot-preview-title"
    >
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative w-full max-w-[480px] mx-4 bg-neutral-0 rounded-lg shadow-elev-modal transition-all duration-[240ms]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-neutral-200">
          <h2 id="snapshot-preview-title" className="text-heading-2 text-neutral-800">
            Preview snapshot
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 transition-colors duration-[160ms] focus-visible:ring-2 focus-visible:ring-brand-primary rounded-sm"
            aria-label="Close snapshot preview"
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
        <div className="px-6 py-5 flex flex-col gap-4">
          {/* Snapshot info */}
          <div className="bg-neutral-50 rounded-md p-3 flex items-center gap-3">
            <span
              className={isCurrentSnapshot ? 'text-brand-primary' : 'text-neutral-400'}
              aria-hidden="true"
            >
              {isCurrentSnapshot ? '●' : '○'}
            </span>
            <div className="flex flex-col gap-0.5">
              <p className="text-small-strong text-neutral-800">{snapshot.summary_chip}</p>
              <p className="text-caption text-neutral-400">{formatTime(snapshot.created_at)}</p>
            </div>
          </div>

          {/* Confirm snapshot before restore */}
          {!isCurrentSnapshot && (
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={snapshotFirst}
                onChange={(e) => setSnapshotFirst(e.target.checked)}
                className="w-4 h-4 rounded-sm border-neutral-200 accent-brand-primary focus-visible:ring-2 focus-visible:ring-brand-primary"
              />
              <span className="text-small text-neutral-600">
                Snapshot the current state first?
              </span>
            </label>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 justify-end px-6 pb-6">
          <Button variant="secondary" onClick={onClose}>
            Exit preview
          </Button>
          {!isCurrentSnapshot && (
            <Button variant="primary" onClick={() => onRestore(snapshotFirst)}>
              Restore this version
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function SnapshotsPanel({ campaignId, onRestoreSnapshot }: SnapshotsPanelProps) {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isExpanded, setIsExpanded] = useState(false)
  const [previewSnapshot, setPreviewSnapshot] = useState<Snapshot | null>(null)
  const [isRestoring, setIsRestoring] = useState(false)
  const mountedRef = useRef(true)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchSnapshots = React.useCallback(async () => {
    try {
      const response = await api.get<Snapshot[]>(`/campaigns/${campaignId}/snapshots`)
      if (mountedRef.current) {
        setSnapshots(response.data)
      }
    } catch {
      // silently ignore
    } finally {
      if (mountedRef.current) {
        setIsLoading(false)
      }
    }
  }, [campaignId])

  useEffect(() => {
    mountedRef.current = true
    fetchSnapshots()

    // Auto-refresh every 30s
    pollRef.current = setInterval(fetchSnapshots, 30_000)

    return () => {
      mountedRef.current = false
      if (pollRef.current !== null) {
        clearInterval(pollRef.current)
      }
    }
  }, [fetchSnapshots])

  const visibleSnapshots = isExpanded ? snapshots : snapshots.slice(0, 3)

  const handleRestore = async (snapshotId: string, confirmSnapshot: boolean) => {
    setIsRestoring(true)
    setPreviewSnapshot(null)
    try {
      if (confirmSnapshot) {
        // Create a snapshot of current state first
        await api.post(`/campaigns/${campaignId}/snapshots`, {
          summary_chip: 'Auto-snapshot before restore',
        })
      }
      await api.post(`/campaigns/${campaignId}/snapshots/${snapshotId}/restore`)
      await fetchSnapshots()
      onRestoreSnapshot(snapshotId)
      showToast('Snapshot restored successfully', 'success')
    } catch {
      showToast('Failed to restore snapshot', 'error')
    } finally {
      setIsRestoring(false)
    }
  }

  return (
    <div className="border-t border-neutral-200">
      {/* Panel header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <span className="text-small-strong uppercase tracking-wider text-neutral-600">
          Snapshots
        </span>
        {isRestoring && (
          <span className="text-caption text-brand-primary animate-pulse">Restoring…</span>
        )}
      </div>

      {/* Loading skeleton */}
      {isLoading && (
        <div className="px-4 pb-4 flex flex-col gap-2" aria-busy="true">
          <SkeletonRow />
          <SkeletonRow />
          <SkeletonRow />
        </div>
      )}

      {/* Empty state */}
      {!isLoading && snapshots.length === 0 && (
        <div className="px-4 pb-4">
          <p className="text-small text-neutral-400 italic">
            Your edits will appear here as snapshots.
          </p>
        </div>
      )}

      {/* Snapshot list */}
      {!isLoading && snapshots.length > 0 && (
        <div className="px-4 pb-4 flex flex-col gap-1">
          {visibleSnapshots.map((snap, index) => {
            const isCurrent = index === 0

            return (
              <button
                key={snap.id}
                type="button"
                onClick={() => setPreviewSnapshot(snap)}
                className={[
                  'flex items-center gap-2 w-full rounded-md px-2 py-1.5 text-left',
                  'hover:bg-neutral-50 transition-colors duration-[160ms]',
                  'focus-visible:ring-2 focus-visible:ring-brand-primary',
                ].join(' ')}
                aria-label={`Snapshot: ${snap.summary_chip} at ${formatTime(snap.created_at)}`}
              >
                <span
                  className={isCurrent ? 'text-brand-primary' : 'text-neutral-400'}
                  aria-hidden="true"
                >
                  {isCurrent ? '●' : '○'}
                </span>
                <span className="text-caption text-neutral-400 flex-shrink-0 w-10">
                  {formatTime(snap.created_at)}
                </span>
                <span className="text-small text-neutral-600 truncate flex-1">
                  {snap.summary_chip}
                </span>
              </button>
            )
          })}

          {/* Show all / Collapse */}
          {snapshots.length > 3 && (
            <button
              type="button"
              onClick={() => setIsExpanded((v) => !v)}
              className="text-small text-brand-primary hover:underline text-left px-2 mt-1 focus-visible:ring-2 focus-visible:ring-brand-primary rounded-sm"
            >
              {isExpanded ? 'Show less' : `Show all (${snapshots.length})`}
            </button>
          )}
        </div>
      )}

      {/* Preview modal */}
      {previewSnapshot && (
        <SnapshotPreviewModal
          snapshot={previewSnapshot}
          isCurrentSnapshot={previewSnapshot.id === snapshots[0]?.id}
          onClose={() => setPreviewSnapshot(null)}
          onRestore={(confirmSnapshot) =>
            handleRestore(previewSnapshot.id, confirmSnapshot)
          }
        />
      )}
    </div>
  )
}
