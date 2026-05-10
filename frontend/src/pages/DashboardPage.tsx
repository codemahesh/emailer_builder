import React, { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import {
  listCampaigns,
  createCampaign,
  duplicateCampaign,
  archiveCampaign,
  type Campaign,
  type CampaignStatus,
} from '../lib/api'
import { useAuth } from '../hooks/useAuth'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Modal } from '../components/ui/Modal'
import { StatusPill } from '../components/ui/Pill'
import { CampaignCardSkeleton } from '../components/ui/Skeleton'
import { showToast } from '../components/ui/Toast'
import { TopBar } from '../components/layout/TopBar'

type FilterTab = 'all' | CampaignStatus

const filterTabs: { label: string; value: FilterTab }[] = [
  { label: 'All', value: 'all' },
  { label: 'Draft', value: 'draft' },
  { label: 'In Review', value: 'in_review' },
  { label: 'Approved', value: 'approved' },
]

// ─── Campaign Card ────────────────────────────────────────────────────────────

interface CampaignCardProps {
  campaign: Campaign
  onClick: () => void
  onDuplicated: (newCampaign: Campaign) => void
  onArchived: (campaignId: string) => void
}

function OverflowMenu({
  onDuplicate,
  onArchive,
  isDuplicating = false,
  isArchiving = false,
}: {
  onDuplicate: () => void
  onArchive: () => void
  isDuplicating?: boolean
  isArchiving?: boolean
}) {
  const [open, setOpen] = useState(false)
  const ref = React.useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation()
          setOpen((v) => !v)
        }}
        className="w-7 h-7 flex items-center justify-center rounded-md text-neutral-400 hover:text-neutral-800 hover:bg-neutral-100 transition-colors text-body-strong"
        aria-haspopup="true"
        aria-expanded={open}
        aria-label="More options"
      >
        ⋯
      </button>
      {open && (
        <div className="absolute right-0 top-8 w-40 bg-neutral-0 rounded-lg shadow-elev-overlay border border-neutral-100 overflow-hidden z-10">
          <button
            type="button"
            disabled={isDuplicating}
            className="w-full text-left px-4 py-2 text-body text-neutral-800 hover:bg-neutral-50 transition-colors disabled:opacity-50"
            onClick={(e) => {
              e.stopPropagation()
              setOpen(false)
              onDuplicate()
            }}
          >
            {isDuplicating ? 'Duplicating…' : 'Duplicate'}
          </button>
          <button
            type="button"
            disabled={isArchiving}
            className="w-full text-left px-4 py-2 text-body text-danger-600 hover:bg-danger-50 transition-colors disabled:opacity-50"
            onClick={(e) => {
              e.stopPropagation()
              setOpen(false)
              onArchive()
            }}
          >
            {isArchiving ? 'Archiving…' : 'Archive'}
          </button>
        </div>
      )}
    </div>
  )
}

function CampaignCard({ campaign, onClick, onDuplicated, onArchived }: CampaignCardProps) {
  const [isDuplicating, setIsDuplicating] = useState(false)
  const [isArchiving, setIsArchiving] = useState(false)
  const updatedAgo = formatDistanceToNow(new Date(campaign.updated_at), {
    addSuffix: true,
  })
  const ownerLabel = campaign.owner?.email?.split('@')[0] ?? 'unknown'

  const handleDuplicate = async () => {
    setIsDuplicating(true)
    try {
      const newCampaign = await duplicateCampaign(campaign.id)
      onDuplicated(newCampaign)
      showToast(`"${newCampaign.name}" created`, 'success')
    } catch {
      showToast('Failed to duplicate campaign', 'error')
    } finally {
      setIsDuplicating(false)
    }
  }

  const handleArchive = async () => {
    setIsArchiving(true)
    try {
      await archiveCampaign(campaign.id)
      onArchived(campaign.id)
      showToast('Campaign archived', 'info')
    } catch {
      showToast('Failed to archive campaign', 'error')
    } finally {
      setIsArchiving(false)
    }
  }

  return (
    <article
      className="flex flex-col rounded-lg border border-neutral-200 bg-neutral-0 shadow-elev-flat hover:shadow-elev-raised transition-shadow duration-200 cursor-pointer min-h-[240px] overflow-hidden"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onClick()
        }
      }}
      aria-label={`Open campaign: ${campaign.name}`}
    >
      {/* Thumbnail */}
      <div className="h-[160px] bg-neutral-100 flex items-center justify-center flex-shrink-0 border-b border-neutral-100">
        <svg
          width="40"
          height="40"
          viewBox="0 0 40 40"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="text-neutral-300"
        >
          <rect x="4" y="8" width="32" height="24" rx="4" stroke="currentColor" strokeWidth="2" />
          <path d="M4 16H36" stroke="currentColor" strokeWidth="2" />
          <path d="M12 24H28" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
          <path d="M12 28.5H21" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" />
        </svg>
      </div>

      {/* Body */}
      <div className="flex flex-col flex-1 p-4 gap-2">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-body-strong text-neutral-800 line-clamp-2 flex-1 min-w-0">
            {campaign.name}
          </h3>
          <OverflowMenu
            onDuplicate={handleDuplicate}
            onArchive={handleArchive}
            isDuplicating={isDuplicating}
            isArchiving={isArchiving}
          />
        </div>

        <StatusPill status={campaign.status} />

        <p className="text-small text-neutral-400 mt-auto">
          Edited {updatedAgo} · {ownerLabel}
        </p>
      </div>
    </article>
  )
}

