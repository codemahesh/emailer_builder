import React, { useState } from 'react'
import { type Product } from '../../lib/api'
import { QualityWarningCard } from '../QualityWarningCard'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface QualityWarningsPanelProps {
  campaignId: string
  products: Product[]
  onProductUpdated: (updatedProduct: Product) => void
}

// FAIL: processing failed or scrape failed — cannot be dismissed without replacement
// WARN: low-res image that was processed with upscaling — can be kept
type IssueKind = 'FAIL' | 'WARN'

interface ProductIssue {
  product: Product
  kind: IssueKind
  description: string
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Derive quality issues from the products array.
 *
 * FAIL: scrape_failed=true OR processed_image_url === '/static/coming-soon.svg'
 * WARN: processed_image_url is set (a real URL, not coming-soon) and
 *       scraped_image_url exists — indicates the image was upscaled from a
 *       low-res source. The presence of processed_image_url with the scraped
 *       one intact means a WARN-verdict image was processed.
 *
 * The backend emits 'warn' verdict events for low-res images. Since we
 * can't store per-product verdict in the Product model yet, we derive WARN
 * from products whose processed_image_url differs from their scraped_image_url
 * and both are non-null non-fallback values. FAIL is derived from scrape_failed
 * or fallback URL.
 */
function buildIssues(products: Product[]): ProductIssue[] {
  const issues: ProductIssue[] = []

  for (const p of products) {
    const hasFallbackUrl =
      p.processed_image_url === '/static/coming-soon.svg' ||
      p.scraped_image_url === '/static/coming-soon.svg'

    if (p.scrape_failed || hasFallbackUrl) {
      issues.push({
        product: p,
        kind: 'FAIL',
        description: p.scrape_failed
          ? 'Image processing failed — cannot be used'
          : 'Image unavailable — no valid source found',
      })
    } else if (
      p.processed_image_url &&
      p.scraped_image_url &&
      p.processed_image_url !== p.scraped_image_url
    ) {
      // Processed image differs from scraped → likely upscaled from low-res (WARN)
      // Only show as WARN if there's a processed result (not coming-soon)
      issues.push({
        product: p,
        kind: 'WARN',
        description: 'Low-resolution image — upscaled for email use',
      })
    }
  }

  return issues
}

// ── Icons ─────────────────────────────────────────────────────────────────────

/** Stop-octagon icon for FAIL items. */
function FailIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      className="flex-shrink-0 text-error-600"
      aria-hidden="true"
    >
      {/* Octagon shape */}
      <path
        d="M4.5 1.5h5L13 5v4l-3.5 3.5h-5L1 9V5l3.5-3.5z"
        stroke="currentColor"
        strokeWidth="1.25"
        fill="currentColor"
        fillOpacity="0.1"
      />
      {/* X mark */}
      <path
        d="M5 5l4 4M9 5l-4 4"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
      />
    </svg>
  )
}

