import React, { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { listCampaigns, type Campaign, type CampaignStatus } from '../lib/api'
import { TopBar } from '../components/layout/TopBar'
import { StatusPill } from '../components/ui/Pill'
import { CampaignCardSkeleton } from '../components/ui/Skeleton'
import { showToast } from '../components/ui/Toast'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ReviewTokenInfo {
  token: string
  campaign_id: string
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Attempts to retrieve the review token for a campaign from the auth token
 * metadata or a locally cached map. Since there is no dedicated reviewer
 * endpoint yet, tokens are retrieved from localStorage if available (stored
 * by the invitation flow) or fall back to `null`.
 */
function getReviewToken(campaignId: string): string | null {
  try {
    const raw = localStorage.getItem('review_tokens')
    if (!raw) return null
    const map: Record<string, string> = JSON.parse(raw)
    return map[campaignId] ?? null
  } catch {
    return null
  }
}

// ── Campaign review card ──────────────────────────────────────────────────────

interface ReviewCardProps {
  campaign: Campaign
}

function ReviewCard({ campaign }: ReviewCardProps) {
  const navigate = useNavigate()
  const token = getReviewToken(campaign.id)

  const updatedAgo = formatDistanceToNow(new Date(campaign.updated_at), {
    addSuffix: true,
  })

  const handleOpen = () => {
    if (token) {
      navigate(`/preview/${token}`)
    } else {
      showToast('Preview link not available for this campaign', 'warn')
    }
  }

  return (
    <article className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-neutral-0 rounded-lg border border-neutral-200 shadow-elev-flat px-5 py-4 hover:shadow-elev-raised transition-shadow duration-200">
      <div className="flex flex-col gap-1.5 min-w-0">
        <h3 className="text-body-strong text-neutral-800 truncate">{campaign.name}</h3>
        <div className="flex items-center gap-3 flex-wrap">
          <StatusPill status={campaign.status} />
          <span className="text-small text-neutral-400">Updated {updatedAgo}</span>
        </div>
      </div>

      <button
        type="button"
        onClick={handleOpen}
        disabled={!token}
        aria-label={`Open preview for ${campaign.name}`}
        className={[
          'flex-shrink-0 h-8 px-4 rounded-md text-small-strong transition-colors focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-1',
          token
            ? 'bg-brand-primary text-neutral-0 hover:bg-brand-primary-hover'
            : 'bg-neutral-100 text-neutral-400 cursor-not-allowed',
        ].join(' ')}
      >
        Open preview
      </button>
    </article>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center gap-4">
      <div className="w-16 h-16 rounded-2xl bg-brand-primary-soft flex items-center justify-center">
        <svg
          width="32"
          height="32"
          viewBox="0 0 32 32"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <rect x="4" y="6" width="24" height="20" rx="3" stroke="#2E5BFF" strokeWidth="2" />
          <path d="M4 13H28" stroke="#2E5BFF" strokeWidth="2" />
          <path d="M10 19H22" stroke="#2E5BFF" strokeWidth="1.75" strokeLinecap="round" />
          <path d="M10 23H16" stroke="#2E5BFF" strokeWidth="1.75" strokeLinecap="round" />
        </svg>
      </div>
      <h2 className="text-heading-2 text-neutral-900">No campaigns shared with you</h2>
      <p className="text-body text-neutral-400 max-w-[400px]">
        Campaigns shared for review will appear here. Ask the campaign owner to send you a review link.
      </p>
    </div>
  )
}

// ── Filter tabs ───────────────────────────────────────────────────────────────

type FilterTab = 'all' | CampaignStatus

const FILTER_TABS: { label: string; value: FilterTab }[] = [
  { label: 'All', value: 'all' },
  { label: 'Draft', value: 'draft' },
  { label: 'In Review', value: 'in_review' },
  { label: 'Approved', value: 'approved' },
]

// ── Page ──────────────────────────────────────────────────────────────────────

export function ReviewerDashboardPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState<FilterTab>('all')

  const fetchCampaigns = useCallback(async (filter: FilterTab) => {
    setIsLoading(true)
    try {
      const result = await listCampaigns({
        status: filter === 'all' ? undefined : filter,
      })
      setCampaigns(result.items)
    } catch {
      showToast('Failed to load campaigns', 'error')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchCampaigns(activeFilter)
  }, [activeFilter, fetchCampaigns])

  return (
    <div className="min-h-screen flex flex-col bg-neutral-50">
      <TopBar />

      {/* Page header */}
      <div className="sticky top-0 z-10 bg-neutral-50 border-b border-neutral-200">
        <div className="max-w-3xl mx-auto px-4 sm:px-6">
          <div className="flex items-center h-[72px]">
            <h1 className="text-heading-1 text-neutral-900">Campaigns for review</h1>
          </div>

          {/* Filter tabs */}
          <div className="flex gap-1 -mb-px">
            {FILTER_TABS.map((tab) => (
              <button
                key={tab.value}
                type="button"
                onClick={() => setActiveFilter(tab.value)}
                aria-current={activeFilter === tab.value ? 'page' : undefined}
                className={[
                  'px-4 py-2.5 text-body-strong border-b-2 transition-colors duration-150 whitespace-nowrap',
                  activeFilter === tab.value
                    ? 'border-brand-primary text-brand-primary'
                    : 'border-transparent text-neutral-600 hover:text-neutral-800 hover:border-neutral-200',
                ].join(' ')}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="flex-1 max-w-3xl mx-auto w-full px-4 sm:px-6 py-6">
        <p className="text-small text-neutral-400 mb-4">
          View campaigns shared with you
        </p>

        {isLoading ? (
          <div className="flex flex-col gap-3" aria-busy="true">
            {Array.from({ length: 4 }).map((_, i) => (
              <CampaignCardSkeleton key={i} />
            ))}
          </div>
        ) : campaigns.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="flex flex-col gap-3">
            {campaigns.map((campaign) => (
              <ReviewCard key={campaign.id} campaign={campaign} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
