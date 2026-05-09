import React, { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'
import { TopBar } from '../components/layout/TopBar'
import { Button } from '../components/ui/Button'
import { Skeleton } from '../components/ui/Skeleton'
import { showToast } from '../components/ui/Toast'
import { Modal } from '../components/ui/Modal'

// ── Types ─────────────────────────────────────────────────────────────────────

type SignalType = 'explicit_positive' | 'implicit_accept' | 'explicit_negative' | 'implicit_revert'

interface UserPreference {
  id: string
  signal_type: SignalType
  asset_type: string
  signal_value: string
  created_at: string
  weight: number
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function isPositiveSignal(signal_type: SignalType): boolean {
  return signal_type === 'explicit_positive' || signal_type === 'implicit_accept'
}

function formatRelativeTime(iso: string): string {
  try {
    const diff = Date.now() - new Date(iso).getTime()
    const days = Math.floor(diff / 86_400_000)
    if (days === 0) return 'today'
    if (days === 1) return '1 day ago'
    if (days < 30) return `${days} days ago`
    const weeks = Math.floor(days / 7)
    if (weeks < 8) return `${weeks} week${weeks !== 1 ? 's' : ''} ago`
    const months = Math.floor(days / 30)
    return `${months} month${months !== 1 ? 's' : ''} ago`
  } catch {
    return ''
  }
}

function getMostRecentDate(prefs: UserPreference[]): string | null {
  if (prefs.length === 0) return null
  const sorted = [...prefs].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  )
  return sorted[0].created_at
}

// ── Icons ─────────────────────────────────────────────────────────────────────

function SparkleIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className="text-[#7B3FE4] flex-shrink-0 mt-0.5"
    >
      <path
        d="M7 1L8.2 5.8L13 7L8.2 8.2L7 13L5.8 8.2L1 7L5.8 5.8L7 1Z"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinejoin="round"
        fill="currentColor"
        fillOpacity="0.15"
      />
    </svg>
  )
}

function HandIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className="text-[#0F8A4A] flex-shrink-0 mt-0.5"
    >
      <path
        d="M5 7V3.5a1 1 0 0 1 2 0V7M5 7V5.5a1 1 0 0 0-2 0V8c0 2.2 1.8 4 4 4a4 4 0 0 0 4-4V6.5a1 1 0 0 0-2 0M5 7h2"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

// ── Preference chip ───────────────────────────────────────────────────────────

interface PreferenceChipProps {
  pref: UserPreference
  onRemove: (id: string) => void
  isRemoving: boolean
}

