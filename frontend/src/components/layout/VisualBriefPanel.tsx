import React, { useState } from 'react'
import { Button } from '../ui/Button'
import type { VisualBrief } from '../../lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────

interface VisualBriefPanelProps {
  brief: VisualBrief | null
  isLoading: boolean
  onVibeShift: () => void
  onOverrideTheme: () => void
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function firstFontName(fontStack: string): string {
  return fontStack.split(',')[0].replace(/["']/g, '').trim()
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SparkleIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 12 12"
      fill="none"
      aria-hidden="true"
      className="flex-shrink-0"
    >
      <path
        d="M6 1l1.12 3.28L10.5 6 7.12 7.72 6 11 4.88 7.72 1.5 6l3.38-1.72L6 1z"
        fill="currentColor"
      />
    </svg>
  )
}

function AiProvPill() {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-caption font-medium"
      style={{ backgroundColor: '#EDE4FF', color: '#7B3FE4' }}
    >
      <SparkleIcon />
      AI
    </span>
  )
}

interface SwatchProps {
  color: string
  label: string
}

function Swatch({ color, label }: SwatchProps) {
  const [showTooltip, setShowTooltip] = useState(false)

  return (
    <div className="relative">
      <button
        type="button"
        title={`${label}: ${color}`}
        aria-label={`${label}: ${color}`}
        className="w-6 h-6 rounded-sm border border-neutral-200 transition-transform hover:scale-110 focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1"
        style={{ backgroundColor: color }}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onFocus={() => setShowTooltip(true)}
        onBlur={() => setShowTooltip(false)}
      />
      {showTooltip && (
        <div
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 z-50 pointer-events-none"
          role="tooltip"
        >
          <div className="bg-neutral-900 text-neutral-0 text-caption px-2 py-1 rounded-sm whitespace-nowrap font-mono shadow-elev-overlay">
            {color}
          </div>
          <div className="w-2 h-2 bg-neutral-900 rotate-45 mx-auto -mt-1" />
        </div>
      )}
    </div>
  )
}

function SkeletonRow({ width = 'w-full' }: { width?: string }) {
  return (
    <div
      className={`h-4 rounded-sm bg-neutral-100 ${width} animate-shimmer`}
      style={{
        backgroundImage:
          'linear-gradient(90deg, #EEF1F5 0%, #F8F9FB 50%, #EEF1F5 100%)',
        backgroundSize: '200% 100%',
      }}
    />
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function VisualBriefPanel({
  brief,
  isLoading,
  onVibeShift,
  onOverrideTheme,
}: VisualBriefPanelProps) {
  // Stub for neutral defaults toggle (wired to preference memory in Issue 17)
  const [useNeutral, setUseNeutral] = useState(brief?.use_neutral_defaults ?? false)

  const palette: Array<{ color: string; label: string }> = brief
    ? [
        { color: brief.background_color, label: 'Background' },
        { color: brief.section_color, label: 'Section' },
        { color: brief.accent_color, label: 'Accent' },
        { color: brief.button_color, label: 'Button' },
        { color: brief.product_bg_color, label: 'Product bg' },
      ]
    : []

  return (
    <div className="border-t border-neutral-200">
      {/* Panel header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-2">
        <span className="text-small-strong uppercase tracking-wider text-neutral-600">
          Visual Brief
        </span>
        <AiProvPill />
      </div>

      {/* Empty state */}
      {!isLoading && !brief && (
        <div className="px-4 pb-4">
          <p className="text-small text-neutral-400 italic">
            Awaiting first sync — run Full Sync to generate a visual brief.
          </p>
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <div className="px-4 pb-4 flex flex-col gap-3" aria-busy="true">
          <SkeletonRow width="w-3/4" />
          <div className="flex gap-1.5">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className="w-6 h-6 rounded-sm bg-neutral-100 animate-shimmer"
                style={{
                  backgroundImage:
                    'linear-gradient(90deg, #EEF1F5 0%, #F8F9FB 50%, #EEF1F5 100%)',
                  backgroundSize: '200% 100%',
                }}
              />
            ))}
          </div>
          <SkeletonRow width="w-full" />
          <SkeletonRow width="w-2/3" />
          <SkeletonRow width="w-1/2" />
        </div>
      )}

      {/* Success state */}
      {!isLoading && brief && (
        <div className="px-4 pb-4 flex flex-col gap-3">
          {/* Theme name */}
          <p className="text-body-strong text-neutral-800 truncate" title={brief.theme_name}>
            "{brief.theme_name}"
          </p>

          {/* Palette swatches */}
          <div className="flex items-center gap-2">
            <span className="text-small text-neutral-400 flex-shrink-0 w-16">Palette</span>
            <div className="flex gap-1.5">
              {palette.map(({ color, label }) => (
                <Swatch key={label} color={color} label={label} />
              ))}
            </div>
          </div>

          {/* Template */}
          <div className="flex items-center gap-2">
            <span className="text-small text-neutral-400 flex-shrink-0 w-16">Template</span>
            <button
              type="button"
              onClick={onOverrideTheme}
              className="text-small text-brand-primary hover:underline text-left truncate"
              title="Open template picker"
            >
              {brief.template_id ?? 'Default'}
              {brief.pinned_theme_id && (
                <span className="ml-1 text-caption text-neutral-400">· pinned</span>
              )}
            </button>
          </div>

          {/* Fonts */}
          <div className="flex items-center gap-2">
            <span className="text-small text-neutral-400 flex-shrink-0 w-16">Fonts</span>
            <span className="text-small text-neutral-600 font-mono truncate">
              {firstFontName(brief.heading_font)} / {brief.h1_size}·{brief.h2_size}·{brief.body_size}
            </span>
          </div>

          {/* Preferences influence line */}
          <div className="flex items-start justify-between gap-2 pt-1">
            <p className="text-small text-info-600 flex-1 leading-tight">
              Influenced by your preferences
            </p>
            <button
              type="button"
              className={[
                'flex-shrink-0 relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-150',
                'focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1',
                useNeutral ? 'bg-brand-primary' : 'bg-neutral-200',
              ].join(' ')}
              role="switch"
              aria-checked={useNeutral}
              aria-label="Use neutral defaults this time"
              onClick={() => setUseNeutral((v) => !v)}
              title={useNeutral ? 'Using neutral defaults' : 'Using your preferences'}
            >
              <span
                className={[
                  'inline-block h-3.5 w-3.5 rounded-full bg-neutral-0 shadow transition-transform duration-150',
                  useNeutral ? 'translate-x-4' : 'translate-x-0.5',
                ].join(' ')}
              />
            </button>
          </div>
          {useNeutral && (
            <p className="text-caption text-neutral-400 -mt-1">
              Neutral defaults active for this campaign
            </p>
          )}

          {/* Action buttons */}
          <div className="flex gap-2 pt-1">
            <Button
              variant="secondary"
              size="sm"
              className="flex-1"
              onClick={onVibeShift}
              leftIcon={<SparkleIcon />}
            >
              Vibe Shift
            </Button>
            <Button
              variant="secondary"
              size="sm"
              className="flex-1"
              onClick={onOverrideTheme}
            >
              Override theme
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