/** Warn-triangle icon for WARN items. */
function WarnIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 14 14"
      fill="none"
      className="flex-shrink-0 text-warning-600"
      aria-hidden="true"
    >
      <path
        d="M7 5.25v2.5M7 9.25v.25M1.5 11.5h11L7 2.5l-5.5 9z"
        stroke="currentColor"
        strokeWidth="1.25"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function QualityWarningsPanel({
  campaignId,
  products,
  onProductUpdated,
}: QualityWarningsPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set())
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null)

  // Rebuild issues whenever products change (WebSocket updates flow through here)
  const allIssues = buildIssues(products)

  // FAIL items can never be dismissed — only replaced.
  // WARN items can be dismissed with "Keep".
  const visibleIssues = allIssues.filter(
    (issue) => issue.kind === 'FAIL' || !dismissedIds.has(issue.product.id),
  )

  // Nothing to show if no issues remain
  if (visibleIssues.length === 0) return null

  const failCount = visibleIssues.filter((i) => i.kind === 'FAIL').length
  const hasAnyFail = failCount > 0

  const handleKeep = (productId: string) => {
    setDismissedIds((prev) => new Set([...prev, productId]))
  }

  const handleReplaced = (issue: ProductIssue, newImageUrl: string) => {
    onProductUpdated({
      ...issue.product,
      processed_image_url: newImageUrl,
      scraped_image_url: newImageUrl,
      scrape_failed: false,
    })
    setSelectedProduct(null)
  }

  return (
    <>
      {/* Panel */}
      <div className="border-t border-neutral-200">
        {/* Collapsed header — always visible */}
        <button
          type="button"
          className={[
            'w-full flex items-center justify-between px-4 py-3 transition-colors',
            hasAnyFail
              ? 'hover:bg-error-50'
              : 'hover:bg-neutral-100',
          ].join(' ')}
          onClick={() => setIsExpanded((v) => !v)}
          aria-expanded={isExpanded}
        >
          <div className="flex items-center gap-2">
            {/* Red dot if any FAIL */}
            {hasAnyFail && (
              <span
                className="w-2 h-2 rounded-full bg-error-600 flex-shrink-0"
                aria-label="Has critical issues"
              />
            )}
            <span
              className={[
                'text-small-strong uppercase tracking-wider',
                hasAnyFail ? 'text-error-700' : 'text-neutral-700',
              ].join(' ')}
            >
              Quality
            </span>
            <span
              className={[
                'text-small px-1.5 py-0.5 rounded-full font-semibold',
                hasAnyFail
                  ? 'bg-error-50 text-error-700'
                  : 'bg-warning-50 text-warning-700',
              ].join(' ')}
            >
              {visibleIssues.length}
            </span>
          </div>

          {/* Chevron */}
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            className={[
              'transition-transform duration-200',
              hasAnyFail ? 'text-error-500' : 'text-neutral-400',
              isExpanded ? 'rotate-180' : '',
            ].join(' ')}
            aria-hidden="true"
          >
            <path
              d="M4 6l4 4 4-4"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>

        {/* Expanded issue list */}
        {isExpanded && (
          <div className="flex flex-col divide-y divide-neutral-100">
            {visibleIssues.map((issue) => (
              <div
                key={issue.product.id}
                className={[
                  'flex items-start gap-3 px-4 py-3',
                  issue.kind === 'FAIL' ? 'bg-error-50/40' : '',
                ].join(' ')}
              >
                {/* Icon */}
                <div className="mt-0.5">
                  {issue.kind === 'FAIL' ? <FailIcon /> : <WarnIcon />}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-small-strong text-neutral-800 truncate">
                    {issue.product.scraped_name ?? issue.product.sku}
                  </p>
                  <p className="text-small text-neutral-400 truncate">
                    {issue.product.sku}
                  </p>
                  <p
                    className={[
                      'text-small mt-0.5',
                      issue.kind === 'FAIL'
                        ? 'text-error-600'
                        : 'text-warning-600',
                    ].join(' ')}
                  >
                    {issue.description}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex flex-col gap-1 flex-shrink-0">
                  <button
                    type="button"
                    className="text-small-strong text-brand-primary hover:underline"
                    onClick={() => setSelectedProduct(issue.product)}
                  >
                    Replace
                  </button>
                  {/* FAIL items cannot be dismissed — only replaced */}
                  {issue.kind === 'WARN' && (
                    <button
                      type="button"
                      className="text-small text-neutral-400 hover:text-neutral-600 hover:underline"
                      onClick={() => handleKeep(issue.product.id)}
                    >
                      Keep
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* QualityWarningCard modal */}
      {selectedProduct && (
        <QualityWarningCard
          isOpen={Boolean(selectedProduct)}
          onClose={() => setSelectedProduct(null)}
          product={selectedProduct}
          campaignId={campaignId}
          onReplaced={(newImageUrl) => {
            const issue = visibleIssues.find(
              (i) => i.product.id === selectedProduct.id,
            )
            if (issue) handleReplaced(issue, newImageUrl)
          }}
        />
      )}
    </>
  )
}
