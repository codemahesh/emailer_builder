import React, { useState, useEffect, useCallback } from 'react'
import { Button } from '../ui/Button'
import { showToast } from '../ui/Toast'
import { api } from '../../lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Theme {
  id: string
  name: string
  background_color: string
  section_color: string
  accent_color: string
  button_color: string
  product_bg_color: string
  heading_font: string
  body_font: string
  h1_size: number
  h2_size: number
  body_size: number
}

interface ThemePickerDrawerProps {
  campaignId: string
  currentPinnedThemeId?: string | null
  isOpen: boolean
  onClose: () => void
  onApply: (theme: Theme) => void
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="flex flex-col gap-2">
      <div
        className="w-full h-[140px] rounded-md bg-neutral-100"
        style={{
          backgroundImage:
            'linear-gradient(90deg, #EEF1F5 0%, #F8F9FB 50%, #EEF1F5 100%)',
          backgroundSize: '200% 100%',
        }}
      />
      <div
        className="h-4 w-3/4 rounded-sm bg-neutral-100"
        style={{
          backgroundImage:
            'linear-gradient(90deg, #EEF1F5 0%, #F8F9FB 50%, #EEF1F5 100%)',
          backgroundSize: '200% 100%',
        }}
      />
    </div>
  )
}

interface ThemeCardProps {
  theme: Theme
  isSelected: boolean
  onSelect: () => void
}

function ThemeCard({ theme, isSelected, onSelect }: ThemeCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={[
        'flex flex-col gap-2 rounded-md overflow-hidden text-left transition-all duration-[160ms]',
        'focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-2',
        isSelected ? 'border-2 border-brand-primary' : 'border border-neutral-200',
      ].join(' ')}
      aria-label={`Select theme: ${theme.name}`}
      aria-pressed={isSelected}
    >
      {/* Preview area */}
      <div
        className="relative w-full h-[140px] flex flex-col overflow-hidden"
        style={{ backgroundColor: theme.background_color }}
      >
        {/* Section accent strip */}
        <div
          className="h-8 w-full"
          style={{ backgroundColor: theme.section_color }}
        />
        {/* Accent bar */}
        <div
          className="h-1 w-full"
          style={{ backgroundColor: theme.accent_color }}
        />
        {/* Product bg swatch */}
        <div className="flex-1 p-2 flex gap-2">
          {[0, 1].map((i) => (
            <div
              key={i}
              className="flex-1 rounded-sm"
              style={{ backgroundColor: theme.product_bg_color }}
            />
          ))}
        </div>
        {/* Button swatch */}
        <div className="px-2 pb-2">
          <div
            className="h-5 w-16 rounded-sm"
            style={{ backgroundColor: theme.button_color }}
          />
        </div>

        {/* Selected checkmark overlay */}
        {isSelected && (
          <div className="absolute top-2 right-2 w-6 h-6 rounded-full bg-brand-primary flex items-center justify-center">
            <svg
              width="12"
              height="12"
              viewBox="0 0 12 12"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M2 6l3 3 5-5"
                stroke="white"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        )}
      </div>

      {/* Label */}
      <div className="px-2 pb-2 flex items-center justify-between">
        <span className="text-small-strong text-neutral-800 truncate">{theme.name}</span>
        <span className="text-caption text-neutral-400 flex-shrink-0 ml-1">Seed</span>
      </div>
    </button>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function ThemePickerDrawer({
  campaignId,
  currentPinnedThemeId,
  isOpen,
  onClose,
  onApply,
}: ThemePickerDrawerProps) {
  const [themes, setThemes] = useState<Theme[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [hasError, setHasError] = useState(false)
  const [selectedThemeId, setSelectedThemeId] = useState<string | null>(
    currentPinnedThemeId ?? null,
  )
  const [isApplying, setIsApplying] = useState(false)

  const fetchThemes = useCallback(async () => {
    setIsLoading(true)
    setHasError(false)
    try {
      const response = await api.get<Theme[]>('/themes')
      setThemes(response.data)
    } catch {
      setHasError(true)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen) {
      fetchThemes()
    }
  }, [isOpen, fetchThemes])

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

  const handleApply = async () => {
    if (!selectedThemeId) return
    const theme = themes.find((t) => t.id === selectedThemeId)
    if (!theme) return

    setIsApplying(true)
    try {
      await api.post(`/campaigns/${campaignId}/themes/apply`, {
        theme_id: selectedThemeId,
      })
      onApply(theme)
      showToast(`Theme "${theme.name}" applied`, 'success')
      onClose()
    } catch {
      showToast('Failed to apply theme', 'error')
    } finally {
      setIsApplying(false)
    }
  }

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

      {/* Drawer */}
      <aside
        className={[
          'fixed top-0 right-0 bottom-0 z-50 w-[480px] bg-neutral-0 shadow-elev-overlay',
          'flex flex-col transition-transform duration-[240ms]',
          isOpen ? 'translate-x-0' : 'translate-x-full',
        ].join(' ')}
        role="dialog"
        aria-modal="true"
        aria-label="Choose theme"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 flex-shrink-0">
          <h2 className="text-heading-2 text-neutral-800">Choose theme</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 transition-colors duration-[160ms] focus-visible:ring-2 focus-visible:ring-brand-primary rounded-sm"
            aria-label="Close theme picker"
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
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {/* Error */}
          {hasError && (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <p className="text-body text-neutral-600">Failed to load themes</p>
              <Button variant="secondary" size="sm" onClick={fetchThemes}>
                Retry
              </Button>
            </div>
          )}

          {/* Loading skeletons */}
          {isLoading && !hasError && (
            <div className="grid grid-cols-2 gap-4" aria-busy="true">
              {[...Array(6)].map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          )}

          {/* Theme grid */}
          {!isLoading && !hasError && themes.length > 0 && (
            <div className="grid grid-cols-2 gap-4">
              {themes.map((theme) => (
                <ThemeCard
                  key={theme.id}
                  theme={theme}
                  isSelected={selectedThemeId === theme.id}
                  onSelect={() => setSelectedThemeId(theme.id)}
                />
              ))}
            </div>
          )}

          {/* Empty */}
          {!isLoading && !hasError && themes.length === 0 && (
            <p className="text-small text-neutral-400 italic text-center mt-8">
              No themes available.
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-neutral-200 flex gap-3 justify-end flex-shrink-0">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={!selectedThemeId || isApplying}
            isLoading={isApplying}
            onClick={handleApply}
          >
            Apply theme
          </Button>
        </div>
      </aside>
    </>
  )
}
