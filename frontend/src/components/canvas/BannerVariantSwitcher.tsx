import React, { useState, useEffect, useRef } from 'react'
import { showToast } from '../ui/Toast'
import { api } from '../../lib/api'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Banner {
  id: string
  variant_index: number
  image_url: string
  is_active: boolean
  generation_status: 'pending' | 'generating' | 'ready' | 'failed'
}

interface BannerVariantSwitcherProps {
  campaignId: string
  banners: Banner[]
  onVariantActivated: (bannerId: string) => void
  onThumbFeedback: (bannerId: string, vote: 'up' | 'down') => void
  isGenerating: boolean
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function ShimmerSkeleton({ className = '' }: { className?: string }) {
  return (
    <div
      className={`bg-neutral-100 animate-pulse ${className}`}
      style={{
        backgroundImage:
          'linear-gradient(90deg, #EEF1F5 0%, #F8F9FB 50%, #EEF1F5 100%)',
        backgroundSize: '200% 100%',
      }}
    />
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface ActiveBannerSlotProps {
  banner: Banner | undefined
  isGenerating: boolean
}

function ActiveBannerSlot({ banner, isGenerating }: ActiveBannerSlotProps) {
  // Overall generating state (component-level) or banner-level generating
  const status = banner?.generation_status

  if (isGenerating || status === 'generating' || status === 'pending') {
    return (
      <div className="relative w-full aspect-[3/1] rounded-md overflow-hidden">
        <ShimmerSkeleton className="absolute inset-0 rounded-md" />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-caption text-neutral-400 animate-pulse">Generating…</span>
        </div>
      </div>
    )
  }

  if (status === 'failed') {
    return (
      <div className="w-full aspect-[3/1] rounded-md bg-neutral-100 flex flex-col items-center justify-center gap-2">
        <p className="text-small text-neutral-400">Banner generation failed</p>
        <button
          type="button"
          className="text-caption text-brand-primary hover:underline focus-visible:ring-2 focus-visible:ring-brand-primary rounded-sm"
        >
          Retry
        </button>
      </div>
    )
  }

  if (status === 'ready' && banner?.image_url) {
    return (
      <div className="w-full aspect-[3/1] rounded-md overflow-hidden bg-neutral-100">
        <img
          src={banner.image_url}
          alt="Active banner variant"
          className="w-full h-full object-cover transition-opacity duration-[240ms]"
        />
      </div>
    )
  }

  // No banner at all
  return (
    <div className="w-full aspect-[3/1] rounded-md bg-neutral-100 flex items-center justify-center">
      <span className="text-small text-neutral-400">No banner</span>
    </div>
  )
}

interface ThumbnailProps {
  banner: Banner
  isActive: boolean
  onActivate: () => void
  onFeedback: (vote: 'up' | 'down') => void
}

function Thumbnail({ banner, isActive, onActivate, onFeedback }: ThumbnailProps) {
  const [showFeedback, setShowFeedback] = useState(false)

  const status = banner.generation_status

  return (
    <div
      className="relative flex-shrink-0"
      onMouseEnter={() => setShowFeedback(true)}
      onMouseLeave={() => setShowFeedback(false)}
    >
      <button
        type="button"
        onClick={onActivate}
        className={[
          'w-20 h-10 rounded-sm overflow-hidden bg-neutral-100 block',
          'transition-all duration-[160ms]',
          'focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1',
          isActive ? 'ring-2 ring-brand-primary ring-offset-1' : 'ring-1 ring-neutral-200',
        ].join(' ')}
        aria-label={`Select banner variant ${banner.variant_index + 1}`}
        aria-pressed={isActive}
      >
        {status === 'ready' && banner.image_url ? (
          <img
            src={banner.image_url}
            alt={`Banner variant ${banner.variant_index + 1}`}
            className="w-full h-full object-cover"
          />
        ) : status === 'generating' || status === 'pending' ? (
          <ShimmerSkeleton className="w-full h-full" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-caption text-neutral-400">–</span>
          </div>
        )}
      </button>

      {/* Feedback overlay */}
      {showFeedback && status === 'ready' && (
        <div className="absolute inset-0 flex items-center justify-center gap-1 bg-black/30 rounded-sm transition-opacity duration-[160ms]">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onFeedback('up')
            }}
            className="w-6 h-6 flex items-center justify-center rounded-sm hover:bg-white/20 focus-visible:ring-2 focus-visible:ring-brand-primary"
            aria-label="Thumbs up for this banner variant"
          >
            👍
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation()
              onFeedback('down')
            }}
            className="w-6 h-6 flex items-center justify-center rounded-sm hover:bg-white/20 focus-visible:ring-2 focus-visible:ring-brand-primary"
            aria-label="Thumbs down for this banner variant"
          >
            👎
          </button>
        </div>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export function BannerVariantSwitcher({
  campaignId,
  banners,
  onVariantActivated,
  onThumbFeedback,
  isGenerating,
}: BannerVariantSwitcherProps) {
  const [localBanners, setLocalBanners] = useState<Banner[]>(banners)
  const prevStatusRef = useRef<Record<string, Banner['generation_status']>>({})

  // Sync external banners to local state
  useEffect(() => {
    // Check for generating→ready transitions and fire toast
    banners.forEach((banner) => {
      const prevStatus = prevStatusRef.current[banner.id]
      if (
        prevStatus === 'generating' &&
        banner.generation_status === 'ready'
      ) {
        showToast('✦ Banner generated', 'success')
      }
    })

    // Update prev status map
    const newPrevStatus: Record<string, Banner['generation_status']> = {}
    banners.forEach((b) => {
      newPrevStatus[b.id] = b.generation_status
    })
    prevStatusRef.current = newPrevStatus

    setLocalBanners(banners)
  }, [banners])

  const activeBanner = localBanners.find((b) => b.is_active)

  const handleActivate = async (bannerId: string) => {
    if (localBanners.find((b) => b.id === bannerId)?.is_active) return

    // Optimistic update
    setLocalBanners((prev) =>
      prev.map((b) => ({ ...b, is_active: b.id === bannerId })),
    )

    try {
      await api.patch(`/campaigns/${campaignId}/banners/${bannerId}/activate`)
      onVariantActivated(bannerId)
    } catch {
      // Revert on failure
      setLocalBanners(banners)
      showToast('Failed to activate banner variant', 'error')
    }
  }

  const handleFeedback = async (bannerId: string, vote: 'up' | 'down') => {
    onThumbFeedback(bannerId, vote)
  }

  // Show up to 3 thumbnails
  const thumbs = localBanners.slice(0, 3)

  return (
    <div className="flex flex-col gap-3">
      {/* Active banner slot */}
      <ActiveBannerSlot banner={activeBanner} isGenerating={isGenerating} />

      {/* Thumbnail row */}
      {thumbs.length > 0 && (
        <div className="flex gap-2 items-center" role="group" aria-label="Banner variants">
          {thumbs.map((banner) => (
            <Thumbnail
              key={banner.id}
              banner={banner}
              isActive={banner.is_active}
              onActivate={() => handleActivate(banner.id)}
              onFeedback={(vote) => handleFeedback(banner.id, vote)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