// ─── New Campaign Modal ───────────────────────────────────────────────────────

interface NewCampaignModalProps {
  isOpen: boolean
  onClose: () => void
  onCreated: (campaign: Campaign) => void
}

function NewCampaignModal({ isOpen, onClose, onCreated }: NewCampaignModalProps) {
  const [name, setName] = useState('')
  const [sheetUrl, setSheetUrl] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errors, setErrors] = useState<{ name?: string; sheetUrl?: string }>({})

  const serviceAccountEmail =
    import.meta.env.VITE_SERVICE_ACCOUNT_EMAIL ??
    'emailer-builder@your-project.iam.gserviceaccount.com'

  const isValid = name.trim().length > 0

  const resetForm = () => {
    setName('')
    setSheetUrl('')
    setErrors({})
  }

  const handleClose = () => {
    resetForm()
    onClose()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValid) return

    setIsSubmitting(true)
    try {
      const campaign = await createCampaign({
        name: name.trim(),
        sheet_url: sheetUrl.trim(),
      })
      onCreated(campaign)
      resetForm()
      showToast(`Campaign "${campaign.name}" created`, 'success')
    } catch {
      showToast('Failed to create campaign', 'error')
    } finally {
      setIsSubmitting(false)
    }
  }

  const [copied, setCopied] = useState(false)
  const handleCopyEmail = async () => {
    await navigator.clipboard.writeText(serviceAccountEmail)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="New Campaign" width="md">
      <form onSubmit={handleSubmit} className="flex flex-col gap-5 px-6 py-5">
        {/* Service account hint */}
        <div className="flex flex-col gap-2">
          <p className="text-small text-neutral-600">
            Share your Google Sheet with this service account before connecting:
          </p>
          <div className="flex items-center gap-2 bg-neutral-100 rounded-md px-3 py-2 border border-neutral-200">
            <span className="text-small text-neutral-600 font-mono truncate flex-1 min-w-0">
              {serviceAccountEmail}
            </span>
            <button
              type="button"
              onClick={handleCopyEmail}
              className="flex-shrink-0 text-small-strong text-brand-primary hover:text-brand-primary-hover transition-colors"
            >
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
        </div>

        <Input
          label="Campaign name"
          placeholder="e.g. Summer 2025 Newsletter"
          value={name}
          onChange={(e) => {
            setName(e.target.value)
            if (errors.name) setErrors((prev) => ({ ...prev, name: undefined }))
          }}
          error={errors.name}
          required
          autoFocus
        />

        <Input
          label="Google Sheet URL"
          type="url"
          placeholder="https://docs.google.com/spreadsheets/d/..."
          value={sheetUrl}
          onChange={(e) => {
            setSheetUrl(e.target.value)
            if (errors.sheetUrl)
              setErrors((prev) => ({ ...prev, sheetUrl: undefined }))
          }}
          error={errors.sheetUrl}
          helperText="Optional — you can add this later in the workspace"
        />

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 pt-1 border-t border-neutral-100 -mx-6 px-6 pb-1 mt-1">
          <Button
            type="button"
            variant="ghost"
            onClick={handleClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            isLoading={isSubmitting}
            disabled={!isValid || isSubmitting}
          >
            Create Campaign
          </Button>
        </div>
      </form>
    </Modal>
  )
}

// ─── Dashboard Page ───────────────────────────────────────────────────────────

