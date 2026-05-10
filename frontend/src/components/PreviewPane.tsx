import React, { useCallback, useEffect, useRef, useState } from 'react'
import { BannerVariantSwitcher } from './canvas/BannerVariantSwitcher'
import type { Banner } from '../lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────

type Viewport = 'desktop' | 'mobile'

export interface PreviewPaneProps {
  campaignId: string
  renderHtml: string | null
  renderSizeKb: number
  sectionCount: number
  productCount: number
  isLoading: boolean
  onShare?: () => void
  onExport?: () => void
  banners?: Banner[]
  isGeneratingBanners?: boolean
  onBannerActivated?: (bannerId: string) => void
  onBannerFeedback?: (bannerId: string, vote: 'up' | 'down') => void
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionSkeleton() {
  return (
    <div className="bg-white rounded-lg border border-neutral-200 p-4 mb-3 animate-pulse">
      <div className="h-4 bg-neutral-200 rounded w-1/3 mb-3" />
      <div className="h-32 bg-neutral-100 rounded mb-3" />
      <div className="h-4 bg-neutral-200 rounded w-2/3 mb-2" />
      <div className="h-4 bg-neutral-200 rounded w-1/2" />
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="flex-1 overflow-y-auto p-6 bg-neutral-100">
      <div className="max-w-[600px] mx-auto">
        <SectionSkeleton />
        <SectionSkeleton />
        <SectionSkeleton />
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center bg-neutral-100 p-8">
      <div className="text-center max-w-sm">
        <div className="w-14 h-14 rounded-2xl bg-neutral-200 flex items-center justify-center mx-auto mb-5">
          {/* Info icon */}
          <svg
            width="28"
            height="28"
            viewBox="0 0 28 28"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <circle cx="14" cy="14" r="11" stroke="#8A94A6" strokeWidth="1.75" />
            <path d="M14 13v6" stroke="#8A94A6" strokeWidth="1.75" strokeLinecap="round" />
            <circle cx="14" cy="10" r="1" fill="#8A94A6" />
          </svg>
        </div>
        <h3 className="text-heading-3 text-neutral-600 mb-2">
          Sync a Google Sheet to see your preview
        </h3>
        <p className="text-body text-neutral-400">
          Connect a Google Sheet and run a full sync to generate your email preview.
        </p>
      </div>
    </div>
  )
}

interface ErrorStateProps {
  onRetry: () => void
}

function ErrorState({ onRetry }: ErrorStateProps) {
  return (
    <div className="flex-1 flex items-center justify-center bg-neutral-100 p-8">
      <div className="text-center max-w-sm">
        <div className="w-14 h-14 rounded-2xl bg-error-50 flex items-center justify-center mx-auto mb-5">
          <svg
            width="28"
            height="28"
            viewBox="0 0 28 28"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <circle cx="14" cy="14" r="11" stroke="#DC2626" strokeWidth="1.75" />
            <path d="M14 9v6" stroke="#DC2626" strokeWidth="1.75" strokeLinecap="round" />
            <circle cx="14" cy="18" r="1" fill="#DC2626" />
          </svg>
        </div>
        <h3 className="text-heading-3 text-neutral-800 mb-2">Render failed</h3>
        <p className="text-body text-neutral-400 mb-5">
          Unable to generate email preview. Check your data and try again.
        </p>
        <button
          type="button"
          onClick={onRetry}
          className="px-4 py-2 bg-brand-primary text-white rounded-md text-sm font-medium hover:opacity-90 transition-opacity"
        >
          Retry
        </button>
      </div>
    </div>
  )
}

// ── Viewport toggle ───────────────────────────────────────────────────────────

interface ViewportToggleProps {
  value: Viewport
  onChange: (v: Viewport) => void
}

function ViewportToggle({ value, onChange }: ViewportToggleProps) {
  return (
    <div className="flex items-center bg-neutral-100 rounded-lg p-0.5 gap-0.5">
      <button
        type="button"
        onClick={() => onChange('desktop')}
        className={[
          'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
          value === 'desktop'
            ? 'bg-white text-neutral-800 shadow-sm'
            : 'text-neutral-500 hover:text-neutral-700',
        ].join(' ')}
      >
        Desktop
      </button>
      <button
        type="button"
        onClick={() => onChange('mobile')}
        className={[
          'px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
          value === 'mobile'
            ? 'bg-white text-neutral-800 shadow-sm'
            : 'text-neutral-500 hover:text-neutral-700',
        ].join(' ')}
      >
        Mobile
      </button>
    </div>
  )
}

// ── KB readout colour ─────────────────────────────────────────────────────────

function kbColourClass(sizeKb: number): string {
  if (sizeKb >= 102) return 'text-red-600'
  if (sizeKb >= 90) return 'text-amber-600'
  return 'text-neutral-400'
}

// ── Share icon ────────────────────────────────────────────────────────────────

function ShareIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M11 1.5a2 2 0 1 1 .001 3.999A2 2 0 0 1 11 1.5ZM5 6a2 2 0 1 1 .001 3.999A2 2 0 0 1 5 6Zm6 4.5a2 2 0 1 1 .001 3.999A2 2 0 0 1 11 10.5Z"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M9.07 3.93 6.93 5.57M9.07 12.07l-2.14-1.64"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
      />
    </svg>
  )
}

function ExportIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M8 2v8M5 7l3 3 3-3"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M2 11v2a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1v-2"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
      />
    </svg>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function PreviewPane({
  campaignId,
  renderHtml,
  renderSizeKb,
  sectionCount,
  productCount,
  isLoading,
  onShare,
  onExport,
  banners = [],
  isGeneratingBanners = false,
  onBannerActivated,
  onBannerFeedback,
}: PreviewPaneProps) {
  const [viewport, setViewport] = useState<Viewport>('desktop')
  const [renderError, setRenderError] = useState(false)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  // Reset error when new HTML arrives
  useEffect(() => {
    if (renderHtml) {
      setRenderError(false)
    }
  }, [renderHtml])

  // Keyboard shortcuts: D = Desktop, M = Mobile
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore when focus is inside an input/textarea/select
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase()
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return

      if (e.key === 'd' || e.key === 'D') {
        setViewport('desktop')
      } else if (e.key === 'm' || e.key === 'M') {
        setViewport('mobile')
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [])

  const handleRetry = useCallback(() => {
    setRenderError(false)
  }, [])

  const iframeWidth = viewport === 'desktop' ? 600 : 375

  // ── Determine state ───────────────────────────────────────────────────────
  const showEmpty = !isLoading && !renderHtml && !renderError
  const showLoading = isLoading
  const showError = renderError && !isLoading
  const showPreview = !isLoading && !renderError && Boolean(renderHtml)

  return (
    <div className="flex-1 flex flex-col bg-neutral-100 overflow-hidden min-h-0">
      {/* Toolbar */}
      <div className="flex-shrink-0 bg-white border-b border-neutral-200 px-4 py-2 flex items-center justify-between gap-3">
        {/* Left: viewport toggle */}
        <ViewportToggle value={viewport} onChange={setViewport} />

        {/* Right: action buttons */}
        <div className="flex items-center gap-2">
          {onShare && (
            <button
              type="button"
              onClick={onShare}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-neutral-600 hover:bg-neutral-100 transition-colors"
            >
              <ShareIcon />
              Share
            </button>
          )}
          {onExport && (
            <button
              type="button"
              onClick={onExport}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium bg-brand-primary text-white hover:opacity-90 transition-opacity"
            >
              <ExportIcon />
              Export
            </button>
          )}
        </div>
      </div>

      {/* Banner variant switcher — shown only when banners exist */}
      {(banners.length > 0 || isGeneratingBanners) && (
        <div className="flex-shrink-0 border-b border-neutral-200 bg-white">
          <BannerVariantSwitcher
            campaignId={campaignId}
            banners={banners}
            isGenerating={isGeneratingBanners}
            onVariantActivated={onBannerActivated ?? (() => {})}
            onThumbFeedback={onBannerFeedback ?? (() => {})}
          />
        </div>
      )}

      {/* Preview area */}
      <div className="flex-1 overflow-auto bg-neutral-100 min-h-0">
        {showLoading && <LoadingSkeleton />}
        {showEmpty && <EmptyState />}
        {showError && <ErrorState onRetry={handleRetry} />}

        {showPreview && (
          <div className="flex justify-center py-6 px-4 min-h-full">
            <div
              className="flex-shrink-0 overflow-hidden rounded-sm shadow-sm"
              style={{
                width: `${iframeWidth}px`,
                transition: 'width 240ms cubic-bezier(0.2, 0.8, 0.2, 1)',
              }}
            >
              <iframe
                ref={iframeRef}
                srcDoc={renderHtml ?? ''}
                sandbox="allow-same-origin"
                title="Email preview"
                className="border border-neutral-200 bg-white block"
                style={{
                  width: `${iframeWidth}px`,
                  height: '800px',
                  transition: 'width 240ms cubic-bezier(0.2, 0.8, 0.2, 1)',
                }}
                onError={() => setRenderError(true)}
              />
            </div>
          </div>
        )}
      </div>

      {/* Footer status strip */}
      <div className="flex-shrink-0 bg-neutral-50 border-t border-neutral-200 px-4 py-2 flex items-center gap-4 text-xs">
        {/* KB readout */}
        <span className={renderSizeKb > 0 ? kbColourClass(renderSizeKb) : 'text-neutral-300'}>
          {renderSizeKb > 0 ? `${renderSizeKb.toFixed(1)} KB` : '— KB'}
        </span>

        {/* Section / product counts */}
        <span className="text-neutral-500">
          {sectionCount > 0 ? (
            <>
              <span className="text-neutral-700 font-medium">{sectionCount}</span>
              {' '}section{sectionCount !== 1 ? 's' : ''}
            </>
          ) : (
            <span className="text-neutral-300">0 sections</span>
          )}
        </span>
        <span className="text-neutral-500">
          {productCount > 0 ? (
            <>
              <span className="text-neutral-700 font-medium">{productCount}</span>
              {' '}product{productCount !== 1 ? 's' : ''}
            </>
          ) : (
            <span className="text-neutral-300">0 products</span>
          )}
        </span>

        {/* Spacer */}
        <span className="flex-1" />

        {/* Co-editor placeholder */}
        <span className="text-neutral-300 italic">— no co-editors</span>
      </div>
    </div>
  )
}