function PreferenceChip({ pref, onRemove, isRemoving }: PreferenceChipProps) {
  const positive = isPositiveSignal(pref.signal_type)

  return (
    <div
      className={[
        'flex items-center justify-between gap-3 px-4 py-3 rounded-lg border transition-colors',
        positive
          ? 'bg-neutral-0 border-neutral-200'
          : 'bg-neutral-0 border-neutral-200',
      ].join(' ')}
    >
      <div className="flex items-start gap-2 min-w-0">
        {positive ? <SparkleIcon /> : <HandIcon />}
        <span className="text-body text-neutral-800 min-w-0">
          {positive ? (
            pref.signal_value
          ) : (
            <>
              <span className="text-neutral-400">Avoid: </span>
              {pref.signal_value}
            </>
          )}
        </span>
      </div>
      <button
        type="button"
        onClick={() => onRemove(pref.id)}
        disabled={isRemoving}
        aria-label={`Remove preference: ${pref.signal_value}`}
        className="w-6 h-6 flex items-center justify-center flex-shrink-0 text-neutral-400 hover:text-neutral-800 hover:bg-neutral-100 rounded transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
      >
        {isRemoving ? (
          <span className="inline-block w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
        ) : (
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <path d="M9 3L3 9M3 3L9 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        )}
      </button>
    </div>
  )
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function PreferencesSkeleton() {
  return (
    <div className="flex flex-col gap-3" aria-busy="true">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="w-full h-12 rounded-lg" />
      ))}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function PreferencesPage() {
  const [prefs, setPrefs] = useState<UserPreference[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [removingId, setRemovingId] = useState<string | null>(null)
  const [showResetModal, setShowResetModal] = useState(false)
  const [isResetting, setIsResetting] = useState(false)

  // ── Load ────────────────────────────────────────────────────────────────────

  const loadPreferences = useCallback(async () => {
    setIsLoading(true)
    try {
      const res = await api.get<UserPreference[]>('/preferences')
      setPrefs(res.data)
    } catch {
      showToast('Failed to load preferences', 'error')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadPreferences()
  }, [loadPreferences])

  // ── Remove single ───────────────────────────────────────────────────────────

  const handleRemove = async (id: string) => {
    setRemovingId(id)
    try {
      await api.delete(`/preferences/${id}`)
      setPrefs((prev) => prev.filter((p) => p.id !== id))
      showToast('Preference removed', 'success')
    } catch {
      showToast('Failed to remove preference', 'error')
    } finally {
      setRemovingId(null)
    }
  }

  // ── Reset all ───────────────────────────────────────────────────────────────

  const handleResetAll = async () => {
    setIsResetting(true)
    try {
      await api.delete('/preferences')
      setPrefs([])
      showToast('All preferences cleared', 'success')
      setShowResetModal(false)
    } catch {
      showToast('Failed to reset preferences', 'error')
    } finally {
      setIsResetting(false)
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  const lastUpdated = getMostRecentDate(prefs)

  return (
    <div className="min-h-screen flex flex-col bg-neutral-50">
      <TopBar breadcrumbs={[{ label: 'My Preferences' }]} />

      <main className="flex-1 flex justify-center px-4 py-10">
        <div className="w-full max-w-[560px] flex flex-col gap-6">
          <h1 className="text-heading-1 text-neutral-900">Your preferences</h1>

          <div className="bg-neutral-0 rounded-lg border border-neutral-200 shadow-elev-flat overflow-hidden">
            {/* Header */}
            <div className="px-6 py-4 border-b border-neutral-200">
              <p className="text-body text-neutral-600">
                The AI biases new campaigns toward:
              </p>
            </div>

            {/* Preference list */}
            <div className="px-6 py-4 flex flex-col gap-2">
              {isLoading ? (
                <PreferencesSkeleton />
              ) : prefs.length === 0 ? (
                <div className="py-10 text-center flex flex-col items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-neutral-100 flex items-center justify-center">
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                      <path d="M10 4v6M10 13.5v.5" stroke="#9CA3AF" strokeWidth="1.5" strokeLinecap="round" />
                      <circle cx="10" cy="10" r="8" stroke="#9CA3AF" strokeWidth="1.5" />
                    </svg>
                  </div>
                  <p className="text-body text-neutral-400 max-w-[320px]">
                    No preferences recorded yet. Use the thumbs up/down on AI suggestions to build your profile.
                  </p>
                </div>
              ) : (
                prefs.map((pref) => (
                  <PreferenceChip
                    key={pref.id}
                    pref={pref}
                    onRemove={handleRemove}
                    isRemoving={removingId === pref.id}
                  />
                ))
              )}
            </div>

            {/* Footer */}
            {!isLoading && prefs.length > 0 && (
              <div className="px-6 py-4 border-t border-neutral-100 flex items-center justify-between gap-4">
                {lastUpdated && (
                  <p className="text-small text-neutral-400">
                    Last updated {formatRelativeTime(lastUpdated)}
                  </p>
                )}
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowResetModal(true)}
                  className="text-danger-600 hover:bg-danger-50"
                >
                  Reset all preferences
                </Button>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Reset confirmation modal */}
      <Modal
        isOpen={showResetModal}
        onClose={() => setShowResetModal(false)}
        title="Reset preferences"
        width="sm"
      >
        <div className="px-6 py-5 flex flex-col gap-5">
          <p className="text-body text-neutral-600">
            This clears <strong className="text-neutral-800">{prefs.length}</strong>{' '}
            preference{prefs.length !== 1 ? 's' : ''}. Continue?
          </p>
          <div className="flex items-center justify-end gap-3 pt-1 border-t border-neutral-100 -mx-6 px-6 pb-1 mt-1">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setShowResetModal(false)}
              disabled={isResetting}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="danger"
              size="sm"
              isLoading={isResetting}
              onClick={handleResetAll}
            >
              Reset all
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