export function DashboardPage() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [total, setTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState<FilterTab>('all')
  const [showNewModal, setShowNewModal] = useState(false)

  const fetchCampaigns = useCallback(
    async (filter: FilterTab) => {
      setIsLoading(true)
      try {
        const result = await listCampaigns({
          status: filter === 'all' ? undefined : filter,
        })
        setCampaigns(result.items)
        setTotal(result.total)
      } catch {
        showToast('Failed to load campaigns', 'error')
      } finally {
        setIsLoading(false)
      }
    },
    [],
  )

  useEffect(() => {
    fetchCampaigns(activeFilter)
  }, [activeFilter, fetchCampaigns])

  const handleFilterChange = (filter: FilterTab) => {
    setActiveFilter(filter)
  }

  const handleCampaignCreated = (campaign: Campaign) => {
    setShowNewModal(false)
    navigate(`/campaigns/${campaign.id}`)
  }

  const handleCardClick = (campaignId: string) => {
    navigate(`/campaigns/${campaignId}`)
  }

  const isFirstName = user?.email?.split('@')[0] ?? 'there'

  return (
    <div className="min-h-screen flex flex-col bg-neutral-50">
      <TopBar />

      {/* Dashboard header */}
      <div className="sticky top-0 z-10 bg-neutral-50 border-b border-neutral-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-[80px]">
            <h1 className="text-heading-1 text-neutral-900">My Campaigns</h1>
            <Button
              variant="primary"
              size="md"
              onClick={() => setShowNewModal(true)}
              leftIcon={
                <span className="text-base leading-none font-bold">+</span>
              }
            >
              New Campaign
            </Button>
          </div>

          {/* Filter tabs */}
          <div className="flex gap-1 -mb-px">
            {filterTabs.map((tab) => (
              <button
                key={tab.value}
                type="button"
                onClick={() => handleFilterChange(tab.value)}
                className={[
                  'px-4 py-2.5 text-body-strong border-b-2 transition-colors duration-150',
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
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6">
        {isLoading ? (
          /* Skeleton grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <CampaignCardSkeleton key={i} />
            ))}
          </div>
        ) : campaigns.length === 0 ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="w-16 h-16 rounded-2xl bg-brand-primary-soft flex items-center justify-center mb-6">
              <svg
                width="32"
                height="32"
                viewBox="0 0 32 32"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <rect
                  x="4"
                  y="6"
                  width="24"
                  height="20"
                  rx="3"
                  stroke="#2E5BFF"
                  strokeWidth="2"
                />
                <path d="M4 13H28" stroke="#2E5BFF" strokeWidth="2" />
                <path
                  d="M10 19H22"
                  stroke="#2E5BFF"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                />
                <path
                  d="M10 23H16"
                  stroke="#2E5BFF"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                />
              </svg>
            </div>
            <h2 className="text-display text-neutral-900 mb-2">
              {activeFilter === 'all'
                ? 'Start your first campaign'
                : `No ${filterTabs.find((t) => t.value === activeFilter)?.label ?? ''} campaigns`}
            </h2>
            <p className="text-body text-neutral-400 max-w-[480px] mb-8">
              {activeFilter === 'all'
                ? `Hi ${isFirstName}! Create a campaign to start building personalised emails at scale using your Google Sheets data.`
                : 'Change the filter or create a new campaign to get started.'}
            </p>
            {activeFilter === 'all' && (
              <Button
                variant="primary"
                size="lg"
                onClick={() => setShowNewModal(true)}
                leftIcon={
                  <span className="text-base leading-none font-bold">+</span>
                }
              >
                New Campaign
              </Button>
            )}
          </div>
        ) : (
          /* Campaign grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {campaigns.map((campaign) => (
              <CampaignCard
                key={campaign.id}
                campaign={campaign}
                onClick={() => handleCardClick(campaign.id)}
                onDuplicated={(newCampaign) => {
                  setCampaigns((prev) => [newCampaign, ...prev])
                  setTotal((t) => t + 1)
                }}
                onArchived={(archivedId) => {
                  setCampaigns((prev) => prev.filter((c) => c.id !== archivedId))
                  setTotal((t) => Math.max(0, t - 1))
                }}
              />
            ))}
          </div>
        )}
      </main>

      <NewCampaignModal
        isOpen={showNewModal}
        onClose={() => setShowNewModal(false)}
        onCreated={handleCampaignCreated}
      />
    </div>
  )
}
